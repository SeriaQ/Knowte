"""Reusable acquisition definitions; execution state belongs to PlanAction."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from .plans import _clean, _now
from .scheduler import clean_schedule, next_due
from datetime import datetime, timezone


@contextmanager
def _database(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS automation_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL UNIQUE,
                etag TEXT NOT NULL DEFAULT '', last_modified TEXT NOT NULL DEFAULT '',
                last_fetched_at TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS subscription_items (
                subscription_id TEXT NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
                item_key TEXT NOT NULL, metadata_json TEXT NOT NULL, first_seen_at TEXT NOT NULL,
                PRIMARY KEY(subscription_id, item_key)
            );
            CREATE TABLE IF NOT EXISTS subscription_connections (
                subscription_id TEXT PRIMARY KEY REFERENCES subscriptions(id) ON DELETE CASCADE,
                channel_key TEXT NOT NULL UNIQUE, spec_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS subscribe_action_subscriptions (
                action_id TEXT NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
                subscription_id TEXT NOT NULL REFERENCES subscriptions(id),
                PRIMARY KEY(action_id, subscription_id)
            );
            CREATE TABLE IF NOT EXISTS actions (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL,
                version INTEGER NOT NULL, config_json TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS plans (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, enabled INTEGER NOT NULL,
                schedule_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS plan_schedule_state (
                plan_id TEXT PRIMARY KEY REFERENCES plans(id) ON DELETE CASCADE,
                next_due_at TEXT, pending INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS plan_actions (
                id TEXT PRIMARY KEY, plan_id TEXT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
                action_id TEXT NOT NULL REFERENCES actions(id), position INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1, execution_state TEXT NOT NULL DEFAULT '{}',
                UNIQUE(plan_id, action_id)
            );
            CREATE TABLE IF NOT EXISTS plan_runs (
                id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, plan_name TEXT NOT NULL,
                trigger TEXT NOT NULL, status TEXT NOT NULL, owner_pid INTEGER NOT NULL,
                started_at TEXT NOT NULL, finished_at TEXT, error TEXT NOT NULL DEFAULT ''
            );
            CREATE UNIQUE INDEX IF NOT EXISTS plan_single_run ON plan_runs(plan_id)
                WHERE status IN ('queued', 'running');
            CREATE TABLE IF NOT EXISTS action_runs (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES plan_runs(id),
                plan_action_id TEXT NOT NULL, action_id TEXT NOT NULL, action_name TEXT NOT NULL,
                action_version INTEGER NOT NULL, config_snapshot TEXT NOT NULL,
                checkpoint_before TEXT NOT NULL, checkpoint_after TEXT NOT NULL,
                position INTEGER NOT NULL, status TEXT NOT NULL, report TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS seen_items (
                canonical_key TEXT PRIMARY KEY, first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS seen_item_aliases (
                alias TEXT PRIMARY KEY, canonical_key TEXT NOT NULL REFERENCES seen_items(canonical_key)
            );
            CREATE TABLE IF NOT EXISTS plan_action_seen (
                plan_action_id TEXT NOT NULL, canonical_key TEXT NOT NULL REFERENCES seen_items(canonical_key),
                first_seen_run TEXT NOT NULL, last_seen_run TEXT NOT NULL,
                metadata_json TEXT NOT NULL, processing_status TEXT NOT NULL DEFAULT 'pending',
                PRIMARY KEY(plan_action_id, canonical_key)
            );
            CREATE TABLE IF NOT EXISTS run_items (
                run_id TEXT NOT NULL, action_run_id TEXT NOT NULL, canonical_key TEXT NOT NULL,
                metadata_json TEXT NOT NULL, is_new INTEGER NOT NULL, disposition TEXT NOT NULL,
                PRIMARY KEY(action_run_id, canonical_key)
            );
            CREATE TABLE IF NOT EXISTS run_item_origins (
                action_run_id TEXT NOT NULL, canonical_key TEXT NOT NULL, provider TEXT NOT NULL,
                PRIMARY KEY(action_run_id, canonical_key, provider)
            );
            CREATE TABLE IF NOT EXISTS plan_processing_policy (
                plan_id TEXT PRIMARY KEY REFERENCES plans(id) ON DELETE CASCADE,
                config_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS run_processing_policy (
                run_id TEXT PRIMARY KEY REFERENCES plan_runs(id), config_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS run_sources (
                run_id TEXT NOT NULL REFERENCES plan_runs(id), source_id TEXT NOT NULL,
                was_created INTEGER NOT NULL, PRIMARY KEY(run_id, source_id)
            );
            CREATE TABLE IF NOT EXISTS source_discoveries (
                source_id TEXT NOT NULL, action_run_id TEXT NOT NULL REFERENCES action_runs(id),
                canonical_key TEXT NOT NULL, provider TEXT NOT NULL,
                ingestion_run_id TEXT NOT NULL REFERENCES plan_runs(id),
                PRIMARY KEY(source_id, action_run_id, canonical_key, provider)
            );
            CREATE TABLE IF NOT EXISTS run_ingestion (
                run_id TEXT PRIMARY KEY REFERENCES plan_runs(id), report_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS plan_generation_jobs (
                id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, first_run_id TEXT NOT NULL,
                last_run_id TEXT NOT NULL, source_ids_json TEXT NOT NULL,
                policy_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
                report_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS plan_source_jobs (
                plan_id TEXT NOT NULL, source_id TEXT NOT NULL, job_id TEXT NOT NULL,
                PRIMARY KEY(plan_id, source_id)
            );
            CREATE TABLE IF NOT EXISTS generation_attempts (
                run_id TEXT NOT NULL, job_id TEXT NOT NULL, status TEXT NOT NULL,
                report_json TEXT NOT NULL DEFAULT '{}', PRIMARY KEY(run_id, job_id)
            );
            CREATE TABLE IF NOT EXISTS plan_claim_jobs (
                id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, first_run_id TEXT NOT NULL,
                input_refs_json TEXT NOT NULL, policy_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued', report_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS plan_claim_inputs (
                plan_id TEXT NOT NULL, proposal_id TEXT NOT NULL, job_id TEXT NOT NULL,
                PRIMARY KEY(plan_id, proposal_id)
            );
            CREATE TABLE IF NOT EXISTS plan_relation_jobs (
                id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, first_run_id TEXT NOT NULL,
                input_refs_json TEXT NOT NULL, policy_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued', report_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS plan_wiki_jobs (
                id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, first_run_id TEXT NOT NULL,
                policy_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
                report_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS plan_relation_inputs (
                plan_id TEXT NOT NULL, proposal_id TEXT NOT NULL,
                PRIMARY KEY(plan_id, proposal_id)
            );
        """)
        # Serialize read-modify-write operations, including migration.
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def search_settings(payload: dict[str, Any]) -> dict[str, int]:
    limits = {"max_papers": 1000, "intelligent_max_results": 100,
              "ai_verify_batch_size": 20, "ai_verify_concurrency": 8,
              "ai_search_timeout_seconds": 3600}
    result = {}
    for key, maximum in limits.items():
        if key not in payload:
            continue
        value = payload[key]
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
            raise ValueError(f"{key} must be between 1 and {maximum}")
        result[key] = value
    return result


