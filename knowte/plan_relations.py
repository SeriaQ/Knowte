"""Bounded, durable relation discovery around a Plan's new Claim outputs."""
from __future__ import annotations

import json
from uuid import uuid4

from .automation import _database
from .config import ai_model_profiles, load_config
from .knowledge import _claim_search_tokens, create_claim_proposal, get_wiki
from .proposal_dependencies import claim_input
from .recomputation import queue_stale_jobs, recomputation_origins


def _generate(pairs, config, config_path, profile):
    from .server import _client_from_config, _claim_audit_prompt
    from .usage import record_ai_usage
    client = _client_from_config(config, skills_dir=config_path.parent / "skills",
                                 require_embedding=False, role="claims", profile_id=profile)
    def context(item):
        return {"claim_id": item["resolved_id"], "statement": item["statement"],
                "basis": item["basis"], "review_state": item["review_state"],
                "grounding": [{**e, "quote": e["quote"][:1200]} for e in item["grounding"][:8]],
                "grounding_truncated": len(item["grounding"]) > 8 or any(len(e["quote"]) > 1200 for e in item["grounding"])}
    try:
        result = client.chat_json(_claim_audit_prompt(config_path.parent / "skills"),
            json.dumps({"instruction": "These include provisional Claims, not user-accepted facts. Discover missing relations only; do not accept or modify Claims.",
                        "pairs": [{"left": context(left), "right": context(right), "existing_relations": []}
                                  for left, right in pairs]}, ensure_ascii=False),
            temperature=0.05, max_tokens=3200, allow_text_fallback=True)
        return result, client.usage_snapshot()
    finally:
        usage = client.usage_snapshot()
        record_ai_usage(chat_requests=usage.get("chat_requests", 0), chat_tokens=usage.get("chat_tokens", 0))


def _relation_key(left, right, kind):
    return (left, right, kind) if kind == "supports" else (*sorted((left, right)), kind)


