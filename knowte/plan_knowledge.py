"""Durable Source -> pending Evidence -> pending Claim generation jobs."""
from __future__ import annotations

import json
from uuid import uuid4

from .automation import _database
from .config import ai_model_profiles, load_config


def execute_evidence_stage(run_id, path, config_path, *, generate=None):
    from .server import generate_evidence_proposals
    generate = generate or generate_evidence_proposals
    config = load_config(config_path)
    with _database(path) as connection:
        run = connection.execute("SELECT * FROM plan_runs WHERE id = ?", (run_id,)).fetchone()
        row = connection.execute("SELECT config_json FROM run_processing_policy WHERE run_id = ?", (run_id,)).fetchone()
        policy = json.loads(row[0]) if row else {}
        stage = policy.get("evidence", {})
        if not stage.get("enabled"):
            return True
        limit = max(1, min(100, int(config.get("ai_evidence_source_limit", 6))))
        if config.get("ai_evidence_request_mode") == "individual":
            limit = 1
        sources = [row[0] for row in connection.execute("""SELECT rs.source_id FROM run_sources rs
            JOIN sources s ON s.id = rs.source_id WHERE rs.run_id = ? AND NOT EXISTS
            (SELECT 1 FROM plan_source_jobs j WHERE j.plan_id = ? AND j.source_id = rs.source_id)
            ORDER BY rs.source_id""", (run_id, run["plan_id"]))]
        for offset in range(0, len(sources), limit):
            ids, job_id = sources[offset:offset + limit], uuid4().hex
            connection.execute("INSERT INTO plan_generation_jobs (id, plan_id, first_run_id, last_run_id, source_ids_json, policy_json) VALUES (?, ?, ?, ?, ?, ?)",
                (job_id, run["plan_id"], run_id, run_id, json.dumps(ids), json.dumps(stage)))
            connection.executemany("INSERT INTO plan_source_jobs VALUES (?, ?, ?)", [(run["plan_id"], sid, job_id) for sid in ids])
        jobs = [dict(row) for row in connection.execute("SELECT * FROM plan_generation_jobs WHERE plan_id = ? AND status IN ('queued', 'running', 'failed') ORDER BY rowid", (run["plan_id"],))]
    successful = True
    blocked_models = set()
    for job in jobs:
        stage = json.loads(job["policy_json"])
        if stage["model_profile_id"] in blocked_models:
            with _database(path) as connection:
                connection.execute("INSERT OR IGNORE INTO generation_attempts (run_id, job_id, status, report_json) VALUES (?, ?, 'queued', ?)",
                    (run_id, job["id"], json.dumps({"warnings": ["Deferred: model service failed in an earlier batch. Retry on next Run."], "proposal_ids": []})))
            successful = False
            continue
        with _database(path) as connection:
            outputs = [row[0] for row in connection.execute("SELECT proposal_id FROM generation_outputs WHERE job_id = ?", (job["id"],))]
            input_ids = json.loads(job["source_ids_json"])
            available_ids = [sid for sid in input_ids if connection.execute("SELECT 1 FROM sources WHERE id = ?", (sid,)).fetchone()]
            connection.execute("UPDATE plan_generation_jobs SET status = 'running', last_run_id = ? WHERE id = ?", (run_id, job["id"]))
            connection.execute("INSERT OR IGNORE INTO generation_attempts (run_id, job_id, status) VALUES (?, ?, 'running')", (run_id, job["id"]))
        if not available_ids:
            report = {"proposal_ids": outputs, "warnings": ["Source inputs were deleted; this batch will not be retried."], "model_usage": {}}
            status = "cancelled"
        elif outputs:
            # A worker can stop after saving proposals but before its receipt.
            # Preserve those results instead of paying for duplicate generation.
            report = {"proposal_ids": outputs, "warnings": ["Recovered saved proposals after interruption; this batch was not called again."], "model_usage": {}}
            status = "partial"
        else:
            try:
                stage = json.loads(job["policy_json"])
                if not any(p["id"] == stage["model_profile_id"] and "chat" in p.get("capabilities", []) for p in ai_model_profiles(config)):
                    raise ValueError("Saved Evidence model is unavailable; restore its profile before retrying")
                result, code = generate({"source_ids": available_ids, "focus": stage["focus"],
                    "model_profile_id": stage["model_profile_id"]}, config_path, path, config_path.parent / "content",
                    automation_scope={"generation_job_id": job["id"], "plan_id": run["plan_id"], "plan_run_id": run_id})
                report = {"proposal_ids": [p["id"] for p in result.get("proposals", [])],
                    "warnings": result.get("warnings", []), "summary": result.get("summary", ""),
                    "model_usage": result.get("model_usage", {}), "failures": result.get("failures", [])}
                codes = {failure.get("code") for failure in report["failures"]} | {result.get("error")}
                if codes & {"connection_failed", "timeout", "http_error", "invalid_base_url"}:
                    blocked_models.add(stage["model_profile_id"])
                    report["warnings"].append("Remaining Evidence batches using this model are deferred until the next Run; no immediate retry was made.")
                if len(available_ids) != len(input_ids):
                    report["warnings"].append("Deleted Source inputs were skipped.")
                if code >= 400 or (not report["proposal_ids"] and (result.get("failed_groups") or "proposals" not in result)):
                    report["warnings"].append(result.get("message") or "No usable Evidence; this batch will retry next Run.")
                    status = "failed"
                else:
                    status = "partial" if report["warnings"] else "completed"
            except Exception as error:
                status = "failed"
                report = {"proposal_ids": [], "warnings": [f"Evidence job failed ({type(error).__name__}); retry on the next Run."], "model_usage": {}}
        with _database(path) as connection:
            connection.execute("UPDATE plan_generation_jobs SET status = ?, report_json = ? WHERE id = ?", (status, json.dumps(report), job["id"]))
            connection.execute("UPDATE generation_attempts SET status = ?, report_json = ? WHERE run_id = ? AND job_id = ?", (status, json.dumps(report), run_id, job["id"]))
        successful = successful and status in {"completed", "cancelled"}
    return successful


