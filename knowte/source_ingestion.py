"""Atomically promote selected discovery receipts into durable Sources."""
from __future__ import annotations

import json

from .automation import _database
from .knowledge import _connect, canonical_source_key, save_source


def ingest_run(run_id, path):
    # Schema initialization must finish before the ingestion write transaction.
    connection = _connect(path)
    connection.close()
    from .plan_runs import _aliases

    with _database(path) as connection:
        previous = connection.execute("SELECT report_json FROM run_ingestion WHERE run_id = ?", (run_id,)).fetchone()
        if previous:
            return json.loads(previous[0])
        row = connection.execute("SELECT config_json FROM run_processing_policy WHERE run_id = ?", (run_id,)).fetchone()
        policy = json.loads(row[0]) if row else {"save_sources": False}
        report = {"sources_created": 0, "sources_reused": 0, "deferred": 0, "enabled": policy["save_sources"]}
        if policy["save_sources"]:
            aliases = {}
            for source in connection.execute("SELECT * FROM sources ORDER BY created_at, id"):
                original = json.loads(source["payload_json"])
                current = {**original, "title": source["title"], "authors": source["authors"],
                           **{field: source[field] for field in ("url", "paper_url", "pdf_url", "doi_url")}}
                for alias in [source["canonical_key"], *_aliases(original), *_aliases(current)]:
                    aliases.setdefault(alias, source["id"])
            # Selected overflow survives runs. Already ingested items only add new
            # discovery paths; deleting a Source must not resurrect it each day.
            pending = connection.execute("""SELECT s.* FROM plan_action_seen s
                WHERE s.plan_action_id IN (SELECT plan_action_id FROM action_runs WHERE run_id = ?)
                AND (s.processing_status = 'selected' OR
                    (s.processing_status = 'ingested' AND s.last_seen_run = ?))
                ORDER BY s.rowid""", (run_id, run_id)).fetchall()
            deferred = set()
            for item in pending:
                payload = json.loads(item["metadata_json"])
                keys = [item["canonical_key"], canonical_source_key(payload), *_aliases(payload)]
                # The global ledger may know identity aliases absent in the first
                # provider's metadata (e.g. a later DOI enrichment).
                keys.extend(row[0] for row in connection.execute("SELECT alias FROM seen_item_aliases WHERE canonical_key = ?", (item["canonical_key"],)))
                source_id = next((aliases[key] for key in keys if key in aliases), None)
                if item["processing_status"] == "ingested" and not source_id:
                    continue
                if not source_id and report["sources_created"] >= policy["max_new_sources"]:
                    deferred.add(item["canonical_key"])
                    continue
                source, created, _ = save_source(payload, path=path, _connection=connection,
                    _existing_id=source_id, preserve_existing=True)
                source_id = source["id"]
                for key in keys:
                    aliases.setdefault(key, source_id)
                added = connection.execute("INSERT OR IGNORE INTO run_sources VALUES (?, ?, ?)", (run_id, source_id, int(created))).rowcount
                if added:
                    report["sources_created" if created else "sources_reused"] += 1
                origins = connection.execute("""SELECT o.action_run_id, o.provider FROM run_item_origins o
                    JOIN action_runs a ON a.id = o.action_run_id
                    WHERE a.plan_action_id = ? AND o.canonical_key = ?""",
                    (item["plan_action_id"], item["canonical_key"])).fetchall()
                for origin in origins:
                    connection.execute("INSERT OR IGNORE INTO source_discoveries VALUES (?, ?, ?, ?, ?)",
                        (source_id, origin["action_run_id"], item["canonical_key"], origin["provider"], run_id))
                connection.execute("UPDATE plan_action_seen SET processing_status = 'ingested' WHERE plan_action_id = ? AND canonical_key = ?",
                    (item["plan_action_id"], item["canonical_key"]))
            report["deferred"] = len(deferred)
        connection.execute("INSERT INTO run_ingestion VALUES (?, ?)", (run_id, json.dumps(report)))
        return report


def source_discoveries(source_id, path):
    with _database(path) as connection:
        rows = connection.execute("""SELECT d.provider, d.ingestion_run_id, a.id AS action_run_id,
            a.action_name, a.action_version, a.config_snapshot, r.id AS run_id,
            r.plan_id, r.plan_name, r.started_at
            FROM source_discoveries d JOIN action_runs a ON a.id = d.action_run_id
            JOIN plan_runs r ON r.id = a.run_id WHERE d.source_id = ?
            ORDER BY r.started_at DESC, a.position""", (source_id,)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            config = json.loads(item.pop("config_snapshot"))
            item["kind"] = config.get("kind", "search")
            item["channel"] = next((channel["name"] for channel in config.get("subscriptions", [])
                                    if channel["id"] == item["provider"]), None)
            result.append(item)
        return result


def source_feed_content(source_id, path):
    """Recover feed text from older persisted subscription receipts, without refetching."""
    with _database(path) as connection:
        rows = connection.execute("""SELECT s.metadata_json, a.config_snapshot FROM source_discoveries d
            JOIN action_runs a ON a.id = d.action_run_id
            JOIN plan_action_seen s ON s.plan_action_id = a.plan_action_id AND s.canonical_key = d.canonical_key
            WHERE d.source_id = ? ORDER BY a.rowid DESC""", (source_id,)).fetchall()
        for row in rows:
            if json.loads(row["config_snapshot"]).get("kind") != "subscribe":
                continue
            item = json.loads(row["metadata_json"])
            if item.get("feed_content"):
                return item["feed_content"]
            if item.get("abstract"):
                return {"text": item["abstract"], "scope": "Subscription-provided excerpt; complete article coverage is not guaranteed"}
    return {}
