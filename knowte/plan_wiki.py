"""Durable projected Wiki organization; never writes reviewed Wiki tables."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from .automation import _database
from .config import load_config, ai_model_profiles
from .knowledge import get_wiki, prepare_wiki_batch, merge_wiki_batch, _normalize_wiki_proposal_payload
from .proposal_dependencies import claim_input, version


def _generate(wiki, selected, partial, config, config_path, profile):
    from .server import _client_from_config, _wiki_maintainer_prompt, _copilot_settings, skill_prompt
    from .usage import record_ai_usage
    client = _client_from_config(config, skills_dir=config_path.parent / "skills", require_embedding=False, role="wiki", profile_id=profile)
    _, temperature, max_tokens, advanced = _copilot_settings(config, "views")
    directory = [{"page_id": p["id"], "parent_id": p["parent_id"], "title": p["title"],
                  "summary": p["summary"], "claim_count": len(p["claim_ids"])} for p in wiki["pages"]]
    def context(claim):
        return {"id": claim["id"], "statement": claim["statement"], "basis": claim["basis"],
                "review_state": claim.get("review_state", "accepted")}
    try:
        references = []
        if partial and directory:
            selection = client.chat_json(skill_prompt("wiki_context_selection", config_path.parent / "skills"),
                json.dumps({"directory": directory, "claims": [context(c) for c in selected]}, ensure_ascii=False),
                temperature=min(temperature, .3), max_tokens=1000, extra_parameters=advanced, allow_text_fallback=True)
            if selection.get("_structured_output_degraded"):
                return selection, client.usage_snapshot()
            ids = selection.get("page_ids")
            by_id = {p["id"]: p for p in wiki["pages"]}
            if not isinstance(ids, list) or len(ids) > 5 or any(not isinstance(i, str) or i not in by_id for i in ids) or len(set(ids)) != len(ids):
                raise ValueError("Invalid reference Page selection")
            selected_ids = {c["id"] for c in selected}
            claims = {c["id"]: c for c in wiki["claims"] if c["id"] not in selected_ids}
            for pid in ids:
                available = [claims[cid] for cid in by_id[pid]["claim_ids"] if cid in claims]
                references.append({"page_id": pid, "truncated": len(available) > 10,
                    "available_claim_count": len(available), "claims": [context(c) for c in available[:10]]})
        result = client.chat_json(_wiki_maintainer_prompt(config_path.parent / "skills"),
            json.dumps({"projection_mode": True, "instruction": "Organize the single optimistic branch. Pending Claims are assumed usable, not reviewed facts. Preserve their uncertainty. Never accept Claims or invent relations.",
                "batch_mode": partial, "current_wiki": directory, "reference_pages": references,
                "claims": [context(c) for c in selected]}, ensure_ascii=False),
            temperature=min(temperature, .3), max_tokens=max(3000, max_tokens), extra_parameters=advanced, allow_text_fallback=True)
        return result, client.usage_snapshot()
    finally:
        usage = client.usage_snapshot()
        record_ai_usage(chat_requests=usage.get("chat_requests", 0), chat_tokens=usage.get("chat_tokens", 0))


def execute_wiki_stage(run_id, path, config_path, *, generate=None):
    config = load_config(config_path)
    with _database(path) as connection:
        run = connection.execute("SELECT * FROM plan_runs WHERE id = ?", (run_id,)).fetchone()
        row = connection.execute("SELECT config_json FROM run_processing_policy WHERE run_id = ?", (run_id,)).fetchone()
        stage = json.loads(row[0]).get("wiki", {}) if row else {}
        if not stage.get("enabled"):
            return True
        if connection.execute("SELECT 1 FROM generation_attempts t JOIN plan_wiki_jobs j ON j.id = t.job_id WHERE t.run_id = ? AND t.status = 'completed'", (run_id,)).fetchone():
            return True
    wiki = get_wiki(path, projected=True)
    organization = wiki["projection"].get("organization", {})
    with _database(path) as connection:
        job = connection.execute("SELECT * FROM plan_wiki_jobs WHERE plan_id = ? AND status IN ('queued', 'running', 'failed') ORDER BY rowid LIMIT 1", (run["plan_id"],)).fetchone()
        if not job:
            if not wiki["unorganized_claim_ids"] and not wiki["stale_claim_ids"] and organization.get("status") != "stale":
                return True
            job_id = uuid4().hex
            connection.execute("INSERT INTO plan_wiki_jobs (id, plan_id, first_run_id, policy_json) VALUES (?, ?, ?, ?)", (job_id, run["plan_id"], run_id, json.dumps(stage)))
            job = connection.execute("SELECT * FROM plan_wiki_jobs WHERE id = ?", (job_id,)).fetchone()
        job = dict(job)
        connection.execute("UPDATE plan_wiki_jobs SET status = 'running' WHERE id = ?", (job["id"],))
        connection.execute("INSERT OR IGNORE INTO generation_attempts (run_id, job_id, status) VALUES (?, ?, 'running')", (run_id, job["id"]))
    selected, scope = prepare_wiki_batch(wiki, max(1, min(1000, int(config.get("ai_wiki_claim_limit", 100)))))
    report = {"claim_ids": scope["claim_ids"], "warnings": [], "model_usage": {}, "pages": 0,
              "estimated_model_calls": (2 if scope["partial"] and wiki["pages"] else 1) if selected else 0}
    status = "completed"
    try:
        if selected:
            profile = json.loads(job["policy_json"])["model_profile_id"]
            if not any(p["id"] == profile and "chat" in p.get("capabilities", []) for p in ai_model_profiles(config)):
                raise ValueError("Saved Wiki model is unavailable")
            # Include preserved pages and read-only context in the version check too.
            with _database(path) as connection:
                inputs = {}
                connection.execute("DELETE FROM artifact_dependencies WHERE child_proposal_id = ?", (job["id"],))
                connection.execute("INSERT OR REPLACE INTO proposal_derivations VALUES (?, 'current')", (job["id"],))
                for claim in wiki["claims"]:
                    current = claim_input(connection, claim["id"])
                    if (current["statement"], current["basis"]) != (claim["statement"], claim["basis"]):
                        raise ValueError("Claim changed while preparing organization")
                    inputs[claim["id"]] = current["input_version"]
                    ref = claim["id"]
                    if ref.startswith("proposal:"):
                        parent = connection.execute("SELECT payload_json FROM review_proposals WHERE id = ?", (ref[9:],)).fetchone()
                        if parent:
                            connection.execute("INSERT INTO artifact_dependencies (parent_proposal_id, parent_version, child_proposal_id, dependency_mode) VALUES (?, ?, ?, 'provisional')",
                                (ref[9:], version(json.loads(parent[0]), "claim"), job["id"]))
                    else:
                        connection.execute("INSERT INTO artifact_dependencies (parent_proposal_id, parent_version, child_proposal_id, dependency_mode, accepted_id) VALUES (?, ?, ?, 'accepted', ?)",
                            ("claim:" + ref, current["input_version"], job["id"], ref))
            result, report["model_usage"] = (generate or _generate)(wiki, selected, scope["partial"], config, config_path, profile)
            if result.get("_structured_output_degraded"):
                report["raw_response"] = str(result.get("answer") or "")
                raise ValueError("Invalid JSON")
            assigned = [cid for p in result.get("pages", []) for cid in p.get("claim_ids", [])]
            if len(assigned) != len(selected) or set(assigned) != set(scope["claim_ids"]):
                raise ValueError("Every selected Claim must be assigned exactly once")
            if scope["partial"]:
                result = merge_wiki_batch(result, wiki, scope["claim_ids"])
            result = _normalize_wiki_proposal_payload(result, set(inputs))
            with _database(path) as connection:
                latest = connection.execute("SELECT id FROM wiki_projections ORDER BY rowid DESC LIMIT 1").fetchone()
                revision = connection.execute("SELECT id FROM wiki_revisions ORDER BY created_at DESC LIMIT 1").fetchone()
                if (latest[0] if latest else None) != organization.get("id") or (revision[0] if revision else None) != scope["base_revision_id"]:
                    raise ValueError("Wiki organization changed during generation")
                for ref, expected in inputs.items():
                    if claim_input(connection, ref)["input_version"] != expected:
                        raise ValueError("Claim changed during organization")
                used = {cid for page in result["pages"] for cid in page["claim_ids"]}
                connection.execute("INSERT INTO wiki_projections VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (job["id"], run["plan_id"], run_id, scope["base_revision_id"], json.dumps(result),
                     json.dumps({ref: inputs[ref] for ref in used}), datetime.now(timezone.utc).isoformat()))
                report.update(pages=len(result["pages"]), projection_id=job["id"], summary=result["summary"], input_versions=inputs)
                _finish(connection, job["id"], run_id, status, report)
            return True
    except Exception as error:
        status = "failed"
        report["warnings"].append(f"Projected Wiki generation failed ({type(error).__name__}); retry on next Run. Reviewed Wiki is unchanged.")
    with _database(path) as connection:
        _finish(connection, job["id"], run_id, status, report)
    return status == "completed"


def _finish(connection, job_id, run_id, status, report):
    connection.execute("UPDATE plan_wiki_jobs SET status = ?, report_json = ? WHERE id = ?", (status, json.dumps(report), job_id))
    connection.execute("UPDATE generation_attempts SET status = ?, report_json = ? WHERE run_id = ? AND job_id = ?", (status, json.dumps(report), run_id, job_id))
