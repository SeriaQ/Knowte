"""Suggest revisions to reviewed Plan Claims without changing reviewed knowledge."""
from __future__ import annotations

import json
from uuid import uuid4

from .automation import _database
from .proposal_dependencies import evidence_input


def _generate(draft, inputs, policy, config, config_path):
    from .server import _client_from_config, _claim_proposal_prompt
    from .usage import record_ai_usage
    client = _client_from_config(config, skills_dir=config_path.parent / "skills",
        require_embedding=False, role="claims", profile_id=policy["model_profile_id"])
    try:
        result = client.chat_json(_claim_proposal_prompt(config_path.parent / "skills"), json.dumps({
            "instruction": "Recheck only the supplied existing Claim against its changed Evidence. "
                "Return claims with exactly one proposed statement, rationale and optional caveats if "
                "the remaining Evidence supports a defensible revision (or the unchanged statement). "
                "Otherwise return claims: [] and explain in summary. Do not invent grounding, "
                "create other Claims, change relationships or accept anything.",
            "focus": policy.get("focus", ""), "existing_claim": draft,
            "evidence": [{"evidence_id": item["id"], "quote": item["quote"],
                "source_id": item["source_id"], "locator": item["locator"]} for item in inputs],
        }, ensure_ascii=False), temperature=0.1, max_tokens=3000, allow_text_fallback=True)
        return result, client.usage_snapshot()
    finally:
        usage = client.usage_snapshot()
        record_ai_usage(chat_requests=usage.get("chat_requests", 0), chat_tokens=usage.get("chat_tokens", 0))


