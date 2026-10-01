"""Durable manual discovery runs. Network/model work never holds a DB transaction."""
from __future__ import annotations

import json
import os
import threading
from contextlib import nullcontext
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from urllib.error import HTTPError

from .automation import _database, _migrate, search_settings, processing_policy
from .config import load_config, ai_model_profiles
from .knowledge import canonical_source_key
from .plans import _now


def _safe_provider_error(error):
    # Do not include request URLs, headers, or credential-bearing exception text.
    if isinstance(error, HTTPError):
        return f"HTTP {error.code}"
    return type(error).__name__


def _aliases(item):
    without_doi = {**item, "doi_url": ""}
    without_id = {**without_doi, "id": "", "source": ""}
    aliases = [canonical_source_key(value, stable=True) for value in (item, without_doi, without_id)]
    if item.get("title") and item.get("authors"):
        aliases.append(canonical_source_key({"title": " ".join(item["title"].split()),
            "authors": " ".join(str(item["authors"]).split())}, stable=True))
    return list(dict.fromkeys(aliases))


def _identity(connection, item):
    aliases = _aliases(item)
    for alias in aliases:
        found = connection.execute("SELECT canonical_key FROM seen_item_aliases WHERE alias = ?", (alias,)).fetchone()
        if found:
            return found[0], aliases
    return aliases[0], aliases


def queue_run(plan_id, path, legacy_path=None, *, trigger="manual", connection=None, knowledge_only=False):
    with (nullcontext(connection) if connection is not None else _database(path)) as connection:
        _migrate(connection, legacy_path)
        plan = connection.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if not plan:
            raise ValueError("Plan not found")
        active = connection.execute("SELECT id FROM plan_runs WHERE plan_id = ? AND status IN ('queued', 'running')", (plan_id,)).fetchone()
        if active:
            return active["id"], False
        actions = connection.execute("""SELECT pa.id AS association_id, pa.execution_state, pa.position,
            a.* FROM plan_actions pa JOIN actions a ON a.id = pa.action_id
            WHERE pa.plan_id = ? AND pa.enabled = 1 ORDER BY pa.position""", (plan_id,)).fetchall()
        if not actions and not knowledge_only:
            raise ValueError("Add at least one enabled Action before running this Plan")
        policy = processing_policy(connection, plan_id)
        if knowledge_only:
            if not policy.get("claims", {}).get("enabled"):
                raise ValueError("Enable Claim processing in this Plan before recomputing")
            actions = []
            policy = {**policy, "save_sources": False, "evidence": {**policy.get("evidence", {}), "enabled": False}, "knowledge_only": True}
        run_id = uuid4().hex
        connection.execute("INSERT INTO plan_runs (id, plan_id, plan_name, trigger, status, owner_pid, started_at) VALUES (?, ?, ?, ?, 'queued', ?, ?)",
                           (run_id, plan_id, plan["name"], trigger, os.getpid(), _now()))
        connection.execute("INSERT INTO run_processing_policy VALUES (?, ?)", (run_id, json.dumps(policy)))
        for action in actions:
            snapshot = json.loads(action["config_json"])
            snapshot["kind"] = action["kind"]
            if action["kind"] == "subscribe":
                snapshot["subscriptions"] = []
                for item in snapshot["subscription_ids"]:
                    channel = dict(connection.execute("SELECT id, name, url FROM subscriptions WHERE id = ?", (item,)).fetchone())
                    connector = connection.execute("SELECT spec_json FROM subscription_connections WHERE subscription_id = ?", (item,)).fetchone()
                    if connector:
                        channel["connector"] = json.loads(connector[0])
                    snapshot["subscriptions"].append(channel)
            connection.execute("INSERT INTO action_runs (id, run_id, plan_action_id, action_id, action_name, action_version, config_snapshot, checkpoint_before, checkpoint_after, position, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued')",
                (uuid4().hex, run_id, action["association_id"], action["id"], action["name"], action["version"], json.dumps(snapshot), action["execution_state"], action["execution_state"], action["position"]))
        return run_id, True