def _search_config(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Search configuration must be an object")
    cleaned = _clean(payload)
    config = {key: cleaned[key] for key in (
        "query", "mode", "areas", "year_from", "year_to", "sources", "search_actions",
    )}
    # Only explicitly allowed behavior is stored; never profiles, keys or endpoints.
    config.update(search_settings(payload))
    if "model_profile_id" in payload:
        config["model_profile_id"] = str(payload["model_profile_id"])[:128]
    return config


def _action_config(connection, payload, kind):
    if kind == "search":
        return _search_config(payload)
    if kind != "subscribe" or not isinstance(payload, dict):
        raise ValueError("Choose Search or Subscribe")
    ids = payload.get("subscription_ids")
    if not isinstance(ids, list) or not ids or any(not isinstance(item, str) for item in ids):
        raise ValueError("Choose at least one Subscription")
    for item in ids:
        if not connection.execute("SELECT 1 FROM subscriptions WHERE id = ?", (item,)).fetchone():
            raise ValueError("A selected Subscription no longer exists")
    focus = str(payload.get("query") or "").strip()[:2000]
    model = str(payload.get("model_profile_id") or "")[:128]
    mode = "intelligent" if payload.get("mode") == "intelligent" else "keyword"
    if mode == "intelligent" and (not focus or not model):
        raise ValueError("Channel AI Verify requires Focus and a model")
    return {"subscription_ids": list(dict.fromkeys(ids)), "mode": mode, "query": focus, "model_profile_id": model}


def _link_subscriptions(connection, action_id, config):
    connection.execute("DELETE FROM subscribe_action_subscriptions WHERE action_id = ?", (action_id,))
    for item in config.get("subscription_ids", []):
        connection.execute("INSERT INTO subscribe_action_subscriptions VALUES (?, ?)", (action_id, item))


def _insert_action(connection, payload, action_id=None):
    kind = payload.get("kind", "search")
    config = _action_config(connection, payload.get("config", payload), kind)
    name = str(payload.get("name") or config.get("query") or "Subscriptions").strip()[:120]
    action_id = action_id or uuid4().hex
    now = _now()
    connection.execute("INSERT INTO actions VALUES (?, ?, ?, 1, ?, ?, ?)",
                       (action_id, name, kind, json.dumps(config), now, now))
    _link_subscriptions(connection, action_id, config)
    return action_id


def processing_policy(connection, plan_id):
    row = connection.execute("SELECT config_json FROM plan_processing_policy WHERE plan_id = ?", (plan_id,)).fetchone()
    # Previously saved schedules must not acquire a new side effect on upgrade.
    return json.loads(row[0]) if row else {"save_sources": False, "max_new_sources": 20}


def _save_plan(connection, payload, plan_id=None):
    existing = connection.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone() if plan_id else None
    if plan_id and not existing:
        raise ValueError("Plan not found")
    if plan_id and any(key in payload for key in ("name", "action_ids", "schedule", "processing")) and connection.execute("SELECT 1 FROM plan_runs WHERE plan_id = ? AND status IN ('queued', 'running')", (plan_id,)).fetchone():
        raise ValueError("Wait for the active Run to finish before editing this Plan")
    name = str(payload.get("name", existing["name"] if existing else "")).strip()[:120]
    if not name:
        raise ValueError("Plan name is required")
    enabled = payload.get("enabled", bool(existing["enabled"]) if existing else True)
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean")
    schedule = clean_schedule(payload.get("schedule", json.loads(existing["schedule_json"]) if existing else {"type": "manual"}))
    policy = payload.get("processing", processing_policy(connection, plan_id) if existing else {"save_sources": True, "max_new_sources": 20})
    if not isinstance(policy, dict) or not {"save_sources", "max_new_sources"} <= set(policy) or set(policy) - {"save_sources", "max_new_sources", "evidence", "claims", "relations", "wiki"}:
        raise ValueError("Processing requires save_sources and max_new_sources")
    if not isinstance(policy["save_sources"], bool) or type(policy["max_new_sources"]) is not int or not 1 <= policy["max_new_sources"] <= 1000:
        raise ValueError("Choose whether to save Sources and a maximum from 1 to 1000")
    if "evidence" in policy:
        stage = policy["evidence"]
        if not isinstance(stage, dict) or set(stage) != {"enabled", "focus", "model_profile_id"} or not isinstance(stage["enabled"], bool):
            raise ValueError("Evidence processing requires enabled, focus and model_profile_id")
        if not isinstance(stage["focus"], str) or len(stage["focus"]) > 2000 or not isinstance(stage["model_profile_id"], str) or len(stage["model_profile_id"]) > 80:
            raise ValueError("Invalid Evidence focus or model profile")
        if stage["enabled"] and (not policy["save_sources"] or not stage["model_profile_id"]):
            raise ValueError("Evidence generation requires Source saving and an explicit model")
    if "claims" in policy:
        stage = policy["claims"]
        if not isinstance(stage, dict) or set(stage) != {"enabled", "focus", "model_profile_id"} or not isinstance(stage["enabled"], bool):
            raise ValueError("Claim processing requires enabled, focus and model_profile_id")
        if not isinstance(stage["focus"], str) or len(stage["focus"]) > 2000 or not isinstance(stage["model_profile_id"], str) or len(stage["model_profile_id"]) > 80:
            raise ValueError("Invalid Claim focus or model profile")
        if stage["enabled"] and (not policy.get("evidence", {}).get("enabled") or not stage["model_profile_id"]):
            raise ValueError("Claim generation requires Evidence generation and an explicit model")
    for stage_name in ("relations", "wiki"):
        if stage_name not in policy:
            continue
        stage = policy[stage_name]
        if (not isinstance(stage, dict) or set(stage) != {"enabled", "model_profile_id"}
                or not isinstance(stage["enabled"], bool) or not isinstance(stage["model_profile_id"], str)
                or len(stage["model_profile_id"]) > 80):
            raise ValueError(f"{stage_name} processing requires enabled and model_profile_id")
        if stage["enabled"] and (not policy.get("claims", {}).get("enabled") or not stage["model_profile_id"]):
            raise ValueError(f"{stage_name} generation requires Claim generation and an explicit model")
    current = connection.execute("SELECT action_id FROM plan_actions WHERE plan_id = ? ORDER BY position", (plan_id,)).fetchall()
    ids = payload.get("action_ids", [row["action_id"] for row in current])
    if not isinstance(ids, list) or any(not isinstance(item, str) for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("Choose each Action only once")
    for action_id in ids:
        if not connection.execute("SELECT 1 FROM actions WHERE id = ?", (action_id,)).fetchone():
            raise ValueError("An Action no longer exists; reload the Action Library")
    if enabled and schedule["type"] != "manual" and not ids:
        raise ValueError("Add an Action before enabling a schedule")
    now = _now()
    plan_id = plan_id or uuid4().hex
    if existing:
        connection.execute("UPDATE plans SET name = ?, enabled = ?, schedule_json = ?, updated_at = ? WHERE id = ?", (name, enabled, json.dumps(schedule), now, plan_id))
    else:
        connection.execute("INSERT INTO plans VALUES (?, ?, ?, ?, ?, ?)",
                           (plan_id, name, enabled, json.dumps(schedule), now, now))
    connection.execute("INSERT INTO plan_processing_policy VALUES (?, ?) ON CONFLICT(plan_id) DO UPDATE SET config_json = excluded.config_json", (plan_id, json.dumps(policy)))
    if not existing or json.loads(existing["schedule_json"]) != schedule or bool(existing["enabled"]) != enabled:
        due = next_due(schedule, datetime.now(timezone.utc)) if enabled else None
        connection.execute("INSERT INTO plan_schedule_state VALUES (?, ?, 0) ON CONFLICT(plan_id) DO UPDATE SET next_due_at = excluded.next_due_at, pending = 0", (plan_id, due.isoformat() if due else None))
    # Retain the same association IDs and checkpoints when reordering/editing.
    for row in current:
        if row["action_id"] not in ids:
            connection.execute("DELETE FROM plan_actions WHERE plan_id = ? AND action_id = ?", (plan_id, row["action_id"]))
    for position, action_id in enumerate(ids):
        connection.execute("""INSERT INTO plan_actions (id, plan_id, action_id, position)
            VALUES (?, ?, ?, ?) ON CONFLICT(plan_id, action_id) DO UPDATE SET position = excluded.position""",
                           (uuid4().hex, plan_id, action_id, position))
    return plan_id


def _migrate(connection, legacy_path):
    if connection.execute("SELECT 1 FROM automation_meta WHERE key = 'legacy_plans_v1'").fetchone():
        return
    old = []
    if legacy_path and legacy_path.exists():
        try:
            old = json.loads(legacy_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ValueError("Cannot migrate plans.json. The original file is unchanged; repair it before retrying.") from error
        if not isinstance(old, list):
            raise ValueError("Cannot migrate plans.json: expected a list. The original file is unchanged.")
    for index, payload in enumerate(old):
        try:
            if not isinstance(payload, dict):
                raise ValueError("expected an object")
            action_id = _insert_action(connection, payload)
            _save_plan(connection, {"name": payload.get("name") or payload.get("query"), "action_ids": [action_id], "processing": {"save_sources": False, "max_new_sources": 20}})
        except (TypeError, ValueError) as error:
            raise ValueError(f"Cannot migrate saved Plan {index + 1}: {error}. Nothing was migrated; original file unchanged.") from error
    connection.execute("INSERT INTO automation_meta VALUES ('legacy_plans_v1', ?)", (json.dumps({"count": len(old), "at": _now()}),))


def _catalog(connection):
    plans = []
    for row in connection.execute("SELECT * FROM plans ORDER BY updated_at DESC, id"):
        plan = dict(row)
        plan["enabled"] = bool(plan["enabled"])
        plan["schedule"] = json.loads(plan.pop("schedule_json"))
        plan["processing"] = processing_policy(connection, plan["id"])
        state = connection.execute("SELECT next_due_at, pending FROM plan_schedule_state WHERE plan_id = ?", (plan["id"],)).fetchone()
        plan["next_run"] = state["next_due_at"] if state else None
        plan["run_pending"] = bool(state["pending"]) if state else False
        plan["actions"] = [dict(item) for item in connection.execute(
            "SELECT id, action_id, position, enabled FROM plan_actions WHERE plan_id = ? ORDER BY position", (plan["id"],))]
        last = connection.execute("SELECT id, status, started_at, finished_at FROM plan_runs WHERE plan_id = ? ORDER BY started_at DESC, rowid DESC LIMIT 1", (plan["id"],)).fetchone()
        plan["last_run"] = dict(last) if last else None
        plans.append(plan)
    actions = []
    for row in connection.execute("SELECT * FROM actions ORDER BY updated_at DESC, id"):
        action = dict(row)
        action["config"] = json.loads(action.pop("config_json"))
        action["used_by"] = [{"id": plan["id"], "name": plan["name"]} for plan in plans
                             if any(item["action_id"] == action["id"] for item in plan["actions"])]
        actions.append(action)
    migration = connection.execute("SELECT value FROM automation_meta WHERE key = 'legacy_plans_v1'").fetchone()
    return {"plans": plans, "actions": actions, "migration": json.loads(migration["value"])}


def catalog(path: Path, legacy_path: Path | None = None):
    with _database(path) as connection:
        _migrate(connection, legacy_path)
        for channel in connection.execute("SELECT id, name FROM subscriptions").fetchall():
            ensure_channel_action(connection, channel["id"], channel["name"])
        return _catalog(connection)


def ensure_channel_action(connection, channel_id, name):
    # Stable internal adapter: users select the Channel itself, with existing
    # PlanAction checkpoints and Run snapshots retaining their usual semantics.
    action_id = "channel-" + channel_id
    if not connection.execute("SELECT 1 FROM actions WHERE id = ?", (action_id,)).fetchone():
        _insert_action(connection, {"kind": "subscribe", "name": name,
                       "config": {"subscription_ids": [channel_id]}}, action_id)
    return action_id


def mutate(payload: dict[str, Any], path: Path, legacy_path: Path | None = None):
    if not isinstance(payload, dict):
        raise ValueError("Expected an object")
    with _database(path) as connection:
        _migrate(connection, legacy_path)
        operation = payload.get("operation")
        item_id = payload.get("id")
        if operation == "import_plan":
            action_id = _insert_action(connection, payload)
            item_id = _save_plan(connection, {"name": payload.get("name") or payload["config"]["query"], "action_ids": [action_id]})
        elif operation == "save_action":
            if item_id:
                row = connection.execute("SELECT * FROM actions WHERE id = ?", (item_id,)).fetchone()
                if not row:
                    raise ValueError("Action not found")
                if payload.get("version") != row["version"]:
                    raise ValueError("This Action changed. Reload before saving.")
                if payload.get("kind", row["kind"]) != row["kind"]:
                    raise ValueError("An Action's type cannot be changed")
                config = _action_config(connection, payload.get("config", json.loads(row["config_json"])), row["kind"])
                name = str(payload.get("name", row["name"])).strip()[:120]
                if not name:
                    raise ValueError("Action name is required")
                connection.execute("UPDATE actions SET name = ?, config_json = ?, version = version + 1, updated_at = ? WHERE id = ?",
                                   (name, json.dumps(config), _now(), item_id))
                _link_subscriptions(connection, item_id, config)
            else:
                item_id = _insert_action(connection, payload)
            if payload.get("plan_id"):
                plan_id = payload["plan_id"]
                ids = [row["action_id"] for row in connection.execute("SELECT action_id FROM plan_actions WHERE plan_id = ? ORDER BY position", (plan_id,))]
                _save_plan(connection, {"action_ids": list(dict.fromkeys(ids + [item_id]))}, plan_id)
        elif operation == "save_plan":
            item_id = _save_plan(connection, payload, item_id)
        elif operation == "delete_action":
            if connection.execute("SELECT 1 FROM plan_actions WHERE action_id = ?", (item_id,)).fetchone():
                raise ValueError("Remove this Action from its Plans before deleting it")
            if not connection.execute("DELETE FROM actions WHERE id = ?", (item_id,)).rowcount:
                raise ValueError("Action not found")
        elif operation == "delete_plan":
            if connection.execute("SELECT 1 FROM plan_runs WHERE plan_id = ? AND status IN ('queued', 'running')", (item_id,)).fetchone():
                raise ValueError("Wait for the active Run to finish before deleting this Plan")
            if not connection.execute("DELETE FROM plans WHERE id = ?", (item_id,)).rowcount:
                raise ValueError("Plan not found")
        else:
            raise ValueError("Unknown operation")
        result = _catalog(connection)
        result["saved_id"] = item_id
        return result
