from __future__ import annotations

import hashlib
import base64
import json
import re
import sqlite3
import threading
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit, urlunsplit
from uuid import uuid4

from .config import CONFIG_DIR

KNOWLEDGE_DB_PATH = CONFIG_DIR / "knowte.db"
_ARTIFACT_STATUSES = {
    "idea",
    "researching",
    "outlining",
    "drafting",
    "reviewing",
    "complete",
    "archived",
}
_ARXIV_ID = re.compile(
    r"(?:arxiv(?:\.org)?(?::|/abs/|/pdf/))?"
    r"((?:[a-z-]+(?:\.[a-z]{2})?/\d{7})|(?:\d{4}\.\d{4,5}))(?:v\d+)?",
    re.IGNORECASE,
)
_SCHEMA_LOCK = threading.Lock()
_TAGGABLE_ENTITY_TABLES = {
    "source": "sources",
    "evidence": "evidence",
    "artifact": "artifacts",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _quote_matches_capture(quote: str, captured_text: str) -> bool:
    """Match viewer text despite PDF extraction whitespace and glyph differences."""
    def normalized(value: str) -> str:
        value = unicodedata.normalize("NFKC", value).replace("\u00ad", "")
        value = re.sub(r"(?<=\w)-\s+(?=\w)", "", value)
        return " ".join(value.split()).casefold()

    normalized_quote = normalized(quote)
    normalized_capture = normalized(captured_text)
    if not normalized_quote:
        return False
    if normalized_quote in normalized_capture:
        return True
    compact_quote = "".join(character for character in normalized_quote if character.isalnum())
    compact_capture = "".join(
        character for character in normalized_capture if character.isalnum()
    )
    return len(compact_quote) >= 12 and compact_quote in compact_capture


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    with _SCHEMA_LOCK:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            INSERT OR IGNORE INTO schema_meta (key, value)
            VALUES ('schema_version', '1');

            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                purpose TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'idea',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                canonical_key TEXT NOT NULL UNIQUE,
                source_type TEXT NOT NULL,
                title TEXT NOT NULL,
                authors TEXT NOT NULL DEFAULT '',
                published_year INTEGER,
                provider TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL DEFAULT '',
                paper_url TEXT NOT NULL DEFAULT '',
                pdf_url TEXT NOT NULL DEFAULT '',
                doi_url TEXT NOT NULL DEFAULT '',
                abstract TEXT NOT NULL DEFAULT '',
                capture_state TEXT NOT NULL DEFAULT 'reference',
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS artifact_sources (
                artifact_id TEXT NOT NULL
                    REFERENCES artifacts(id) ON DELETE CASCADE,
                source_id TEXT NOT NULL
                    REFERENCES sources(id) ON DELETE CASCADE,
                added_at TEXT NOT NULL,
                PRIMARY KEY (artifact_id, source_id)
            );

            CREATE INDEX IF NOT EXISTS idx_sources_updated_at
            ON sources(updated_at DESC);

            CREATE INDEX IF NOT EXISTS idx_artifact_sources_source
            ON artifact_sources(source_id);

            CREATE TABLE IF NOT EXISTS source_captures (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
                url TEXT NOT NULL,
                media_type TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                raw_path TEXT NOT NULL,
                extraction_version INTEGER NOT NULL DEFAULT 1,
                captured_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS capture_segments (
                id TEXT PRIMARY KEY,
                capture_id TEXT NOT NULL
                    REFERENCES source_captures(id) ON DELETE CASCADE,
                ordinal INTEGER NOT NULL,
                locator TEXT NOT NULL,
                text TEXT NOT NULL,
                text_hash TEXT NOT NULL,
                block_type TEXT NOT NULL DEFAULT 'paragraph',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                UNIQUE(capture_id, ordinal)
            );

            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
                capture_id TEXT NOT NULL
                    REFERENCES source_captures(id) ON DELETE CASCADE,
                segment_id TEXT NOT NULL
                    REFERENCES capture_segments(id) ON DELETE CASCADE,
                quote TEXT NOT NULL,
                start_offset INTEGER NOT NULL,
                end_offset INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS artifact_evidence (
                artifact_id TEXT NOT NULL
                    REFERENCES artifacts(id) ON DELETE CASCADE,
                evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
                added_at TEXT NOT NULL,
                PRIMARY KEY (artifact_id, evidence_id)
            );

            CREATE TABLE IF NOT EXISTS annotations (
                id TEXT PRIMARY KEY,
                target_type TEXT NOT NULL CHECK(target_type IN ('source', 'evidence')),
                target_id TEXT NOT NULL,
                body TEXT NOT NULL,
                origin TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tags (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                normalized_name TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS entity_tags (
                entity_type TEXT NOT NULL CHECK(
                    entity_type IN ('source', 'evidence', 'artifact')
                ),
                entity_id TEXT NOT NULL,
                tag_id TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                PRIMARY KEY (entity_type, entity_id, tag_id)
            );

            CREATE INDEX IF NOT EXISTS idx_captures_source
            ON source_captures(source_id, captured_at DESC);
            CREATE INDEX IF NOT EXISTS idx_evidence_source
            ON evidence(source_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_annotations_target
            ON annotations(target_type, target_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_entity_tags_entity
            ON entity_tags(entity_type, entity_id);
            """
        )
        evidence_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(evidence)").fetchall()
        }
        for name, definition in (
            ("evidence_type", "TEXT NOT NULL DEFAULT 'text'"),
            ("locator", "TEXT NOT NULL DEFAULT ''"),
            ("anchor_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("snapshot_path", "TEXT NOT NULL DEFAULT ''"),
        ):
            if name not in evidence_columns:
                connection.execute(
                    f"ALTER TABLE evidence ADD COLUMN {name} {definition}"
                )
        segment_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(capture_segments)"
            ).fetchall()
        }
        for name, definition in (
            ("block_type", "TEXT NOT NULL DEFAULT 'paragraph'"),
            ("metadata_json", "TEXT NOT NULL DEFAULT '{}'"),
        ):
            if name not in segment_columns:
                connection.execute(
                    f"ALTER TABLE capture_segments ADD COLUMN {name} {definition}"
                )
        capture_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(source_captures)"
            ).fetchall()
        }
        if "extraction_version" not in capture_columns:
            connection.execute(
                "ALTER TABLE source_captures ADD COLUMN "
                "extraction_version INTEGER NOT NULL DEFAULT 1"
            )
        annotation_schema = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'annotations'"
        ).fetchone()["sql"]
        if "'artifact'" not in annotation_schema:
            connection.executescript(
                """
                ALTER TABLE annotations RENAME TO annotations_legacy;
                CREATE TABLE annotations (
                    id TEXT PRIMARY KEY,
                    target_type TEXT NOT NULL CHECK(
                        target_type IN ('source', 'evidence', 'artifact')
                    ),
                    target_id TEXT NOT NULL,
                    body TEXT NOT NULL,
                    origin TEXT NOT NULL DEFAULT 'user',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                INSERT INTO annotations
                    (id, target_type, target_id, body, origin, created_at, updated_at)
                SELECT id, target_type, target_id, body, origin, created_at, updated_at
                FROM annotations_legacy;
                DROP TABLE annotations_legacy;
                CREATE INDEX IF NOT EXISTS idx_annotations_target
                ON annotations(target_type, target_id, created_at);
                """
            )
        entity_tags_schema = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'entity_tags'"
        ).fetchone()["sql"]
        if "'annotation'" in entity_tags_schema:
            connection.executescript(
                """
                ALTER TABLE entity_tags RENAME TO entity_tags_legacy;
                CREATE TABLE entity_tags (
                    entity_type TEXT NOT NULL CHECK(
                        entity_type IN ('source', 'evidence', 'artifact')
                    ),
                    entity_id TEXT NOT NULL,
                    tag_id TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (entity_type, entity_id, tag_id)
                );
                INSERT INTO entity_tags
                    (entity_type, entity_id, tag_id, created_at)
                SELECT entity_type, entity_id, tag_id, created_at
                FROM entity_tags_legacy
                WHERE entity_type IN ('source', 'evidence', 'artifact');
                DROP TABLE entity_tags_legacy;
                CREATE INDEX IF NOT EXISTS idx_entity_tags_entity
                ON entity_tags(entity_type, entity_id);
                DELETE FROM tags
                WHERE NOT EXISTS (
                    SELECT 1 FROM entity_tags WHERE entity_tags.tag_id = tags.id
                );
                """
            )
        legacy_groups = (
            connection.execute(
                "SELECT id, group_name FROM evidence WHERE group_name <> ''"
            ).fetchall()
            if "group_name" in evidence_columns else []
        )
        for row in legacy_groups:
            name = _clean_text(row["group_name"], 60)
            normalized = _normalize_tag_name(name)
            tag_id = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]
            connection.execute(
                "INSERT OR IGNORE INTO tags "
                "(id, name, normalized_name, created_at) VALUES (?, ?, ?, ?)",
                (tag_id, name, normalized, _now()),
            )
            connection.execute(
                "INSERT OR IGNORE INTO entity_tags "
                "(entity_type, entity_id, tag_id, created_at) VALUES ('evidence', ?, ?, ?)",
                (row["id"], tag_id, _now()),
            )
    return connection


def _clean_text(value: Any, maximum: int) -> str:
    return " ".join(str(value or "").split())[:maximum]


def _normalize_tag_name(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def _tags_by_entity(
    connection: sqlite3.Connection, entity_type: str, entity_ids: list[str]
) -> dict[str, list[dict[str, Any]]]:
    if not entity_ids:
        return {}
    placeholders = ",".join("?" for _ in entity_ids)
    rows = connection.execute(
        f"""
        SELECT entity_tags.entity_id, tags.* FROM entity_tags
        JOIN tags ON tags.id = entity_tags.tag_id
        WHERE entity_tags.entity_type = ?
          AND entity_tags.entity_id IN ({placeholders})
        ORDER BY tags.normalized_name
        """,
        (entity_type, *entity_ids),
    ).fetchall()
    result: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        result.setdefault(row["entity_id"], []).append({
            "id": row["id"], "name": row["name"], "color": row["color"],
            "description": row["description"],
        })
    return result


def _normalize_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
    except ValueError:
        return raw
    if not parts.scheme or not parts.netloc:
        return raw
    path = unquote(parts.path).rstrip("/") or "/"
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            path,
            parts.query,
            "",
        )
    )


def canonical_source_key(payload: dict[str, Any]) -> str:
    doi_url = _normalize_url(payload.get("doi_url"))
    if doi_url:
        doi_path = urlsplit(doi_url).path.strip("/").casefold()
        if doi_path:
            return f"doi:{doi_path}"

    candidates = (
        payload.get("id"),
        payload.get("paper_url"),
        payload.get("url"),
        payload.get("pdf_url"),
    )
    for value in candidates:
        match = _ARXIV_ID.search(str(value or ""))
        if match:
            return f"arxiv:{match.group(1).casefold()}"

    primary_url = _normalize_url(
        payload.get("paper_url") or payload.get("url") or payload.get("pdf_url")
    )
    if primary_url:
        return f"url:{primary_url}"

    identity = "\n".join(
        (
            _clean_text(payload.get("title"), 1000).casefold(),
            _clean_text(payload.get("authors"), 1000).casefold(),
            str(payload.get("year") or ""),
            _clean_text(payload.get("source"), 100).casefold(),
        )
    )
    return f"fallback:{hashlib.sha256(identity.encode('utf-8')).hexdigest()}"


def _artifact_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "purpose": row["purpose"],
        "status": row["status"],
        "source_count": row["source_count"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_artifacts(path: Path | None = None) -> list[dict[str, Any]]:
    with _connect(path or KNOWLEDGE_DB_PATH) as connection:
        rows = connection.execute(
            """
            SELECT artifacts.*, COUNT(artifact_sources.source_id) AS source_count
            FROM artifacts
            LEFT JOIN artifact_sources
              ON artifact_sources.artifact_id = artifacts.id
            GROUP BY artifacts.id
            ORDER BY artifacts.updated_at DESC
            """
        ).fetchall()
        tags = _tags_by_entity(connection, "artifact", [row["id"] for row in rows])
    artifacts = [_artifact_row(row) for row in rows]
    for artifact in artifacts:
        artifact["tags"] = tags.get(artifact["id"], [])
    return artifacts


def create_artifact(
    payload: dict[str, Any],
    path: Path | None = None,
) -> dict[str, Any]:
    title = _clean_text(payload.get("title"), 200)
    purpose = _clean_text(payload.get("purpose"), 4000)
    if not title:
        raise ValueError("title is required")
    if not purpose:
        raise ValueError("purpose is required")
    status = str(payload.get("status") or "idea").strip().lower()
    if status not in _ARTIFACT_STATUSES:
        status = "idea"
    now = _now()
    artifact_id = uuid4().hex
    with _connect(path or KNOWLEDGE_DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO artifacts
                (id, title, purpose, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (artifact_id, title, purpose, status, now, now),
        )
    return {
        "id": artifact_id,
        "title": title,
        "purpose": purpose,
        "status": status,
        "source_count": 0,
        "created_at": now,
        "updated_at": now,
    }


def _source_row(
    row: sqlite3.Row,
    artifacts: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "id": row["id"],
        "canonical_key": row["canonical_key"],
        "source_type": row["source_type"],
        "title": row["title"],
        "authors": row["authors"],
        "year": row["published_year"],
        "source": row["provider"],
        "url": row["url"],
        "paper_url": row["paper_url"],
        "pdf_url": row["pdf_url"],
        "doi_url": row["doi_url"],
        "abstract": row["abstract"],
        "capture_state": row["capture_state"],
        "artifacts": artifacts,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_sources(path: Path | None = None) -> list[dict[str, Any]]:
    database_path = path or KNOWLEDGE_DB_PATH
    with _connect(database_path) as connection:
        source_rows = connection.execute(
            "SELECT * FROM sources ORDER BY updated_at DESC"
        ).fetchall()
        links = connection.execute(
            """
            SELECT artifact_sources.source_id, artifacts.id, artifacts.title
            FROM artifact_sources
            JOIN artifacts ON artifacts.id = artifact_sources.artifact_id
            ORDER BY artifact_sources.added_at
            """
        ).fetchall()
        tags = _tags_by_entity(
            connection, "source", [row["id"] for row in source_rows]
        )
    artifacts_by_source: dict[str, list[dict[str, str]]] = {}
    for link in links:
        artifacts_by_source.setdefault(link["source_id"], []).append(
            {"id": link["id"], "title": link["title"]}
        )
    sources = [
        _source_row(row, artifacts_by_source.get(row["id"], []))
        for row in source_rows
    ]
    for source in sources:
        source["tags"] = tags.get(source["id"], [])
    return sources


def list_replay_sources(
    artifact_reference: str = "",
    path: Path | None = None,
) -> list[dict[str, Any]]:
    database_path = path or KNOWLEDGE_DB_PATH
    reference = str(artifact_reference or "").strip()
    with _connect(database_path) as connection:
        if reference:
            rows = connection.execute(
                """
                SELECT sources.*
                FROM sources
                JOIN artifact_sources
                  ON artifact_sources.source_id = sources.id
                JOIN artifacts
                  ON artifacts.id = artifact_sources.artifact_id
                WHERE artifacts.id = ?
                   OR lower(artifacts.title) = lower(?)
                ORDER BY artifact_sources.added_at
                """,
                (reference, reference),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM sources ORDER BY created_at"
            ).fetchall()

    replay_results = []
    for row in rows:
        try:
            stored_payload = json.loads(row["payload_json"])
        except (json.JSONDecodeError, TypeError):
            stored_payload = {}
        result = dict(stored_payload) if isinstance(stored_payload, dict) else {}
        original_path = str(result.get("discovery_path") or "").strip()
        result.update(
            {
                "id": row["id"],
                "title": row["title"],
                "authors": row["authors"],
                "year": row["published_year"],
                "source": row["provider"],
                "url": row["url"],
                "paper_url": row["paper_url"],
                "pdf_url": row["pdf_url"],
                "doi_url": row["doi_url"],
                "abstract": row["abstract"],
                "result_type": row["source_type"],
                "capture_state": row["capture_state"],
                "debug_replay": True,
                "discovery_path": (
                    f"Debug replay · {original_path}"
                    if original_path
                    else "Debug replay · previously saved Source"
                ),
            }
        )
        replay_results.append(result)
    return replay_results


def save_source(
    payload: dict[str, Any],
    artifact_id: str | None = None,
    path: Path | None = None,
) -> tuple[dict[str, Any], bool, bool]:
    title = _clean_text(payload.get("title"), 1000)
    if not title:
        raise ValueError("source title is required")
    canonical_key = canonical_source_key(payload)
    source_type = (
        "web" if str(payload.get("result_type") or "") == "web" else "paper"
    )
    authors = _clean_text(payload.get("authors"), 2000)
    provider = _clean_text(payload.get("source"), 100)
    abstract = _clean_text(payload.get("abstract"), 12000)
    try:
        year = int(payload.get("year")) if payload.get("year") else None
    except (TypeError, ValueError):
        year = None
    urls = {
        field: _normalize_url(payload.get(field))
        for field in ("url", "paper_url", "pdf_url", "doi_url")
    }
    now = _now()
    source_created = False
    link_created = False
    database_path = path or KNOWLEDGE_DB_PATH
    with _connect(database_path) as connection:
        if artifact_id:
            artifact = connection.execute(
                "SELECT id FROM artifacts WHERE id = ?",
                (artifact_id,),
            ).fetchone()
            if artifact is None:
                raise ValueError("artifact not found")
        existing = connection.execute(
            "SELECT id, created_at FROM sources WHERE canonical_key = ?",
            (canonical_key,),
        ).fetchone()
        if existing is None:
            source_id = uuid4().hex
            created_at = now
            connection.execute(
                """
                INSERT INTO sources (
                    id, canonical_key, source_type, title, authors,
                    published_year, provider, url, paper_url, pdf_url,
                    doi_url, abstract, capture_state, payload_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    canonical_key,
                    source_type,
                    title,
                    authors,
                    year,
                    provider,
                    urls["url"],
                    urls["paper_url"],
                    urls["pdf_url"],
                    urls["doi_url"],
                    abstract,
                    "reference",
                    json.dumps(payload, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            source_created = True
        else:
            source_id = existing["id"]
            created_at = existing["created_at"]
            connection.execute(
                """
                UPDATE sources SET
                    title = ?, authors = ?, published_year = ?, provider = ?,
                    url = ?, paper_url = ?, pdf_url = ?, doi_url = ?,
                    abstract = ?, payload_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    title,
                    authors,
                    year,
                    provider,
                    urls["url"],
                    urls["paper_url"],
                    urls["pdf_url"],
                    urls["doi_url"],
                    abstract,
                    json.dumps(payload, ensure_ascii=False),
                    now,
                    source_id,
                ),
            )
        if artifact_id:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO artifact_sources
                    (artifact_id, source_id, added_at)
                VALUES (?, ?, ?)
                """,
                (artifact_id, source_id, now),
            )
            link_created = cursor.rowcount > 0
            if link_created:
                connection.execute(
                    "UPDATE artifacts SET updated_at = ? WHERE id = ?",
                    (now, artifact_id),
                )

        artifact_rows = connection.execute(
            """
            SELECT artifacts.id, artifacts.title
            FROM artifact_sources
            JOIN artifacts ON artifacts.id = artifact_sources.artifact_id
            WHERE artifact_sources.source_id = ?
            ORDER BY artifact_sources.added_at
            """,
            (source_id,),
        ).fetchall()
        source_row = connection.execute(
            "SELECT * FROM sources WHERE id = ?",
            (source_id,),
        ).fetchone()
    source = _source_row(
        source_row,
        [{"id": row["id"], "title": row["title"]} for row in artifact_rows],
    )
    source["created_at"] = created_at
    return source, source_created, link_created


def get_source(source_id: str, path: Path | None = None) -> dict[str, Any]:
    sources = list_sources(path)
    for source in sources:
        if source["id"] == source_id:
            return source
    raise ValueError("source not found")


def store_capture(
    source_id: str,
    captured: dict[str, Any],
    path: Path | None = None,
) -> dict[str, Any]:
    database_path = path or KNOWLEDGE_DB_PATH
    now = _now()
    with _connect(database_path) as connection:
        if connection.execute(
            "SELECT id FROM sources WHERE id = ?", (source_id,)
        ).fetchone() is None:
            raise ValueError("source not found")
        existing = connection.execute(
            """
            SELECT id FROM source_captures
            WHERE source_id = ? AND sha256 = ? AND extraction_version = ?
            ORDER BY captured_at DESC LIMIT 1
            """,
            (
                source_id,
                captured["sha256"],
                int(captured.get("extraction_version") or 1),
            ),
        ).fetchone()
        if existing:
            capture_id = existing["id"]
        else:
            capture_id = uuid4().hex
            connection.execute(
                """
                INSERT INTO source_captures
                    (id, source_id, url, media_type, sha256, raw_path,
                     extraction_version, captured_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    capture_id, source_id, captured["url"], captured["media_type"],
                    captured["sha256"], captured["raw_path"],
                    int(captured.get("extraction_version") or 1), now,
                ),
            )
            locators = captured.get("locators") or []
            blocks = captured.get("blocks") or []
            for ordinal, text in enumerate(captured["segments"], start=1):
                block = blocks[ordinal - 1] if ordinal <= len(blocks) else {}
                connection.execute(
                    """
                    INSERT INTO capture_segments
                        (id, capture_id, ordinal, locator, text, text_hash,
                         block_type, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        uuid4().hex, capture_id, ordinal,
                        (
                            str(locators[ordinal - 1])
                            if ordinal <= len(locators)
                            else f"Segment {ordinal}"
                        ),
                        text,
                        hashlib.sha256(text.encode("utf-8")).hexdigest(),
                        str(block.get("type") or "paragraph"),
                        json.dumps(block.get("metadata") or {}, ensure_ascii=False),
                    ),
                )
        connection.execute(
            "UPDATE sources SET capture_state = 'captured', updated_at = ? WHERE id = ?",
            (now, source_id),
        )
    return get_source_workspace(source_id, database_path)


def _annotation_rows(
    connection: sqlite3.Connection, target_type: str, target_ids: list[str]
) -> dict[str, list[dict[str, Any]]]:
    if not target_ids:
        return {}
    placeholders = ",".join("?" for _ in target_ids)
    rows = connection.execute(
        f"""
        SELECT * FROM annotations
        WHERE target_type = ? AND target_id IN ({placeholders})
        ORDER BY created_at
        """,
        (target_type, *target_ids),
    ).fetchall()
    result: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        result.setdefault(row["target_id"], []).append(dict(row))
    return result


def get_source_workspace(
    source_id: str, path: Path | None = None
) -> dict[str, Any]:
    database_path = path or KNOWLEDGE_DB_PATH
    source = get_source(source_id, database_path)
    with _connect(database_path) as connection:
        capture = connection.execute(
            """
            SELECT * FROM source_captures
            WHERE source_id = ? ORDER BY captured_at DESC LIMIT 1
            """,
            (source_id,),
        ).fetchone()
        segments = []
        if capture:
            segments = [
                dict(row) for row in connection.execute(
                    "SELECT * FROM capture_segments WHERE capture_id = ? ORDER BY ordinal",
                    (capture["id"],),
                ).fetchall()
            ]
            for segment in segments:
                try:
                    segment["metadata"] = json.loads(
                        segment.pop("metadata_json") or "{}"
                    )
                except (json.JSONDecodeError, TypeError):
                    segment["metadata"] = {}
        evidence_rows = [
            dict(row) for row in connection.execute(
                """
                SELECT evidence.*, capture_segments.locator
                FROM evidence JOIN capture_segments
                  ON capture_segments.id = evidence.segment_id
                WHERE evidence.source_id = ? ORDER BY evidence.created_at DESC
                """,
                (source_id,),
            ).fetchall()
        ]
        evidence_annotations = _annotation_rows(
            connection, "evidence", [item["id"] for item in evidence_rows]
        )
        evidence_tags = _tags_by_entity(
            connection, "evidence", [item["id"] for item in evidence_rows]
        )
        for item in evidence_rows:
            try:
                item["anchor"] = json.loads(item.pop("anchor_json") or "{}")
            except (json.JSONDecodeError, TypeError):
                item["anchor"] = {}
            item["has_snapshot"] = bool(item.pop("snapshot_path", ""))
            item["annotations"] = evidence_annotations.get(item["id"], [])
            item["tags"] = evidence_tags.get(item["id"], [])
        source_annotations = _annotation_rows(connection, "source", [source_id])
        source_annotation_list = source_annotations.get(source_id, [])
    capture_payload = dict(capture) if capture else None
    if capture_payload:
        capture_payload.pop("raw_path", None)
    return {
        "source": source,
        "capture": capture_payload,
        "segments": segments,
        "evidence": evidence_rows,
        "annotations": source_annotation_list,
    }


def create_evidence(
    payload: dict[str, Any], path: Path | None = None
) -> dict[str, Any]:
    database_path = path or KNOWLEDGE_DB_PATH
    evidence_type = str(payload.get("evidence_type") or "text").strip().lower()
    if evidence_type not in {"text", "snapshot"}:
        raise ValueError("unsupported Evidence type")
    segment_id = str(payload.get("segment_id") or "")
    quote = str(payload.get("quote") or "")
    if evidence_type == "text" and not quote.strip():
        raise ValueError("quote is required")
    anchor = payload.get("anchor")
    anchor = anchor if isinstance(anchor, dict) else {}
    locator = _clean_text(payload.get("locator"), 300)
    snapshot_path = ""
    now = _now()
    with _connect(database_path) as connection:
        segment = connection.execute(
            """
            SELECT capture_segments.*, source_captures.source_id
            FROM capture_segments JOIN source_captures
              ON source_captures.id = capture_segments.capture_id
            WHERE capture_segments.id = ?
            """,
            (segment_id,),
        ).fetchone()
        if segment is None:
            raise ValueError("segment not found")
        if evidence_type == "text":
            try:
                start = int(payload.get("start_offset"))
                end = int(payload.get("end_offset"))
            except (TypeError, ValueError):
                start = end = -1
            exact_offsets = (
                start >= 0
                and end > start
                and end <= len(segment["text"])
                and segment["text"][start:end] == quote
            )
            quote_anchor = _quote_matches_capture(quote, segment["text"])
            if not exact_offsets and not quote_anchor:
                raise ValueError("quote does not match the captured Source")
            if not exact_offsets:
                start = end = -1
        else:
            start = end = 0
            image_data = str(payload.get("image_data") or "")
            prefix = "data:image/png;base64,"
            if not image_data.startswith(prefix):
                raise ValueError("Snapshot Evidence must be a PNG image")
            try:
                image_bytes = base64.b64decode(
                    image_data[len(prefix):], validate=True
                )
            except (ValueError, TypeError) as error:
                raise ValueError("Snapshot image is invalid") from error
            if not image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("Snapshot Evidence must be a PNG image")
            if len(image_bytes) > 10 * 1024 * 1024:
                raise ValueError("Snapshot image exceeds the 10 MB limit")
            snapshot_id = uuid4().hex
            snapshot_dir = database_path.parent / "content" / "evidence"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            snapshot_file = snapshot_dir / f"{snapshot_id}.png"
            snapshot_file.write_bytes(image_bytes)
            snapshot_path = str(snapshot_file)
        evidence_id = uuid4().hex
        connection.execute(
            """
            INSERT INTO evidence
                (id, source_id, capture_id, segment_id, quote,
                 start_offset, end_offset, created_at, evidence_type,
                 locator, anchor_json, snapshot_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id, segment["source_id"], segment["capture_id"],
                segment_id, quote, start, end, now, evidence_type,
                locator or segment["locator"],
                json.dumps(anchor, ensure_ascii=False), snapshot_path,
            ),
        )
        artifact_id = str(payload.get("artifact_id") or "").strip()
        if artifact_id:
            if connection.execute(
                "SELECT id FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone() is None:
                raise ValueError("artifact not found")
            connection.execute(
                """
                INSERT INTO artifact_evidence (artifact_id, evidence_id, added_at)
                VALUES (?, ?, ?)
                """,
                (artifact_id, evidence_id, now),
            )
    return {
        "id": evidence_id,
        "source_id": segment["source_id"],
        "evidence_type": evidence_type,
        "quote": quote,
        "locator": locator or segment["locator"],
    }


def get_capture_file(
    source_id: str,
    content_dir: Path,
    path: Path | None = None,
) -> tuple[Path, str, str]:
    database_path = path or KNOWLEDGE_DB_PATH
    with _connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT raw_path, media_type, sha256
            FROM source_captures
            WHERE source_id = ? ORDER BY captured_at DESC LIMIT 1
            """,
            (source_id,),
        ).fetchone()
    if row is None:
        raise ValueError("Source has not been captured")
    raw_path = Path(row["raw_path"]).resolve()
    root = content_dir.resolve()
    if raw_path != root and root not in raw_path.parents:
        raise ValueError("captured content path is invalid")
    if not raw_path.is_file():
        raise ValueError("captured content is missing")
    return raw_path, row["media_type"], row["sha256"]


def get_snapshot_file(
    evidence_id: str,
    content_dir: Path,
    path: Path | None = None,
) -> Path:
    database_path = path or KNOWLEDGE_DB_PATH
    with _connect(database_path) as connection:
        row = connection.execute(
            "SELECT snapshot_path FROM evidence WHERE id = ? AND evidence_type = 'snapshot'",
            (evidence_id,),
        ).fetchone()
    if row is None or not row["snapshot_path"]:
        raise ValueError("Snapshot Evidence not found")
    snapshot_path = Path(row["snapshot_path"]).resolve()
    root = content_dir.resolve()
    if snapshot_path != root and root not in snapshot_path.parents:
        raise ValueError("Snapshot path is invalid")
    if not snapshot_path.is_file():
        raise ValueError("Snapshot image is missing")
    return snapshot_path


def create_annotation(
    payload: dict[str, Any], path: Path | None = None
) -> dict[str, Any]:
    database_path = path or KNOWLEDGE_DB_PATH
    target_type = str(payload.get("target_type") or "").strip().lower()
    target_id = str(payload.get("target_id") or "").strip()
    body = str(payload.get("body") or "").strip()
    if target_type not in {"source", "evidence", "artifact"}:
        raise ValueError("annotation target must be a Source, Evidence, or Artifact")
    if not body:
        raise ValueError("annotation body is required")
    table = _TAGGABLE_ENTITY_TABLES[target_type]
    now = _now()
    annotation_id = uuid4().hex
    with _connect(database_path) as connection:
        if connection.execute(
            f"SELECT id FROM {table} WHERE id = ?", (target_id,)
        ).fetchone() is None:
            raise ValueError(f"{target_type} not found")
        connection.execute(
            """
            INSERT INTO annotations
                (id, target_type, target_id, body, origin, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'user', ?, ?)
            """,
            (annotation_id, target_type, target_id, body, now, now),
        )
    return {
        "id": annotation_id, "target_type": target_type, "target_id": target_id,
        "body": body, "origin": "user", "created_at": now, "updated_at": now,
    }


def list_tags(path: Path | None = None) -> list[dict[str, Any]]:
    with _connect(path or KNOWLEDGE_DB_PATH) as connection:
        rows = connection.execute(
            "SELECT * FROM tags ORDER BY normalized_name"
        ).fetchall()
    return [dict(row) for row in rows]


def set_entity_tags(
    entity_type: str, entity_id: str, names: list[Any], path: Path | None = None
) -> list[dict[str, Any]]:
    normalized_type = str(entity_type or "").strip().lower()
    table = _TAGGABLE_ENTITY_TABLES.get(normalized_type)
    if table is None:
        raise ValueError("unsupported tag entity type")
    clean_names: dict[str, str] = {}
    for raw_name in names:
        name = _clean_text(raw_name, 60)
        normalized = _normalize_tag_name(name)
        if normalized:
            clean_names.setdefault(normalized, name)
    if len(clean_names) > 20:
        raise ValueError("an entity can have at most 20 Tags")
    database_path = path or KNOWLEDGE_DB_PATH
    now = _now()
    with _connect(database_path) as connection:
        if connection.execute(
            f"SELECT id FROM {table} WHERE id = ?", (entity_id,)
        ).fetchone() is None:
            raise ValueError(f"{normalized_type} not found")
        tag_ids = []
        for normalized, name in clean_names.items():
            row = connection.execute(
                "SELECT id FROM tags WHERE normalized_name = ?", (normalized,)
            ).fetchone()
            tag_id = row["id"] if row else uuid4().hex
            if row is None:
                connection.execute(
                    "INSERT INTO tags "
                    "(id, name, normalized_name, created_at) VALUES (?, ?, ?, ?)",
                    (tag_id, name, normalized, now),
                )
            tag_ids.append(tag_id)
        connection.execute(
            "DELETE FROM entity_tags WHERE entity_type = ? AND entity_id = ?",
            (normalized_type, entity_id),
        )
        connection.executemany(
            "INSERT INTO entity_tags "
            "(entity_type, entity_id, tag_id, created_at) VALUES (?, ?, ?, ?)",
            [(normalized_type, entity_id, tag_id, now) for tag_id in tag_ids],
        )
        tags = _tags_by_entity(connection, normalized_type, [entity_id])
    return tags.get(entity_id, [])


def delete_evidence(evidence_id: str, path: Path | None = None) -> bool:
    database_path = path or KNOWLEDGE_DB_PATH
    snapshot_path = ""
    with _connect(database_path) as connection:
        row = connection.execute(
            "SELECT snapshot_path FROM evidence WHERE id = ?", (evidence_id,)
        ).fetchone()
        if row is None:
            return False
        snapshot_path = row["snapshot_path"] or ""
        connection.execute(
            "DELETE FROM annotations WHERE target_type = 'evidence' AND target_id = ?",
            (evidence_id,),
        )
        connection.execute("DELETE FROM evidence WHERE id = ?", (evidence_id,))
    if snapshot_path:
        try:
            Path(snapshot_path).unlink(missing_ok=True)
        except OSError:
            pass
    return True


def delete_annotation(annotation_id: str, path: Path | None = None) -> bool:
    database_path = path or KNOWLEDGE_DB_PATH
    with _connect(database_path) as connection:
        cursor = connection.execute(
            "DELETE FROM annotations WHERE id = ?", (annotation_id,)
        )
    return cursor.rowcount > 0