def recover_interrupted(path):
    """Never steal a run from a living process using the same local library."""
    with _database(path) as connection:
        for row in connection.execute("SELECT id, owner_pid, plan_id, trigger FROM plan_runs WHERE status IN ('queued', 'running')").fetchall():
            try:
                os.kill(row["owner_pid"], 0)
            except ProcessLookupError:
                connection.execute("UPDATE plan_runs SET status = 'failed', finished_at = ?, error = ? WHERE id = ?",
                    (_now(), "Knowte stopped during this Run. Committed acquisition is retained; unprocessed items will be retried next Run. Model requests without saved results may have consumed quota and may repeat.", row["id"]))
                connection.execute("UPDATE action_runs SET status = 'failed' WHERE run_id = ? AND status IN ('queued', 'running')", (row["id"],))
                connection.execute("UPDATE generation_attempts SET status = 'failed', report_json = ? WHERE run_id = ? AND status = 'running'", (json.dumps({"warnings": ["Knowte stopped during generation; saved proposals are retained. The next Run will recover this batch."]}), row["id"]))
                if row["trigger"] != "manual":
                    connection.execute("UPDATE plan_schedule_state SET pending = 1 WHERE plan_id = ?", (row["plan_id"],))
            except PermissionError:
                pass


def list_runs(path, plan_id=None, run_id=None):
    with _database(path) as connection:
        where, args = ("WHERE id = ?", (run_id,)) if run_id else (("WHERE plan_id = ?", (plan_id,)) if plan_id else ("", ()))
        result = []
        for row in connection.execute(f"SELECT * FROM plan_runs {where} ORDER BY started_at DESC, rowid DESC LIMIT 50", args):
            run = dict(row)
            run.pop("owner_pid")
            run["actions"] = []
            for action in connection.execute("SELECT * FROM action_runs WHERE run_id = ? ORDER BY position", (run["id"],)):
                item = dict(action)
                for field in ("config_snapshot", "checkpoint_before", "checkpoint_after", "report"):
                    item[field] = json.loads(item[field])
                run["actions"].append(item)
            run["counts"] = dict(connection.execute("""SELECT count(*) AS retrieved_unique,
                coalesce(sum(is_new), 0) AS new_count,
                coalesce(sum(disposition = 'selected'), 0) AS selected_count,
                coalesce(sum(disposition = 'excluded'), 0) AS excluded_count
                FROM run_items WHERE run_id = ?""", (run["id"],)).fetchone())
            run["counts"]["duplicate_count"] = run["counts"]["retrieved_unique"] - run["counts"]["new_count"]
            policy = connection.execute("SELECT config_json FROM run_processing_policy WHERE run_id = ?", (run["id"],)).fetchone()
            run["processing"] = json.loads(policy[0]) if policy else {"save_sources": False, "max_new_sources": 20}
            ingestion = connection.execute("SELECT report_json FROM run_ingestion WHERE run_id = ?", (run["id"],)).fetchone()
            run["ingestion"] = json.loads(ingestion[0]) if ingestion else None
            run["knowledge_jobs"] = []
            for job in connection.execute("""SELECT j.id, j.plan_id, j.first_run_id, j.source_ids_json, j.policy_json, t.status, t.report_json
                FROM generation_attempts t JOIN plan_generation_jobs j ON j.id = t.job_id WHERE t.run_id = ? ORDER BY t.rowid""", (run["id"],)):
                item = dict(job)
                for field in ("source_ids", "policy", "report"):
                    item[field] = json.loads(item.pop(field + "_json"))
                item["stage"] = "evidence"
                run["knowledge_jobs"].append(item)
            for job in connection.execute("""SELECT j.id, j.plan_id, j.first_run_id, j.input_refs_json, j.policy_json, t.status, t.report_json
                FROM generation_attempts t JOIN plan_claim_jobs j ON j.id = t.job_id WHERE t.run_id = ? ORDER BY t.rowid""", (run["id"],)):
                item = dict(job)
                for field in ("input_refs", "policy", "report"):
                    item[field] = json.loads(item.pop(field + "_json"))
                item["stage"] = "claims"
                run["knowledge_jobs"].append(item)
            for job in connection.execute("""SELECT j.id, j.plan_id, j.first_run_id, j.input_refs_json, j.policy_json, t.status, t.report_json
                FROM generation_attempts t JOIN plan_relation_jobs j ON j.id = t.job_id WHERE t.run_id = ? ORDER BY t.rowid""", (run["id"],)):
                item = dict(job)
                for field in ("input_refs", "policy", "report"):
                    item[field] = json.loads(item.pop(field + "_json"))
                item["stage"] = "relations"
                run["knowledge_jobs"].append(item)
            for job in connection.execute("""SELECT j.id, j.plan_id, j.first_run_id, j.policy_json, t.status, t.report_json
                FROM generation_attempts t JOIN plan_wiki_jobs j ON j.id = t.job_id WHERE t.run_id = ? ORDER BY t.rowid""", (run["id"],)):
                item = dict(job)
                for field in ("policy", "report"):
                    item[field] = json.loads(item.pop(field + "_json"))
                item["stage"] = "wiki"
                run["knowledge_jobs"].append(item)
            if run_id:
                run["sources"] = [dict(item) for item in connection.execute("""SELECT rs.source_id, rs.was_created, s.title
                    FROM run_sources rs LEFT JOIN sources s ON s.id = rs.source_id WHERE rs.run_id = ?""", (run_id,))] if ingestion else []
                run["items"] = [dict(item) for item in connection.execute("SELECT canonical_key, action_run_id, is_new, disposition, metadata_json FROM run_items WHERE run_id = ? ORDER BY rowid", (run_id,))]
                for item in run["items"]:
                    item["metadata"] = json.loads(item.pop("metadata_json"))
            result.append(run)
        return result