def execute_claim_stage(run_id, path, config_path, *, generate=None):
    from .server import generate_claim_proposals
    from .proposal_dependencies import evidence_input
    from .recomputation import queue_stale_jobs, recomputation_origins
    generate = generate or generate_claim_proposals
    config = load_config(config_path)
    with _database(path) as connection:
        run = connection.execute("SELECT * FROM plan_runs WHERE id = ?", (run_id,)).fetchone()
        row = connection.execute("SELECT config_json FROM run_processing_policy WHERE run_id = ?", (run_id,)).fetchone()
        stage = json.loads(row[0]).get("claims", {}) if row else {}
        if not stage.get("enabled"):
            return True
        queue_stale_jobs(connection, run["plan_id"], run_id, "claims")
        limit = max(1, min(100, int(config.get("ai_claim_evidence_limit", 30))))
        ids = [r[0] for r in connection.execute("""SELECT o.proposal_id FROM generation_outputs o
            JOIN plan_generation_jobs j ON j.id = o.job_id WHERE j.plan_id = ? AND NOT EXISTS
            (SELECT 1 FROM plan_claim_inputs i WHERE i.plan_id = ? AND i.proposal_id = o.proposal_id)
            ORDER BY j.rowid, o.rowid""", (run["plan_id"], run["plan_id"]))]
        if row and json.loads(row[0]).get("knowledge_only"):
            ids = []
        for offset in range(0, len(ids), limit):
            batch, job_id = ids[offset:offset + limit], uuid4().hex
            connection.execute("INSERT INTO plan_claim_jobs (id, plan_id, first_run_id, input_refs_json, policy_json) VALUES (?, ?, ?, ?, ?)",
                (job_id, run["plan_id"], run_id, json.dumps(["proposal:" + item for item in batch]), json.dumps(stage)))
            connection.executemany("INSERT INTO plan_claim_inputs VALUES (?, ?, ?)", [(run["plan_id"], item, job_id) for item in batch])
        jobs = [dict(row) for row in connection.execute("SELECT * FROM plan_claim_jobs WHERE plan_id = ? AND status IN ('queued', 'running', 'failed') AND json_extract(policy_json, '$.recheck') IS NULL ORDER BY rowid", (run["plan_id"],))]
    from .plan_rechecks import execute_rechecks
    successful = execute_rechecks(run_id, path, config_path, config)
    for job in jobs:
        warnings, inputs = [], []
        with _database(path) as connection:
            outputs = [r[0] for r in connection.execute("SELECT proposal_id FROM generation_outputs WHERE job_id = ?", (job["id"],))]
            recomputed_ids = recomputation_origins(connection, job["id"])
            for reference in json.loads(job["input_refs_json"]):
                try:
                    inputs.append(evidence_input(connection, reference))
                except ValueError:
                    warnings.append("An Evidence input was rejected or deleted and was skipped.")
            connection.execute("UPDATE plan_claim_jobs SET status = 'running' WHERE id = ?", (job["id"],))
            connection.execute("INSERT OR IGNORE INTO generation_attempts (run_id, job_id, status) VALUES (?, ?, 'running')", (run_id, job["id"]))
        report = {"proposal_ids": outputs, "warnings": warnings, "model_usage": {}, "recomputed_proposal_ids": recomputed_ids}
        if outputs:
            status = "partial"
            warnings.append("Recovered saved Claim proposals; no duplicate model call was made.")
        elif not inputs:
            status = "cancelled"
        else:
            try:
                stage = json.loads(job["policy_json"])
                if not any(p["id"] == stage["model_profile_id"] and "chat" in p.get("capabilities", []) for p in ai_model_profiles(config)):
                    raise ValueError("Saved Claim model is unavailable")
                result, code = generate({"evidence_ids": [i["id"] for i in inputs], "focus": stage["focus"], "model_profile_id": stage["model_profile_id"],
                    "instruction": "Pending Evidence is provisionally usable for this computation, not user-accepted. Generate reviewable proposals without claiming that upstream content has been reviewed."},
                    config_path, path, evidence_inputs=inputs,
                    automation_scope={"generation_job_id": job["id"], "plan_id": run["plan_id"], "plan_run_id": run_id,
                                      "recomputed_proposal_ids": recomputed_ids})
                report.update({"proposal_ids": [p["id"] for p in result.get("proposals", [])], "summary": result.get("summary", ""),
                               "skipped": result.get("skipped", []), "model_usage": result.get("model_usage", {})})
                if code >= 400:
                    status = "failed"
                    warnings.append(result.get("message") or "Claim generation failed; retry on next Run.")
                else:
                    status = "partial" if warnings else "completed"
            except Exception as error:
                status = "failed"
                warnings.append(f"Claim generation failed ({type(error).__name__}); retry on next Run.")
        with _database(path) as connection:
            connection.execute("UPDATE plan_claim_jobs SET status = ?, report_json = ? WHERE id = ?", (status, json.dumps(report), job["id"]))
            connection.execute("UPDATE generation_attempts SET status = ?, report_json = ? WHERE run_id = ? AND job_id = ?", (status, json.dumps(report), run_id, job["id"]))
        successful = successful and status in {"completed", "cancelled"}
    return successful
