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
    "claim": "claims",
}
_CLAIM_BASES = {
    "premise", "observation", "reported", "inference",
    "hypothesis", "prediction", "judgment",
}
_CLAIM_STANDINGS = {"unassessed", "consensus", "disputed"}
_CLAIM_LIFECYCLES = {"active", "withdrawn", "superseded"}
_VIEW_TYPES = {"wiki", "article", "graph"}
_VIEW_BLOCK_TYPES = {"heading", "paragraph", "claim"}
_EVIDENCE_CLAIM_STANCES = {
    "supports", "challenges", "qualifies", "contextualizes",
}
_CLAIM_BASIS_TO_STORAGE = {
    "background": "premise",
    "premise": "premise",
    "observation": "reported",
    "reported": "reported",
    "inference": "inference",
    "hypothesis": "inference",
    "prediction": "inference",
    "judgment": "inference",
}
_CLAIM_BASIS_FROM_STORAGE = {
    "premise": "background",
    "observation": "reported",
    "reported": "reported",
    "inference": "inference",
    "hypothesis": "inference",
    "prediction": "inference",
    "judgment": "inference",
}
_EVIDENCE_STANCE_TO_STORAGE = {
    "supports": "supports",
    "contradicts": "challenges",
    "challenges": "challenges",
    "limits": "qualifies",
    "qualifies": "qualifies",
    "contextualizes": "qualifies",
}
_EVIDENCE_STANCE_FROM_STORAGE = {
    "supports": "supports",
    "challenges": "contradicts",
    "qualifies": "limits",
    "contextualizes": "limits",
}
_CLAIM_RELATION_TYPES = {"supports", "contradicts", "related"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _claim_basis_for_storage(value: Any) -> str:
    basis = str(value or "reported").strip().lower()
    try:
        return _CLAIM_BASIS_TO_STORAGE[basis]
    except KeyError as error:
        raise ValueError("unsupported Claim basis") from error


def _evidence_stance_for_storage(value: Any) -> str:
    stance = str(value or "supports").strip().lower()
    try:
        return _EVIDENCE_STANCE_TO_STORAGE[stance]
    except KeyError as error:
        raise ValueError("unsupported Evidence–Claim stance") from error


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

            CREATE TABLE IF NOT EXISTS claims (
                id TEXT PRIMARY KEY,
                current_revision_id TEXT NOT NULL,
                basis TEXT NOT NULL CHECK(basis IN (
                    'premise', 'observation', 'reported', 'inference',
                    'hypothesis', 'prediction', 'judgment'
                )),
                standing TEXT NOT NULL DEFAULT 'unassessed' CHECK(standing IN (
                    'unassessed', 'consensus', 'disputed'
                )),
                lifecycle TEXT NOT NULL DEFAULT 'active' CHECK(lifecycle IN (
                    'active', 'withdrawn', 'superseded'
                )),
                created_via TEXT NOT NULL DEFAULT 'manual',
                capability_version TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT '',
                intentionally_ungrounded INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS claim_revisions (
                id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                statement TEXT NOT NULL,
                change_note TEXT NOT NULL DEFAULT '',
                created_by TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS evidence_claim_links (
                evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
                claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                stance TEXT NOT NULL CHECK(stance IN (
                    'supports', 'challenges', 'qualifies', 'contextualizes'
                )),
                rationale TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                PRIMARY KEY (evidence_id, claim_id)
            );

            CREATE TABLE IF NOT EXISTS claim_relations (
                subject_claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                object_claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                relation_type TEXT NOT NULL CHECK(relation_type IN (
                    'supports', 'contradicts', 'related'
                )),
                rationale TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                PRIMARY KEY (subject_claim_id, object_claim_id, relation_type),
                CHECK(subject_claim_id <> object_claim_id)
            );

            CREATE TABLE IF NOT EXISTS artifact_claims (
                artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
                claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                added_at TEXT NOT NULL,
                PRIMARY KEY (artifact_id, claim_id)
            );

            CREATE TABLE IF NOT EXISTS views (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                view_type TEXT NOT NULL CHECK(view_type IN ('wiki', 'article', 'graph')),
                purpose TEXT NOT NULL DEFAULT '',
                artifact_id TEXT NOT NULL DEFAULT '',
                graph_state_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS view_claims (
                view_id TEXT NOT NULL REFERENCES views(id) ON DELETE CASCADE,
                claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                ordinal INTEGER NOT NULL,
                added_at TEXT NOT NULL,
                PRIMARY KEY (view_id, claim_id)
            );

            CREATE TABLE IF NOT EXISTS review_proposals (
                id TEXT PRIMARY KEY,
                proposal_type TEXT NOT NULL DEFAULT 'claim',
                status TEXT NOT NULL DEFAULT 'awaiting_review',
                capability_version TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                scope_json TEXT NOT NULL DEFAULT '{}',
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_captures_source
            ON source_captures(source_id, captured_at DESC);
            CREATE INDEX IF NOT EXISTS idx_evidence_source
            ON evidence(source_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_annotations_target
            ON annotations(target_type, target_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_entity_tags_entity
            ON entity_tags(entity_type, entity_id);
            CREATE INDEX IF NOT EXISTS idx_claims_updated_at
            ON claims(updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_claim_revisions_claim
            ON claim_revisions(claim_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_evidence_claim_claim
            ON evidence_claim_links(claim_id);
            CREATE INDEX IF NOT EXISTS idx_review_proposals_status
            ON review_proposals(status, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_view_claims_claim
            ON view_claims(claim_id);
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
        claim_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(claims)").fetchall()
        }
        if "intentionally_ungrounded" not in claim_columns:
            connection.execute(
                "ALTER TABLE claims ADD COLUMN "
                "intentionally_ungrounded INTEGER NOT NULL DEFAULT 0"
            )
        claim_relation_schema = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'claim_relations'"
        ).fetchone()["sql"]
        if "'related'" not in claim_relation_schema:
            connection.executescript(
                """
                ALTER TABLE claim_relations RENAME TO claim_relations_legacy;
                CREATE TABLE claim_relations (
                    subject_claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                    object_claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                    relation_type TEXT NOT NULL CHECK(
                        relation_type IN ('supports', 'contradicts', 'related')
                    ),
                    rationale TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (subject_claim_id, object_claim_id, relation_type),
                    CHECK(subject_claim_id <> object_claim_id)
                );
                INSERT INTO claim_relations
                    (subject_claim_id, object_claim_id, relation_type, rationale, created_at)
                SELECT subject_claim_id, object_claim_id, relation_type,
                       rationale, created_at
                FROM claim_relations_legacy
                WHERE relation_type IN ('supports', 'contradicts');
                DROP TABLE claim_relations_legacy;
                """
            )
        view_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(views)").fetchall()
        }
        if "artifact_id" not in view_columns:
            connection.execute(
                "ALTER TABLE views ADD COLUMN artifact_id TEXT NOT NULL DEFAULT ''"
            )
        view_schema = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'views'"
        ).fetchone()["sql"]
        if "'article'" not in view_schema:
            connection.executescript(
                """
                ALTER TABLE view_claims RENAME TO view_claims_legacy;
                ALTER TABLE views RENAME TO views_legacy;
                CREATE TABLE views (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    view_type TEXT NOT NULL CHECK(view_type IN ('wiki', 'article', 'graph')),
                    purpose TEXT NOT NULL DEFAULT '',
                    artifact_id TEXT NOT NULL DEFAULT '',
                    graph_state_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                INSERT INTO views
                    (id, title, view_type, purpose, artifact_id, graph_state_json,
                     created_at, updated_at)
                SELECT id, title,
                       CASE
                         WHEN view_type = 'graph' THEN 'graph'
                         WHEN view_type = 'wiki' THEN 'wiki'
                         ELSE 'article'
                       END,
                       purpose, artifact_id, '{}', created_at, updated_at
                FROM views_legacy;
                CREATE TABLE view_claims (
                    view_id TEXT NOT NULL REFERENCES views(id) ON DELETE CASCADE,
                    claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                    ordinal INTEGER NOT NULL,
                    added_at TEXT NOT NULL,
                    PRIMARY KEY (view_id, claim_id)
                );
                INSERT INTO view_claims (view_id, claim_id, ordinal, added_at)
                SELECT view_id, claim_id, ordinal, added_at FROM view_claims_legacy;
                DROP TABLE view_claims_legacy;
                DROP TABLE views_legacy;
                CREATE INDEX IF NOT EXISTS idx_view_claims_claim ON view_claims(claim_id);
                """
            )
        else:
            view_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(views)").fetchall()
            }
            if "graph_state_json" not in view_columns:
                connection.execute(
                    "ALTER TABLE views ADD COLUMN graph_state_json TEXT NOT NULL DEFAULT '{}'"
                )
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS view_blocks (
                id TEXT PRIMARY KEY,
                view_id TEXT NOT NULL REFERENCES views(id) ON DELETE CASCADE,
                block_type TEXT NOT NULL CHECK(block_type IN ('heading', 'paragraph', 'claim')),
                content TEXT NOT NULL DEFAULT '',
                claim_id TEXT REFERENCES claims(id) ON DELETE SET NULL,
                ordinal INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_view_blocks_view
            ON view_blocks(view_id, ordinal);
            """
        )
        document_views = connection.execute(
            "SELECT id, view_type, purpose FROM views WHERE view_type IN ('wiki', 'article')"
        ).fetchall()
        for document_view in document_views:
            has_blocks = connection.execute(
                "SELECT 1 FROM view_blocks WHERE view_id = ? LIMIT 1",
                (document_view["id"],),
            ).fetchone()
            if has_blocks:
                continue
            now = _now()
            default_heading = "Overview" if document_view["view_type"] == "wiki" else "Article"
            connection.execute(
                "INSERT INTO view_blocks "
                "(id, view_id, block_type, content, claim_id, ordinal, created_at, updated_at) "
                "VALUES (?, ?, 'heading', ?, NULL, 0, ?, ?)",
                (uuid4().hex, document_view["id"], default_heading, now, now),
            )
            ordinal = 1
            if document_view["view_type"] == "article" and document_view["purpose"]:
                connection.execute(
                    "INSERT INTO view_blocks "
                    "(id, view_id, block_type, content, claim_id, ordinal, created_at, updated_at) "
                    "VALUES (?, ?, 'paragraph', ?, NULL, ?, ?, ?)",
                    (uuid4().hex, document_view["id"], document_view["purpose"], ordinal, now, now),
                )
                ordinal += 1
            claim_rows = connection.execute(
                "SELECT claim_id FROM view_claims WHERE view_id = ? ORDER BY ordinal",
                (document_view["id"],),
            ).fetchall()
            for claim_row in claim_rows:
                connection.execute(
                    "INSERT INTO view_blocks "
                    "(id, view_id, block_type, content, claim_id, ordinal, created_at, updated_at) "
                    "VALUES (?, ?, 'claim', '', ?, ?, ?, ?)",
                    (uuid4().hex, document_view["id"], claim_row["claim_id"], ordinal, now, now),
                )
                ordinal += 1
        annotation_schema = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'annotations'"
        ).fetchone()["sql"]
        if "'claim'" not in annotation_schema:
            connection.executescript(
                """
                ALTER TABLE annotations RENAME TO annotations_legacy;
                CREATE TABLE annotations (
                    id TEXT PRIMARY KEY,
                    target_type TEXT NOT NULL CHECK(
                        target_type IN ('source', 'evidence', 'artifact', 'claim')
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
        if "'claim'" not in entity_tags_schema:
            connection.executescript(
                """
                ALTER TABLE entity_tags RENAME TO entity_tags_legacy;
                CREATE TABLE entity_tags (
                    entity_type TEXT NOT NULL CHECK(
                        entity_type IN ('source', 'evidence', 'artifact', 'claim')
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
                WHERE entity_type IN ('source', 'evidence', 'artifact', 'claim');
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
        connection.execute(
            "UPDATE schema_meta SET value = '3' WHERE key = 'schema_version'"
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
    if target_type not in {"source", "evidence", "artifact", "claim"}:
        raise ValueError(
            "annotation target must be a Source, Evidence, Artifact, or Claim"
        )
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


def list_evidence(path: Path | None = None) -> list[dict[str, Any]]:
    database_path = path or KNOWLEDGE_DB_PATH
    with _connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT evidence.*, sources.title AS source_title,
                   sources.provider AS source_provider,
                   COUNT(DISTINCT evidence_claim_links.claim_id) AS claim_count
            FROM evidence
            JOIN sources ON sources.id = evidence.source_id
            LEFT JOIN evidence_claim_links
              ON evidence_claim_links.evidence_id = evidence.id
            GROUP BY evidence.id
            ORDER BY evidence.created_at DESC
            """
        ).fetchall()
        ids = [row["id"] for row in rows]
        tags = _tags_by_entity(connection, "evidence", ids)
        annotations = _annotation_rows(connection, "evidence", ids)
    result = []
    for row in rows:
        item = dict(row)
        item["has_snapshot"] = bool(item.pop("snapshot_path", ""))
        item.pop("anchor_json", None)
        item["tags"] = tags.get(item["id"], [])
        item["annotations"] = annotations.get(item["id"], [])
        result.append(item)
    return result


def _claim_payload(connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    revision = connection.execute(
        "SELECT * FROM claim_revisions WHERE id = ?", (row["current_revision_id"],)
    ).fetchone()
    evidence_rows = connection.execute(
        """
        SELECT evidence_claim_links.*, evidence.evidence_type, evidence.quote,
               evidence.locator, evidence.source_id, sources.title AS source_title
        FROM evidence_claim_links
        JOIN evidence ON evidence.id = evidence_claim_links.evidence_id
        JOIN sources ON sources.id = evidence.source_id
        WHERE evidence_claim_links.claim_id = ?
        ORDER BY evidence_claim_links.created_at
        """,
        (row["id"],),
    ).fetchall()
    artifact_rows = connection.execute(
        """
        SELECT artifacts.id, artifacts.title FROM artifact_claims
        JOIN artifacts ON artifacts.id = artifact_claims.artifact_id
        WHERE artifact_claims.claim_id = ? ORDER BY artifact_claims.added_at
        """,
        (row["id"],),
    ).fetchall()
    relations = connection.execute(
        """
        SELECT * FROM claim_relations
        WHERE subject_claim_id = ? OR object_claim_id = ?
        ORDER BY created_at
        """,
        (row["id"], row["id"]),
    ).fetchall()
    revisions = connection.execute(
        "SELECT * FROM claim_revisions WHERE claim_id = ? ORDER BY created_at",
        (row["id"],),
    ).fetchall()
    tags = _tags_by_entity(connection, "claim", [row["id"]]).get(row["id"], [])
    annotations = _annotation_rows(connection, "claim", [row["id"]]).get(row["id"], [])
    claim = dict(row)
    claim["basis"] = _CLAIM_BASIS_FROM_STORAGE.get(claim["basis"], "inference")
    claim["review_state"] = (
        "disputed" if claim.get("standing") == "disputed" else "accepted"
    )
    evidence_payloads = []
    for item in evidence_rows:
        evidence_item = dict(item)
        evidence_item["stance"] = _EVIDENCE_STANCE_FROM_STORAGE.get(
            evidence_item["stance"], "limits"
        )
        evidence_payloads.append(evidence_item)
    return {
        **claim,
        "statement": revision["statement"],
        "current_revision": dict(revision),
        "revisions": [dict(item) for item in revisions],
        "evidence": evidence_payloads,
        "artifacts": [dict(item) for item in artifact_rows],
        "relations": [dict(item) for item in relations],
        "tags": tags,
        "annotations": annotations,
    }


def list_claims(path: Path | None = None) -> list[dict[str, Any]]:
    with _connect(path or KNOWLEDGE_DB_PATH) as connection:
        rows = connection.execute(
            "SELECT * FROM claims ORDER BY updated_at DESC"
        ).fetchall()
        return [_claim_payload(connection, row) for row in rows]


def get_claim(claim_id: str, path: Path | None = None) -> dict[str, Any]:
    with _connect(path or KNOWLEDGE_DB_PATH) as connection:
        row = connection.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
        if row is None:
            raise ValueError("Claim not found")
        return _claim_payload(connection, row)


def create_claim(payload: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    database_path = path or KNOWLEDGE_DB_PATH
    statement = _clean_text(payload.get("statement"), 4000)
    if not statement:
        raise ValueError("Claim statement is required")
    requested_basis = str(payload.get("basis") or "reported").strip().lower()
    basis = _claim_basis_for_storage(requested_basis)
    review_state = str(payload.get("review_state") or "accepted").strip().lower()
    if review_state not in {"accepted", "disputed"}:
        raise ValueError("unsupported Claim review state")
    standing = "disputed" if review_state == "disputed" else "unassessed"
    if "standing" in payload and "review_state" not in payload:
        legacy_standing = str(payload.get("standing") or "unassessed").strip().lower()
        if legacy_standing not in _CLAIM_STANDINGS:
            raise ValueError("unsupported Claim standing")
        standing = legacy_standing
    evidence_links = payload.get("evidence") or []
    artifact_ids = payload.get("artifact_ids") or []
    if not isinstance(evidence_links, list) or not isinstance(artifact_ids, list):
        raise ValueError("Claim links must be lists")
    intentionally_ungrounded = bool(payload.get("intentionally_ungrounded"))
    if not evidence_links and requested_basis == "background":
        intentionally_ungrounded = True
    if not evidence_links and not intentionally_ungrounded:
        raise ValueError(
            "Claim requires Evidence or an explicit intentionally ungrounded decision"
        )
    now = _now()
    claim_id = uuid4().hex
    revision_id = uuid4().hex
    with _connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO claims
                (id, current_revision_id, basis, standing, lifecycle,
                 created_via, capability_version, model, intentionally_ungrounded,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?)
            """,
            (
                claim_id, revision_id, basis, standing,
                _clean_text(payload.get("created_via") or "manual", 40),
                _clean_text(payload.get("capability_version"), 100),
                _clean_text(payload.get("model"), 200),
                int(intentionally_ungrounded), now, now,
            ),
        )
        connection.execute(
            """
            INSERT INTO claim_revisions
                (id, claim_id, statement, change_note, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                revision_id, claim_id, statement,
                _clean_text(payload.get("change_note"), 1000),
                _clean_text(payload.get("created_by") or "user", 40), now,
            ),
        )
        for link in evidence_links:
            if not isinstance(link, dict):
                continue
            evidence_id = str(link.get("evidence_id") or "")
            stance = _evidence_stance_for_storage(link.get("stance"))
            if connection.execute(
                "SELECT id FROM evidence WHERE id = ?", (evidence_id,)
            ).fetchone() is None:
                raise ValueError("Evidence not found")
            connection.execute(
                """
                INSERT INTO evidence_claim_links
                    (evidence_id, claim_id, stance, rationale, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    evidence_id, claim_id, stance,
                    _clean_text(link.get("rationale"), 2000), now,
                ),
            )
        for artifact_id in dict.fromkeys(str(item) for item in artifact_ids if item):
            if connection.execute(
                "SELECT id FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone() is None:
                raise ValueError("Artifact not found")
            connection.execute(
                "INSERT INTO artifact_claims (artifact_id, claim_id, added_at) VALUES (?, ?, ?)",
                (artifact_id, claim_id, now),
            )
    tags = payload.get("tags") or []
    if isinstance(tags, list) and tags:
        set_entity_tags("claim", claim_id, tags, database_path)
    return get_claim(claim_id, database_path)


def revise_claim(
    claim_id: str, payload: dict[str, Any], path: Path | None = None
) -> dict[str, Any]:
    database_path = path or KNOWLEDGE_DB_PATH
    statement = _clean_text(payload.get("statement"), 4000)
    if not statement:
        raise ValueError("Claim statement is required")
    now = _now()
    revision_id = uuid4().hex
    with _connect(database_path) as connection:
        if connection.execute(
            "SELECT id FROM claims WHERE id = ?", (claim_id,)
        ).fetchone() is None:
            raise ValueError("Claim not found")
        connection.execute(
            """
            INSERT INTO claim_revisions
                (id, claim_id, statement, change_note, created_by, created_at)
            VALUES (?, ?, ?, ?, 'user', ?)
            """,
            (revision_id, claim_id, statement, _clean_text(payload.get("change_note"), 1000), now),
        )
        updates = ["current_revision_id = ?", "updated_at = ?"]
        values: list[Any] = [revision_id, now]
        if "basis" in payload:
            updates.append("basis = ?")
            values.append(_claim_basis_for_storage(payload.get("basis")))
        if "review_state" in payload:
            review_state = str(payload.get("review_state") or "").strip().lower()
            if review_state not in {"accepted", "disputed"}:
                raise ValueError("unsupported Claim review state")
            updates.append("standing = ?")
            values.append("disputed" if review_state == "disputed" else "unassessed")
        elif "standing" in payload:
            value = str(payload.get("standing") or "").strip().lower()
            if value not in _CLAIM_STANDINGS:
                raise ValueError("unsupported Claim standing")
            updates.append("standing = ?")
            values.append(value)
        values.append(claim_id)
        connection.execute(
            f"UPDATE claims SET {', '.join(updates)} WHERE id = ?", values
        )
    return get_claim(claim_id, database_path)


def set_claim_lifecycle(
    claim_id: str, lifecycle: str, path: Path | None = None
) -> dict[str, Any]:
    value = str(lifecycle or "").strip().lower()
    if value not in _CLAIM_LIFECYCLES:
        raise ValueError("unsupported Claim lifecycle")
    database_path = path or KNOWLEDGE_DB_PATH
    with _connect(database_path) as connection:
        cursor = connection.execute(
            "UPDATE claims SET lifecycle = ?, updated_at = ? WHERE id = ?",
            (value, _now(), claim_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("Claim not found")
    return get_claim(claim_id, database_path)


def create_claim_relation(
    payload: dict[str, Any], path: Path | None = None
) -> dict[str, Any]:
    database_path = path or KNOWLEDGE_DB_PATH
    subject_id = str(payload.get("subject_claim_id") or "").strip()
    object_id = str(payload.get("object_claim_id") or "").strip()
    relation_type = str(payload.get("relation_type") or "").strip().lower()
    if not subject_id or not object_id or subject_id == object_id:
        raise ValueError("Claim relation requires two different Claims")
    if relation_type not in _CLAIM_RELATION_TYPES:
        raise ValueError("unsupported Claim relation type")
    rationale = _clean_text(payload.get("rationale"), 2000)
    now = _now()
    with _connect(database_path) as connection:
        found = connection.execute(
            "SELECT COUNT(*) AS count FROM claims WHERE id IN (?, ?)",
            (subject_id, object_id),
        ).fetchone()["count"]
        if found != 2:
            raise ValueError("Claim not found")
        connection.execute(
            """
            INSERT INTO claim_relations
                (subject_claim_id, object_claim_id, relation_type, rationale, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(subject_claim_id, object_claim_id, relation_type)
            DO UPDATE SET rationale = excluded.rationale
            """,
            (subject_id, object_id, relation_type, rationale, now),
        )
    return {
        "subject_claim_id": subject_id,
        "object_claim_id": object_id,
        "relation_type": relation_type,
        "rationale": rationale,
        "created_at": now,
    }


def create_claim_proposal(
    payload: dict[str, Any], capability_version: str,
    model: str = "", scope: dict[str, Any] | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    statement = _clean_text(payload.get("statement"), 4000)
    if not statement:
        raise ValueError("Proposal statement is required")
    proposal_payload = {
        **payload,
        "statement": statement,
        "basis": _CLAIM_BASIS_FROM_STORAGE[
            _claim_basis_for_storage(payload.get("basis"))
        ],
    }
    proposal_payload.pop("standing", None)
    proposal_payload["evidence"] = [
        {
            **link,
            "stance": _EVIDENCE_STANCE_FROM_STORAGE[
                _evidence_stance_for_storage(link.get("stance"))
            ],
        }
        for link in (payload.get("evidence") or [])
        if isinstance(link, dict)
    ]
    now = _now()
    proposal_id = uuid4().hex
    with _connect(path or KNOWLEDGE_DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO review_proposals
                (id, capability_version, model, scope_json, payload_json,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proposal_id, capability_version, _clean_text(model, 200),
                json.dumps(scope or {}, ensure_ascii=False),
                json.dumps(proposal_payload, ensure_ascii=False), now, now,
            ),
        )
    return {
        "id": proposal_id, "status": "awaiting_review",
        "capability_version": capability_version, "model": model,
        "scope": scope or {}, "payload": proposal_payload,
        "created_at": now, "updated_at": now,
    }


def list_claim_proposals(path: Path | None = None) -> list[dict[str, Any]]:
    with _connect(path or KNOWLEDGE_DB_PATH) as connection:
        rows = connection.execute(
            """
            SELECT * FROM review_proposals
            WHERE proposal_type = 'claim' AND status = 'awaiting_review'
            ORDER BY updated_at DESC
            """
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["scope"] = json.loads(item.pop("scope_json"))
            item["payload"] = json.loads(item.pop("payload_json"))
            payload = item["payload"]
            payload["basis"] = _CLAIM_BASIS_FROM_STORAGE[
                _claim_basis_for_storage(payload.get("basis"))
            ]
            payload.pop("standing", None)
            payload["evidence"] = [
                {
                    **link,
                    "stance": _EVIDENCE_STANCE_FROM_STORAGE[
                        _evidence_stance_for_storage(link.get("stance"))
                    ],
                }
                for link in (payload.get("evidence") or [])
                if isinstance(link, dict)
            ]
        except (TypeError, json.JSONDecodeError):
            item["scope"], item["payload"] = {}, {}
        result.append(item)
    return result


def accept_claim_proposal(
    proposal_id: str, edits: dict[str, Any] | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    database_path = path or KNOWLEDGE_DB_PATH
    with _connect(database_path) as connection:
        row = connection.execute(
            "SELECT * FROM review_proposals WHERE id = ? AND status = 'awaiting_review'",
            (proposal_id,),
        ).fetchone()
    if row is None:
        raise ValueError("Proposal not found")
    try:
        proposal_payload = json.loads(row["payload_json"])
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("Proposal payload is invalid") from error
    accepted_payload = {**proposal_payload, **(edits or {})}
    accepted_payload.update({
        "created_via": "ai_assisted",
        "created_by": "user",
        "capability_version": row["capability_version"],
        "model": row["model"],
    })
    claim = create_claim(accepted_payload, database_path)
    discard_claim_proposal(proposal_id, database_path)
    return claim


def discard_claim_proposal(proposal_id: str, path: Path | None = None) -> bool:
    with _connect(path or KNOWLEDGE_DB_PATH) as connection:
        cursor = connection.execute(
            "DELETE FROM review_proposals WHERE id = ?", (proposal_id,)
        )
    return cursor.rowcount > 0


def _view_payload(connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    claim_rows = connection.execute(
        """
        SELECT claims.*, view_claims.ordinal
        FROM view_claims
        JOIN claims ON claims.id = view_claims.claim_id
        WHERE view_claims.view_id = ?
        ORDER BY view_claims.ordinal
        """,
        (row["id"],),
    ).fetchall()
    claims = []
    for claim_row in claim_rows:
        claim = _claim_payload(connection, claim_row)
        claim["ordinal"] = claim_row["ordinal"]
        claims.append(claim)
    artifact = None
    artifact_id = str(row["artifact_id"] or "")
    if artifact_id:
        artifact_row = connection.execute(
            "SELECT id, title, purpose FROM artifacts WHERE id = ?", (artifact_id,)
        ).fetchone()
        artifact = dict(artifact_row) if artifact_row is not None else None
    block_rows = connection.execute(
        "SELECT id, block_type, content, claim_id, ordinal "
        "FROM view_blocks WHERE view_id = ? ORDER BY ordinal",
        (row["id"],),
    ).fetchall()
    payload = dict(row)
    graph_state_raw = payload.pop("graph_state_json", "{}")
    try:
        graph_state = json.loads(graph_state_raw or "{}")
    except json.JSONDecodeError:
        graph_state = {}
    return {
        **payload,
        "artifact": artifact,
        "claims": claims,
        "blocks": [dict(item) for item in block_rows],
        "graph_state": graph_state if isinstance(graph_state, dict) else {},
    }


def _normalize_view_blocks(
    raw_blocks: Any, claim_ids: list[str], view_type: str, purpose: str
) -> list[dict[str, str]]:
    if view_type == "graph":
        return []
    if raw_blocks is None:
        blocks: list[dict[str, str]] = [{
            "id": uuid4().hex,
            "block_type": "heading",
            "content": "Overview" if view_type == "wiki" else "Article",
            "claim_id": "",
        }]
        if view_type == "article" and purpose:
            blocks.append({
                "id": uuid4().hex,
                "block_type": "paragraph",
                "content": purpose,
                "claim_id": "",
            })
        blocks.extend({
            "id": uuid4().hex,
            "block_type": "claim",
            "content": "",
            "claim_id": claim_id,
        } for claim_id in claim_ids)
        return blocks
    if not isinstance(raw_blocks, list):
        raise ValueError("View blocks must be a list")
    if len(raw_blocks) > 200:
        raise ValueError("A View can contain at most 200 blocks")
    normalized = []
    available_claims = set(claim_ids)
    for raw in raw_blocks:
        if not isinstance(raw, dict):
            raise ValueError("Each View block must be an object")
        block_type = str(raw.get("block_type") or "").strip().lower()
        if block_type not in _VIEW_BLOCK_TYPES:
            raise ValueError("unsupported View block type")
        content = _clean_text(raw.get("content"), 12000)
        claim_id = str(raw.get("claim_id") or "").strip()
        if block_type == "claim":
            if claim_id not in available_claims:
                raise ValueError("View block Claim is not linked to this View")
            content = ""
        elif not content:
            raise ValueError("Heading and paragraph blocks require content")
        normalized.append({
            "id": str(raw.get("id") or uuid4().hex),
            "block_type": block_type,
            "content": content,
            "claim_id": claim_id if block_type == "claim" else "",
        })
    if not normalized:
        raise ValueError("Wiki and Article Views require at least one block")
    return normalized


def _replace_view_blocks(
    connection: sqlite3.Connection, view_id: str,
    blocks: list[dict[str, str]], now: str,
) -> None:
    connection.execute("DELETE FROM view_blocks WHERE view_id = ?", (view_id,))
    connection.executemany(
        "INSERT INTO view_blocks "
        "(id, view_id, block_type, content, claim_id, ordinal, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, NULLIF(?, ''), ?, ?, ?)",
        [
            (
                block["id"], view_id, block["block_type"], block["content"],
                block["claim_id"], ordinal, now, now,
            )
            for ordinal, block in enumerate(blocks)
        ],
    )


def list_views(path: Path | None = None) -> list[dict[str, Any]]:
    with _connect(path or KNOWLEDGE_DB_PATH) as connection:
        rows = connection.execute(
            "SELECT * FROM views ORDER BY updated_at DESC"
        ).fetchall()
        return [_view_payload(connection, row) for row in rows]


def get_view(view_id: str, path: Path | None = None) -> dict[str, Any]:
    with _connect(path or KNOWLEDGE_DB_PATH) as connection:
        row = connection.execute("SELECT * FROM views WHERE id = ?", (view_id,)).fetchone()
        if row is None:
            raise ValueError("View not found")
        return _view_payload(connection, row)


def create_view(payload: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    database_path = path or KNOWLEDGE_DB_PATH
    title = _clean_text(payload.get("title"), 200)
    if not title:
        raise ValueError("View title is required")
    view_type = str(payload.get("view_type") or "wiki").strip().lower()
    if view_type not in _VIEW_TYPES:
        raise ValueError("unsupported View type")
    purpose = _clean_text(payload.get("purpose"), 2000)
    if not purpose:
        raise ValueError("View purpose is required")
    claim_ids = payload.get("claim_ids") or []
    if not isinstance(claim_ids, list):
        raise ValueError("View Claim links must be a list")
    claim_ids = list(dict.fromkeys(str(item) for item in claim_ids if item))
    if not claim_ids:
        raise ValueError("Select at least one Claim for the View")
    artifact_id = str(payload.get("artifact_id") or "").strip()
    graph_state = payload.get("graph_state") or {}
    if not isinstance(graph_state, dict):
        raise ValueError("Graph state must be an object")
    blocks = _normalize_view_blocks(payload.get("blocks"), claim_ids, view_type, purpose)
    now = _now()
    view_id = uuid4().hex
    with _connect(database_path) as connection:
        found = {
            row["id"] for row in connection.execute(
                f"SELECT id FROM claims WHERE id IN ({','.join('?' for _ in claim_ids)})",
                claim_ids,
            ).fetchall()
        }
        if len(found) != len(claim_ids):
            raise ValueError("Claim not found")
        if artifact_id and connection.execute(
            "SELECT id FROM artifacts WHERE id = ?", (artifact_id,)
        ).fetchone() is None:
            raise ValueError("Project not found")
        connection.execute(
            """
            INSERT INTO views
                (id, title, view_type, purpose, artifact_id, graph_state_json,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                view_id, title, view_type,
                purpose, artifact_id, json.dumps(graph_state), now, now,
            ),
        )
        connection.executemany(
            """
            INSERT INTO view_claims (view_id, claim_id, ordinal, added_at)
            VALUES (?, ?, ?, ?)
            """,
            [
                (view_id, claim_id, ordinal, now)
                for ordinal, claim_id in enumerate(claim_ids)
            ],
        )
        _replace_view_blocks(connection, view_id, blocks, now)
        row = connection.execute("SELECT * FROM views WHERE id = ?", (view_id,)).fetchone()
        return _view_payload(connection, row)


def update_view(
    view_id: str, payload: dict[str, Any], path: Path | None = None
) -> dict[str, Any]:
    database_path = path or KNOWLEDGE_DB_PATH
    with _connect(database_path) as connection:
        current = connection.execute(
            "SELECT * FROM views WHERE id = ?", (view_id,)
        ).fetchone()
        if current is None:
            raise ValueError("View not found")
        title = _clean_text(payload.get("title", current["title"]), 200)
        if not title:
            raise ValueError("View title is required")
        view_type = str(payload.get("view_type", current["view_type"])).strip().lower()
        if view_type not in _VIEW_TYPES:
            raise ValueError("unsupported View type")
        purpose = _clean_text(payload.get("purpose", current["purpose"]), 2000)
        if not purpose:
            raise ValueError("View purpose is required")
        artifact_id = str(payload.get("artifact_id", current["artifact_id"]) or "").strip()
        if artifact_id and connection.execute(
            "SELECT id FROM artifacts WHERE id = ?", (artifact_id,)
        ).fetchone() is None:
            raise ValueError("Project not found")
        claim_ids = payload.get("claim_ids")
        if claim_ids is not None:
            if not isinstance(claim_ids, list):
                raise ValueError("View Claim links must be a list")
            claim_ids = list(dict.fromkeys(str(item) for item in claim_ids if item))
            if not claim_ids:
                raise ValueError("Select at least one Claim for the View")
            found = {
                row["id"] for row in connection.execute(
                    f"SELECT id FROM claims WHERE id IN ({','.join('?' for _ in claim_ids)})",
                    claim_ids,
                ).fetchall()
            }
            if len(found) != len(claim_ids):
                raise ValueError("Claim not found")
            connection.execute("DELETE FROM view_claims WHERE view_id = ?", (view_id,))
            now = _now()
            connection.executemany(
                "INSERT INTO view_claims (view_id, claim_id, ordinal, added_at) "
                "VALUES (?, ?, ?, ?)",
                [(view_id, claim_id, ordinal, now) for ordinal, claim_id in enumerate(claim_ids)],
            )
        else:
            claim_ids = [
                row["claim_id"] for row in connection.execute(
                    "SELECT claim_id FROM view_claims WHERE view_id = ? ORDER BY ordinal",
                    (view_id,),
                ).fetchall()
            ]
        if "blocks" in payload or view_type != current["view_type"]:
            blocks = _normalize_view_blocks(
                payload.get("blocks"), claim_ids, view_type, purpose
            )
            _replace_view_blocks(connection, view_id, blocks, _now())
        graph_state = payload.get("graph_state")
        if graph_state is None:
            try:
                graph_state = json.loads(current["graph_state_json"] or "{}")
            except (json.JSONDecodeError, KeyError):
                graph_state = {}
        if not isinstance(graph_state, dict):
            raise ValueError("Graph state must be an object")
        now = _now()
        connection.execute(
            "UPDATE views SET title = ?, view_type = ?, purpose = ?, artifact_id = ?, graph_state_json = ?, "
            "updated_at = ? WHERE id = ?",
            (title, view_type, purpose, artifact_id, json.dumps(graph_state), now, view_id),
        )
        row = connection.execute("SELECT * FROM views WHERE id = ?", (view_id,)).fetchone()
        return _view_payload(connection, row)


def delete_view(view_id: str, path: Path | None = None) -> bool:
    with _connect(path or KNOWLEDGE_DB_PATH) as connection:
        cursor = connection.execute("DELETE FROM views WHERE id = ?", (view_id,))
    return cursor.rowcount > 0


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