def _retrieve(config, provider, runtime, year_from):
    import time
    from .search import search_papers
    from .usage import can_request, record_request
    queries = list(dict.fromkeys(item["query"] for item in config.get("search_actions", [])
                                if item.get("target") in {"academic", "both"})) or [config["query"]]
    results = []
    config["_raw_count"] = 0
    def before_request():
        if not can_request([provider])["allowed_paper"]:
            raise RuntimeError("Paper quota reached")
        time.sleep(3 if provider == "arxiv" else 1)
        record_request([provider])
    for query in queries:
        diagnostics = {}
        results.extend(search_papers(query, limit=min(100, max(8, config.get("max_papers", 100))),
            email=runtime.get("email"), semanticscholar_key=runtime.get("semanticscholar_api_key"),
            areas=config.get("areas", []), backends=[provider], year_from=year_from,
            year_to=config.get("year_to"), strict_match=config.get("mode") != "intelligent",
            raise_provider_errors=True, academic_page=config.get("_page", 0), diagnostics=diagnostics,
            before_provider_request=before_request))
        config["_raw_count"] += diagnostics.get("academic", {}).get("raw_count", 0)
    return results


def _refill(config, provider, runtime, path, association_id, retrieve):
    """Bounded forward paging; only unseen identities fill the acquisition target."""
    target = config.get("max_papers", 100)
    results, keys, new_keys = [], set(), set()
    reason = "page limit reached (10 pages)"
    for page in range(10):
        try:
            page_config = {**config, "_page": page}
            batch = retrieve(page_config, provider, runtime, config.get("year_from"))
        except Exception as error:
            if not results:
                raise
            return results, {"pages": page + 1, "new_candidates": len(new_keys), "target": target,
                             "stop_reason": f"request failed: {_safe_provider_error(error)}", "incomplete": True}
        added = 0
        with _database(path) as connection:
            for item in batch:
                key, aliases = _identity(connection, item)
                if any(alias in keys for alias in aliases):
                    continue
                keys.update([key, *aliases])
                added += 1
                results.append(item)
                if not connection.execute("SELECT 1 FROM plan_action_seen WHERE plan_action_id = ? AND canonical_key = ?", (association_id, key)).fetchone():
                    new_keys.add(key)
                if len(new_keys) >= target:
                    break
        if len(new_keys) >= target:
            reason = "target reached"
            break
        if not batch and not page_config.get("_raw_count"):
            reason = "no further matching results"
            break
        if batch and not added:
            reason = "provider repeated the same results"
            break
    return results, {"pages": page + 1, "new_candidates": len(new_keys), "target": target, "stop_reason": reason}


