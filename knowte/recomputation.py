"""Merge stale, still-pending Plan outputs into subsequent generation jobs."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from .proposal_dependencies import evidence_input, claim_input


def queue_stale_jobs(connection, plan_id, run_id, stage):
    table, operation = ("plan_claim_jobs", "create_claim") if stage == "claims" else ("plan_relation_jobs", "create_relation")
    rows = connection.execute(f"""SELECT p.id, p.payload_json, j.id AS old_job, j.policy_json
        FROM review_proposals p JOIN proposal_derivations d ON d.proposal_id = p.id
        JOIN generation_outputs o ON o.proposal_id = p.id JOIN {table} j ON j.id = o.job_id
        WHERE j.plan_id = ? AND p.status = 'awaiting_review' AND d.derivation_status != 'current'
        AND NOT EXISTS (SELECT 1 FROM proposal_recomputations r WHERE r.proposal_id = p.id)
        ORDER BY j.rowid, p.rowid""", (plan_id,)).fetchall()
    groups = {}
    for row in rows:
        payload = json.loads(row["payload_json"])
        if payload.get("operation", "create_claim") != operation:
            continue
        refs = []
        if stage == "claims":
            for link in payload.get("evidence", []):
                try:
                    evidence_input(connection, link["evidence_id"])
                    refs.append(link["evidence_id"])
                except ValueError:
                    continue
        else:
            try:
                pair = tuple(payload[key] for key in ("subject_claim_id", "object_claim_id"))
                for ref in pair:
                    claim_input(connection, ref)
                refs = [pair]
            except ValueError:
                # Replacement pending Claims will discover their own relations.
                pass
        group = groups.setdefault(row["old_job"], {"refs": set(), "ids": [], "policy": row["policy_json"]})
        group["refs"].update(refs)
        group["ids"].append(row["id"])
    for group in groups.values():
        job_id = uuid4().hex if group["refs"] else ""
        if job_id:
            connection.execute(f"INSERT INTO {table} (id, plan_id, first_run_id, input_refs_json, policy_json) VALUES (?, ?, ?, ?, ?)",
                (job_id, plan_id, run_id, json.dumps(sorted(group["refs"])), group["policy"]))
        connection.executemany("INSERT INTO proposal_recomputations VALUES (?, ?, ?)",
            [(proposal_id, job_id, datetime.now(timezone.utc).isoformat()) for proposal_id in group["ids"]])


def recomputation_origins(connection, job_id):
    return [row[0] for row in connection.execute("SELECT proposal_id FROM proposal_recomputations WHERE job_id = ?", (job_id,))]