def execute_rechecks(run_id, path, config_path, config, *, generate=None):
    with _database(path) as connection:
        plan_id = connection.execute("SELECT plan_id FROM plan_runs WHERE id = ?", (run_id,)).fetchone()[0]
        rows = connection.execute("""SELECT p.id, p.payload_json, j.policy_json
            FROM review_proposals p JOIN proposal_outcomes o
              ON o.result_id = json_extract(p.payload_json, '$.target_claim_id') AND o.decision = 'accepted'
            JOIN generation_outputs g ON g.proposal_id = o.proposal_id
            JOIN plan_claim_jobs j ON j.id = g.job_id
            WHERE j.plan_id = ? AND p.status = 'awaiting_review'
              AND json_extract(p.payload_json, '$.operation') = 'review_evidence_change'
            ORDER BY j.rowid""", (plan_id,)).fetchall()
        for row in rows:
            draft = json.loads(row["payload_json"])
            key = {"id": row["id"], "token": draft["change_token"]}
            if connection.execute("""SELECT 1 FROM plan_claim_jobs
                WHERE json_extract(policy_json, '$.recheck.id') = ?
                AND json_extract(policy_json, '$.recheck.token') = ?""", (key["id"], key["token"])).fetchone():
                continue
            policy = {**json.loads(row["policy_json"]), "recheck": key}
            connection.execute("INSERT INTO plan_claim_jobs (id, plan_id, first_run_id, input_refs_json, policy_json) VALUES (?, ?, ?, ?, ?)",
                (uuid4().hex, plan_id, run_id, json.dumps([link["evidence_id"] for link in draft["evidence"]]), json.dumps(policy)))
        jobs = [dict(row) for row in connection.execute("""SELECT * FROM plan_claim_jobs WHERE plan_id = ?
            AND json_extract(policy_json, '$.recheck') IS NOT NULL AND status IN ('queued', 'running', 'failed')""", (plan_id,))]
    successful = True
    for job in jobs:
        policy = json.loads(job["policy_json"])
        key = policy["recheck"]
        report = {"proposal_ids": [], "warnings": [], "model_usage": {}, "recheck_proposal_id": key["id"]}
        status = "cancelled"
        try:
            with _database(path) as connection:
                row = connection.execute("SELECT payload_json FROM review_proposals WHERE id = ?", (key["id"],)).fetchone()
                draft = json.loads(row[0]) if row else {}
                inputs = [evidence_input(connection, ref) for ref in json.loads(job["input_refs_json"])] if draft.get("change_token") == key["token"] else []
                connection.execute("UPDATE plan_claim_jobs SET status = 'running' WHERE id = ?", (job["id"],))
                connection.execute("INSERT OR IGNORE INTO generation_attempts VALUES (?, ?, 'running', '{}')", (run_id, job["id"]))
            if inputs:
                if len(inputs) > int(config.get("ai_claim_evidence_limit", 30)):
                    raise ValueError("Recheck exceeds the configured Evidence limit")
                result, report["model_usage"] = (generate or _generate)(draft, inputs, policy, config, config_path)
                if not isinstance(result, dict) or not isinstance(result.get("claims"), list):
                    report["raw_response"] = result
                    raise ValueError("Recheck response has no claims list; inspect the saved response")
                candidates = result["claims"]
                report["summary"] = str(result.get("summary") or "")
                if len(candidates) > 1:
                    raise ValueError("Recheck must propose at most one revision")
                with _database(path) as connection:
                    row = connection.execute("SELECT payload_json FROM review_proposals WHERE id = ?", (key["id"],)).fetchone()
                    current = json.loads(row[0]) if row else {}
                    claim = connection.execute("SELECT current_revision_id FROM claims WHERE id = ?", (draft["target_claim_id"],)).fetchone()
                    if current.get("change_token") != key["token"] or not claim or claim[0] != draft["claim_revision_id"]:
                        raise ValueError("Review or Claim changed during recomputation")
                    for item in inputs:
                        if evidence_input(connection, item["id"])["input_version"] != item["input_version"]:
                            raise ValueError("Evidence changed during recomputation")
                    if candidates:
                        candidate = candidates[0]
                        statement = str(candidate.get("statement") or "").strip()
                        if not statement or len(statement) > 4000:
                            raise ValueError("Invalid revised statement")
                        from .proposal_dependencies import _propagate
                        _propagate(connection, key["id"], "stale")
                        current.update(statement=statement, rationale=str(candidate.get("rationale") or "")[:2000],
                            caveats=[str(c)[:1000] for c in candidate.get("caveats", [])[:8]],
                            ai_recheck={"job_id": job["id"], "previous_statement": draft["statement"],
                                "change_token": key["token"],
                                "input_versions": {item["id"]: item["input_version"] for item in inputs}})
                        connection.execute("UPDATE review_proposals SET payload_json = ?, model = ? WHERE id = ?",
                            (json.dumps(current), policy["model_profile_id"], key["id"]))
                        connection.execute("INSERT OR REPLACE INTO proposal_derivations VALUES (?, 'current')", (key["id"],))
                        connection.execute("INSERT OR IGNORE INTO generation_outputs VALUES (?, ?)", (job["id"], key["id"]))
                        connection.execute("DELETE FROM plan_relation_inputs WHERE plan_id = ? AND proposal_id = ?", (plan_id, key["id"]))
                        report["proposal_ids"] = [key["id"]]
                    else:
                        report["warnings"].append("No defensible revision proposed; existing review remains for human decision.")
                    status = "completed"
                    # Save the receipt with the suggestion, so interruption cannot duplicate the call.
                    connection.execute("UPDATE plan_claim_jobs SET status = ?, report_json = ? WHERE id = ?", (status, json.dumps(report), job["id"]))
                    connection.execute("UPDATE generation_attempts SET status = ?, report_json = ? WHERE run_id = ? AND job_id = ?", (status, json.dumps(report), run_id, job["id"]))
            else:
                report["warnings"].append("Review resolved/changed or no remaining Evidence; no model call made.")
        except Exception as error:
            status = "failed"
            report["warnings"].append(str(error))
        if status != "completed":
            with _database(path) as connection:
                connection.execute("UPDATE plan_claim_jobs SET status = ?, report_json = ? WHERE id = ?", (status, json.dumps(report), job["id"]))
                connection.execute("INSERT OR REPLACE INTO generation_attempts VALUES (?, ?, ?, ?)", (run_id, job["id"], status, json.dumps(report)))
        successful = successful and status in {"completed", "cancelled"}
    return successful