def _review(config, candidates, runtime, config_path):
    if config.get("mode") != "intelligent":
        return {"results": candidates, "excluded_results": [], "warnings": [], "_ai_usage": {}}
    profile_id = config.get("model_profile_id")
    if profile_id and not any(item.get("id") == profile_id and "chat" in item.get("capabilities", []) for item in ai_model_profiles(runtime)):
        raise ValueError("Saved model profile is unavailable; edit the Action before retrying")
    if config.get("kind") == "subscribe":
        from .intelligent import _client_from_config, _verify_batched
        from .usage import record_ai_usage
        client = _client_from_config(runtime, require_embedding=False, role="subscription_verify", profile_id=profile_id,
                                     skills_dir=config_path.parent / "skills")
        candidates = [{**item, "discovery_path": "Channel acquisition → LLM verify (title and supplied excerpt/comment only)"} for item in candidates]
        assessed, errors, _ = _verify_batched(client, config["query"], [], candidates,
            max(1, min(int(runtime.get("ai_verify_batch_size") or 5), 20)), 1, len(candidates),
            "Subscription review: candidates are posts, comments, repository updates or feed articles. Judge only the supplied title and excerpt/comment text, not an assumed full article. Do not require an academic paper.")
        usage = client.usage_snapshot()
        record_ai_usage(chat_requests=usage.get("chat_requests", 0), chat_tokens=usage.get("chat_tokens", 0))
        return {"results": [item for item in assessed if item.get("relevance_tier") != "excluded"],
                "excluded_results": [item for item in assessed if item.get("relevance_tier") == "excluded"],
                "warnings": ["verification_failed:" + error.code for error in errors], "_ai_usage": usage}
    from .intelligent import intelligent_search
    from .usage import record_ai_usage
    response = intelligent_search(config["query"], {**runtime, **search_settings(config)},
        config.get("intelligent_max_results", 20),
        [item for item in config["sources"] if item in {"arxiv", "openalex", "semanticscholar"}],
        config.get("areas", []), config.get("year_from"), config.get("year_to"),
        search_actions=config.get("search_actions"), profile_id=config.get("model_profile_id", ""),
        skills_dir=config_path.parent / "skills", recall_candidates=candidates)
    usage = response.get("_ai_usage", {})
    if usage:
        record_ai_usage(chat_requests=usage.get("chat_requests", 0), chat_tokens=usage.get("chat_tokens", 0),
            embedding_requests=usage.get("embedding_requests", 0), embedding_tokens=usage.get("embedding_tokens", 0))
    return response