def execute_relation_stage(run_id, path, config_path, *, generate=None):
    config = load_config(config_path)
    with _database(path) as connection:
        run = connection.execute("SELECT * FROM plan_runs WHERE id = ?", (run_id,)).fetchone()
        row = connection.execute("SELECT config_json FROM run_processing_policy WHERE run_id = ?", (run_id,)).fetchone()
        stage = json.loads(row[0]).get("relations", {}) if row else {}
        if not stage.get("enabled"):
            return True
    wiki = get_wiki(path, projected=True)
    with _database(path) as connection:
        queue_stale_jobs(connection, run["plan_id"], run_id, "relations")
        seeds = [r[0] for r in connection.execute("""SELECT o.proposal_id FROM generation_outputs o
            JOIN plan_claim_jobs j ON j.id = o.job_id WHERE j.plan_id = ? AND NOT EXISTS
            (SELECT 1 FROM plan_relation_inputs i WHERE i.plan_id = ? AND i.proposal_id = o.proposal_id)
            ORDER BY j.rowid, o.rowid""", (run["plan_id"], run["plan_id"]))]
        pool = {}
        for claim in wiki["claims"]:
            try:
                pool[claim["id"]] = claim_input(connection, claim["id"])
            except ValueError:
                continue
        linked = {frozenset((e["subject_claim_id"], e["object_claim_id"])) for e in wiki["graph"]["edges"]}
        pairs = set()
        for seed in seeds:
            ref = "proposal:" + seed
            try:
                left = claim_input(connection, ref)
            except ValueError:
                continue
            left_tokens = _claim_search_tokens(left["statement"])
            sources = {e["source_id"] for e in left["grounding"]}
            ranked = []
            for right in pool.values():
                if right["resolved_id"] == left["resolved_id"] or frozenset((left["resolved_id"], right["resolved_id"])) in linked:
                    continue
                tokens = _claim_search_tokens(right["statement"])
                lexical = len(tokens & left_tokens) / (len(tokens | left_tokens) or 1)
                shared = len(sources & {e["source_id"] for e in right["grounding"]})
                if shared or lexical >= 0.12:
                    ranked.append((shared * 6 + lexical * 10, right["id"]))
            for _, other in sorted(ranked, reverse=True)[:8]:
                pairs.add(tuple(sorted((ref, other))))
        unique_pairs = {}
        for refs in sorted(pairs):
            key = tuple(sorted(claim_input(connection, ref)["resolved_id"] for ref in refs))
            unique_pairs.setdefault(key, refs)
        pairs = list(unique_pairs.values())
        for offset in range(0, len(pairs), 8):
            connection.execute("INSERT INTO plan_relation_jobs (id, plan_id, first_run_id, input_refs_json, policy_json) VALUES (?, ?, ?, ?, ?)",
                (uuid4().hex, run["plan_id"], run_id, json.dumps(pairs[offset:offset + 8]), json.dumps(stage)))
        connection.executemany("INSERT OR IGNORE INTO plan_relation_inputs VALUES (?, ?)", [(run["plan_id"], seed) for seed in seeds])
        jobs = [dict(r) for r in connection.execute("SELECT * FROM plan_relation_jobs WHERE plan_id = ? AND status IN ('queued', 'running', 'failed') ORDER BY rowid", (run["plan_id"],))]
    successful = True
    for job in jobs:
        report = {"proposal_ids": [], "warnings": [], "model_usage": {}}
        with _database(path) as connection:
            report["recomputed_proposal_ids"] = recomputation_origins(connection, job["id"])
            connection.execute("UPDATE plan_relation_jobs SET status = 'running' WHERE id = ?", (job["id"],))
            connection.execute("INSERT OR IGNORE INTO generation_attempts (run_id, job_id, status) VALUES (?, ?, 'running')", (run_id, job["id"]))
            pairs = []
            for refs in json.loads(job["input_refs_json"]):
                try:
                    pairs.append(tuple(claim_input(connection, ref) for ref in refs))
                except ValueError:
                    report["warnings"].append("Unavailable or stale Claim pair skipped.")
        status = "completed"
        try:
            if pairs:
                profile = json.loads(job["policy_json"])["model_profile_id"]
                model_profile = next((p for p in ai_model_profiles(config) if p["id"] == profile and "chat" in p.get("capabilities", [])), None)
                if not model_profile:
                    raise ValueError("Saved Relation model is unavailable")
                result, report["model_usage"] = (generate or _generate)(pairs, config, config_path, profile)
                if result.get("_structured_output_degraded"):
                    report["raw_response"] = str(result.get("answer") or "")
                    raise ValueError("Invalid JSON; raw response retained")
                assessments = result.get("assessments")
                allowed = {frozenset((a["resolved_id"], b["resolved_id"])): (a, b) for a, b in pairs}
                if not isinstance(assessments, list) or len(assessments) != len(allowed):
                    raise ValueError("Incomplete relation assessment")
                seen, drafts = set(), []
                for assessment in assessments:
                    key = frozenset((assessment.get("left_claim_id"), assessment.get("right_claim_id")))
                    if key not in allowed or key in seen:
                        raise ValueError("Unexpected or duplicate Claim pair")
                    seen.add(key)
                    judgment = assessment.get("judgment")
                    if judgment not in {"supports", "contradicts", "related", "scope_difference", "same", "revises", "distinct", "uncertain"}:
                        raise ValueError("Unknown relation judgment")
                    if judgment not in {"supports", "contradicts", "related"}:
                        report.setdefault("skipped", []).append(assessment)
                        continue
                    subject = assessment.get("subject_claim_id")
                    target = assessment.get("object_claim_id")
                    if judgment != "supports":
                        subject = subject or assessment["left_claim_id"]
                        target = target or assessment["right_claim_id"]
                    if frozenset((subject, target)) != key or not str(assessment.get("rationale") or "").strip():
                        raise ValueError("Relation needs valid endpoints, direction and rationale")
                    by_id = {item["resolved_id"]: item for item in allowed[key]}
                    drafts.append({"operation": "create_relation", "relation_type": judgment,
                        "subject_claim_id": by_id[subject]["id"], "object_claim_id": by_id[target]["id"],
                        "rationale": assessment["rationale"], "caveats": assessment.get("caveats", [])})
                # Proposals and completion receipt commit together: interruption cannot
                # leave a partially saved batch which costs another model call.
                with _database(path) as connection:
                    versions = {i["id"]: i["input_version"] for pair in pairs for i in pair}
                    for ref, expected in versions.items():
                        if claim_input(connection, ref)["input_version"] != expected:
                            raise ValueError("Claim changed during generation")
                    existing = {_relation_key(r[0], r[1], r[2]) for r in connection.execute("SELECT subject_claim_id, object_claim_id, relation_type FROM claim_relations")}
                    for row in connection.execute("SELECT p.payload_json FROM review_proposals p LEFT JOIN proposal_derivations d ON d.proposal_id = p.id WHERE p.proposal_type = 'claim' AND COALESCE(d.derivation_status, 'current') = 'current'"):
                        p = json.loads(row[0])
                        if p.get("operation") == "create_relation":
                            existing.add(_relation_key(p["subject_claim_id"], p["object_claim_id"], p["relation_type"]))
                    for draft in drafts:
                        a, b = [claim_input(connection, draft[k])["resolved_id"] for k in ("subject_claim_id", "object_claim_id")]
                        key = _relation_key(a, b, draft["relation_type"])
                        if key in existing:
                            continue
                        proposal = create_claim_proposal(draft, "plan-relations-v1", model_profile.get("model", profile),
                            {"generation_job_id": job["id"], "plan_id": run["plan_id"], "plan_run_id": run_id, "input_versions": versions,
                             "recomputed_proposal_ids": report["recomputed_proposal_ids"]},
                            path, _claim_versions=versions, _connection=connection)
                        report["proposal_ids"].append(proposal["id"])
                        existing.add(key)
                    _finish(connection, job["id"], run_id, status, report)
                continue
        except Exception as error:
            status = "failed"
            report["proposal_ids"] = []
            report["warnings"].append(f"Relation batch failed ({type(error).__name__}); retry on next Run.")
        with _database(path) as connection:
            _finish(connection, job["id"], run_id, status, report)
        successful = successful and status == "completed"
    return successful


def _finish(connection, job_id, run_id, status, report):
    connection.execute("UPDATE plan_relation_jobs SET status = ?, report_json = ? WHERE id = ?", (status, json.dumps(report), job_id))
    connection.execute("UPDATE generation_attempts SET status = ?, report_json = ? WHERE run_id = ? AND job_id = ?", (status, json.dumps(report), run_id, job_id))