def execute_run(run_id, path, config_path, *, retrieve=None, review=None):
    retrieve = retrieve or _retrieve
    review = review or _review
    try:
        with _database(path) as connection:
            if not connection.execute("UPDATE plan_runs SET status = 'running' WHERE id = ? AND status = 'queued'", (run_id,)).rowcount:
                return
            actions = [dict(row) for row in connection.execute("SELECT * FROM action_runs WHERE run_id = ? ORDER BY position", (run_id,))]
        runtime = load_config(config_path)
        for action in actions:
            config = json.loads(action["config_snapshot"])
            state = json.loads(action["checkpoint_before"])
            # A changed definition starts a fresh retrieval window, not a fresh seen ledger.
            if state.get("action_version") != action["action_version"]:
                state = {"action_version": action["action_version"], "providers": {}}
            report = {"providers": {}, "warnings": [], "usage": {}}
            with _database(path) as connection:
                connection.execute("UPDATE action_runs SET status = 'running' WHERE id = ?", (action["id"],))
            successes = 0
            subscriptions = {item["id"]: item for item in config.get("subscriptions", [])}
            for provider in (subscriptions if config.get("kind") == "subscribe" else config["sources"]):
                if not subscriptions and provider not in {"arxiv", "openalex", "semanticscholar"}:
                    report["warnings"].append(f"Unsupported legacy provider skipped: {provider}")
                    continue
                before = state.get("providers", {}).get(provider)
                report["progress"] = "Fetching · " + (subscriptions[provider]["name"] if subscriptions else provider)
                with _database(path) as connection:
                    connection.execute("UPDATE action_runs SET report = ? WHERE id = ?", (json.dumps(report), action["id"]))
                effective_from = (datetime.fromisoformat(before) - timedelta(days=7)).date().isoformat() if before else None
                try:
                    # Current connectors only offer publication-year filters, which remove
                    # undated items and miss late-indexed old papers. Do not pretend that
                    # those are safe incremental cursors. Keep the user's date constraints.
                    if subscriptions:
                        from .subscriptions import fetch_subscription
                        from .channel_connectors import fetch_scope
                        report["warnings"].append(subscriptions[provider]["name"] + ": " + fetch_scope(subscriptions[provider].get("connector", {}).get("kind", "feed")))
                        results = fetch_subscription(provider, path, expected_url=subscriptions[provider]["url"], expected_spec=subscriptions[provider].get("connector"), config=runtime)
                    else:
                        results, refill = _refill(config, provider, runtime, path, action["plan_action_id"], retrieve)
                        if refill["new_candidates"] < refill["target"]:
                            report["warnings"].append(f"{provider}: {refill['new_candidates']}/{refill['target']} new candidates; {refill['stop_reason']}")
                    now = _now()
                    with _database(path) as connection:
                        for item in results:
                            key, aliases = _identity(connection, item)
                            connection.execute("INSERT INTO seen_items VALUES (?, ?, ?) ON CONFLICT(canonical_key) DO UPDATE SET last_seen_at = excluded.last_seen_at", (key, now, now))
                            for alias in aliases:
                                connection.execute("INSERT OR IGNORE INTO seen_item_aliases VALUES (?, ?)", (alias, key))
                            prior = connection.execute("SELECT first_seen_run FROM plan_action_seen WHERE plan_action_id = ? AND canonical_key = ?", (action["plan_action_id"], key)).fetchone()
                            connection.execute("""INSERT INTO plan_action_seen (plan_action_id, canonical_key, first_seen_run, last_seen_run, metadata_json)
                                VALUES (?, ?, ?, ?, ?) ON CONFLICT(plan_action_id, canonical_key) DO UPDATE SET last_seen_run = excluded.last_seen_run""",
                                (action["plan_action_id"], key, run_id, run_id, json.dumps(item)))
                            connection.execute("INSERT OR IGNORE INTO run_items VALUES (?, ?, ?, ?, ?, 'retrieved')",
                                (run_id, action["id"], key, json.dumps(item), int(not prior)))
                            connection.execute("INSERT OR IGNORE INTO run_item_origins VALUES (?, ?, ?)", (action["id"], key, provider))
                        next_state = json.loads(json.dumps(state))
                        incomplete = not subscriptions and refill.get("incomplete", False)
                        if not incomplete:
                            next_state.setdefault("providers", {})[provider] = now
                        connection.execute("UPDATE plan_actions SET execution_state = ? WHERE id = ?", (json.dumps(next_state), action["plan_action_id"]))
                        report["providers"][provider] = {"status": "completed", "retrieved": len(results), "checkpoint": now,
                            "overlap_from": effective_from, "date_filter": "user constraints only; connector has no safe indexed-date/undated cursor"}
                        if not subscriptions:
                            report["providers"][provider]["refill"] = refill
                            if incomplete:
                                report["providers"][provider].update(status="failed", checkpoint=before)
                        if subscriptions:
                            report["providers"][provider] = {"status": "completed", "retrieved": len(results), "checkpoint": now, "channel": subscriptions[provider]["name"], "cache": "Shared fetch; independent Plan consumption"}
                        connection.execute("UPDATE action_runs SET checkpoint_after = ?, report = ? WHERE id = ?", (json.dumps(next_state), json.dumps(report), action["id"]))
                    state = next_state
                    successes += 1
                except Exception as error:
                    # Exception messages may contain credential-bearing provider URLs.
                    reason = "Paper quota reached" if isinstance(error, RuntimeError) and str(error) == "Paper quota reached" else _safe_provider_error(error)
                    from .channel_connectors import ChannelResponseTooLarge
                    if isinstance(error, ChannelResponseTooLarge):
                        reason = str(error)
                        report["warnings"].append(reason)
                    report["providers"][provider] = {"status": "failed", "error": reason, "checkpoint": before}
            report["warnings"].append("Feeds only expose their available window; cached entries are retained for other Plans." if subscriptions else "Bounded provider search, not exhaustive backfill. Undated items are deduplicated by identity; only explicit user year filters exclude them.")
            with _database(path) as connection:
                pending = connection.execute("SELECT canonical_key, metadata_json FROM plan_action_seen WHERE plan_action_id = ? AND processing_status = 'pending' ORDER BY rowid LIMIT ?",
                    (action["plan_action_id"], min(config.get("max_papers", 100), 100))).fetchall()
            review_failed = False
            if pending:
                try:
                    report["progress"] = f"Selecting candidates · {len(pending)} inputs"
                    with _database(path) as connection:
                        connection.execute("UPDATE action_runs SET report = ? WHERE id = ?", (json.dumps(report), action["id"]))
                    response = review(config, [json.loads(row["metadata_json"]) for row in pending], runtime, config_path)
                    report["usage"] = response.get("_ai_usage", {})
                    report["warnings"].extend(response.get("warnings", []))
                    review_failed = any(str(item).startswith("verification_failed") for item in response.get("warnings", []))
                    if not review_failed:
                        allowed = {row["canonical_key"] for row in pending}
                        with _database(path) as connection:
                            for disposition, values in (("selected", response.get("results", [])), ("excluded", response.get("excluded_results", []))):
                                for item in values:
                                    key, _ = _identity(connection, item)
                                    if key not in allowed:
                                        raise ValueError("Review returned an unknown candidate")
                                    connection.execute("UPDATE plan_action_seen SET processing_status = ?, metadata_json = ? WHERE plan_action_id = ? AND canonical_key = ?", (disposition, json.dumps(item), action["plan_action_id"], key))
                                    connection.execute("INSERT INTO run_items VALUES (?, ?, ?, ?, 0, ?) ON CONFLICT(action_run_id, canonical_key) DO UPDATE SET disposition = excluded.disposition, metadata_json = excluded.metadata_json",
                                        (run_id, action["id"], key, json.dumps(item), disposition))
                except Exception as error:
                    review_failed = True
                    report["warnings"].append(f"Review failed ({type(error).__name__}); candidates retained for next Run.")
            with _database(path) as connection:
                report["pending_count"] = connection.execute("SELECT count(*) FROM plan_action_seen WHERE plan_action_id = ? AND processing_status = 'pending'", (action["plan_action_id"],)).fetchone()[0]
                failed = any(item["status"] == "failed" for item in report["providers"].values())
                status = "failed" if not successes else "partial" if failed or review_failed else "completed"
                connection.execute("UPDATE action_runs SET status = ?, report = ? WHERE id = ?", (status, json.dumps(report), action["id"]))
        from .source_ingestion import ingest_run
        ingest_run(run_id, path)
        from .plan_knowledge import execute_evidence_stage, execute_claim_stage
        knowledge_ok = execute_evidence_stage(run_id, path, config_path)
        claims_ok = execute_claim_stage(run_id, path, config_path)
        from .plan_relations import execute_relation_stage
        relations_ok = execute_relation_stage(run_id, path, config_path)
        from .plan_wiki import execute_wiki_stage
        wiki_ok = execute_wiki_stage(run_id, path, config_path)
        with _database(path) as connection:
            statuses = [row[0] for row in connection.execute("SELECT status FROM action_runs WHERE run_id = ?", (run_id,))]
            status = "completed" if all(item == "completed" for item in statuses) else "failed" if all(item == "failed" for item in statuses) else "partial"
            if status == "completed" and not (knowledge_ok and claims_ok and relations_ok and wiki_ok):
                status = "partial"
            connection.execute("UPDATE plan_runs SET status = ?, finished_at = ? WHERE id = ?", (status, _now(), run_id))
    except Exception as error:
        with _database(path) as connection:
            connection.execute("UPDATE plan_runs SET status = 'failed', finished_at = ?, error = ? WHERE id = ?", (_now(), f"Run interrupted ({type(error).__name__}); committed results retained.", run_id))
            connection.execute("UPDATE action_runs SET status = 'failed' WHERE run_id = ? AND status IN ('queued', 'running')", (run_id,))


def launch_run(run_id, path, config_path):
    try:
        threading.Thread(target=execute_run, args=(run_id, path, config_path), daemon=True,
                         name=f"knowte-plan-{run_id[:8]}").start()
    except RuntimeError:
        with _database(path) as connection:
            connection.execute("UPDATE plan_runs SET status = 'failed', finished_at = ?, error = 'Could not start worker' WHERE id = ?", (_now(), run_id))
            connection.execute("UPDATE action_runs SET status = 'failed' WHERE run_id = ?", (run_id,))
        raise ValueError("Could not start Plan worker; retry this Run") from None


def start_run(plan_id, path, config_path, legacy_path=None, *, knowledge_only=False):
    recover_interrupted(path)
    run_id, created = queue_run(plan_id, path, legacy_path, trigger="recompute" if knowledge_only else "manual", knowledge_only=knowledge_only)
    if created:
        launch_run(run_id, path, config_path)
    return {"run_id": run_id, "already_running": not created}
