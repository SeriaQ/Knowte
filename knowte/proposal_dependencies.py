"""Versioned provisional references, independent of proposal review status.

Functions share the caller's transaction. No model calls or automatic acceptance.
"""
from __future__ import annotations

import hashlib
import json


def evidence_input(connection, reference):
    """Resolve a stable automation output reference without accepting it."""
    parent_id = reference.removeprefix("proposal:")
    row = connection.execute("SELECT payload_json FROM review_proposals WHERE id = ? AND proposal_type = 'evidence'", (parent_id,)).fetchone() if reference.startswith("proposal:") else None
    if row:
        payload = json.loads(row[0])
        if payload.get("verification") == "external_unverified" and not payload.get("locator"):
            payload["locator"] = "Imported Evidence"
        resolved_id = reference
    else:
        outcome = connection.execute("SELECT * FROM proposal_outcomes WHERE proposal_id = ? AND proposal_type = 'evidence' AND decision = 'accepted'", (parent_id,)).fetchone() if reference.startswith("proposal:") else None
        resolved_id = outcome["result_id"] if outcome else reference
        evidence = connection.execute("SELECT * FROM evidence WHERE id = ?", (resolved_id,)).fetchone()
        if not evidence:
            raise ValueError("Evidence input was rejected, deleted or is unavailable")
        payload = dict(evidence)
    source = connection.execute("SELECT title, provider FROM sources WHERE id = ?", (payload["source_id"],)).fetchone()
    if not source:
        raise ValueError("Evidence Source is unavailable")
    logical = {key: payload.get(key) or "" for key in ("quote", "locator", "source_id", "evidence_type")}
    meaning = dict(logical)
    if not resolved_id.startswith("proposal:"):
        # Ignore only the trailing non-logical edits. Never erase an earlier
        # meaningful revision or its already-stale descendants.
        for row in connection.execute("SELECT snapshot_json FROM evidence_revisions WHERE evidence_id = ? ORDER BY revision DESC", (resolved_id,)):
            previous = json.loads(row[0])
            if not previous.get("logical_version_preserved"):
                break
            meaning.update(quote=previous["quote"], locator=previous["locator"])
    fingerprint = hashlib.sha256(json.dumps(meaning, sort_keys=True).encode()).hexdigest()
    tags = payload.get("tags", [])
    return {**logical, "logical_quote": meaning["quote"], "id": reference, "resolved_id": resolved_id, "input_version": fingerprint,
            "source_title": source["title"], "source_provider": source["provider"],
            "tags": [{"name": tag} for tag in tags if isinstance(tag, str)]}


def prepare_inputs(connection, payload, expected):
    accepted = []
    links = []
    for link in payload.get("evidence") or []:
        ref = link.get("evidence_id", "")
        current = evidence_input(connection, ref)
        if expected.get(ref) != current["input_version"]:
            raise ValueError("Evidence changed during generation; generated draft was not saved")
        links.append({**link, "evidence_id": current["resolved_id"]})
        if not current["resolved_id"].startswith("proposal:"):
            parent_id = ref[9:] if ref.startswith("proposal:") else "evidence:" + ref
            accepted.append((parent_id, current["input_version"], current["resolved_id"]))
    return {**payload, "evidence": links}, accepted


def validate_recheck(connection, payload):
    """Only a current AI suggestion can stand in for a reviewed Claim."""
    suggestion = payload.get("ai_recheck") or {}
    if not suggestion or suggestion.get("change_token") != payload.get("change_token"):
        raise ValueError("Claim revision has no current AI suggestion")
    claim = connection.execute("SELECT current_revision_id, lifecycle FROM claims WHERE id = ?", (payload["target_claim_id"],)).fetchone()
    if not claim or claim["lifecycle"] != "active" or claim["current_revision_id"] != payload["claim_revision_id"]:
        raise ValueError("Reviewed Claim changed after this suggestion")
    for ref, expected in suggestion.get("input_versions", {}).items():
        if evidence_input(connection, ref)["input_version"] != expected:
            raise ValueError("Evidence changed after this suggestion")


def merge_input(connection, payload):
    from .knowledge import _claim_payload
    ids = [payload["target_claim_id"], payload["source_claim_id"]]
    if not payload.get("merge_versions"):
        raise ValueError("Merge has no input snapshot; review a fresh proposal")
    items = []
    for cid in ids:
        current = claim_input(connection, cid)
        if current["input_version"] != payload["merge_versions"].get(cid):
            raise ValueError("Merge input changed; review a fresh proposal")
        items.append(_claim_payload(connection, connection.execute("SELECT * FROM claims WHERE id = ?", (cid,)).fetchone()))
    links = {link["evidence_id"]: link for item in reversed(items) for link in item["evidence"]}
    return {**payload, "statement": payload.get("merged_statement") or items[0]["statement"],
            "basis": items[0]["basis"], "evidence": list(links.values())}


def claim_input(connection, reference):
    """Resolve a Claim endpoint and fingerprint its meaning, not temporary IDs."""
    from .knowledge import _claim_payload
    proposal_id = reference[9:] if reference.startswith("proposal:") else ""
    row = connection.execute("SELECT * FROM review_proposals WHERE id = ? AND proposal_type = 'claim'", (proposal_id,)).fetchone() if proposal_id else None
    if row:
        payload = json.loads(row["payload_json"])
        operation = payload.get("operation", "create_claim")
        if operation == "review_evidence_change":
            validate_recheck(connection, payload)
        if operation == "merge_claims":
            payload = merge_input(connection, payload)
        if operation not in {"create_claim", "review_evidence_change", "merge_claims"} or describe(connection, proposal_id)["status"] != "current":
            raise ValueError("Claim input is not a current new Claim")
        resolved_id = reference
    else:
        outcome = connection.execute("SELECT result_id FROM proposal_outcomes WHERE proposal_id = ? AND decision = 'accepted'", (proposal_id,)).fetchone() if proposal_id else None
        resolved_id = outcome[0] if outcome else reference
        row = connection.execute("SELECT * FROM claims WHERE id = ?", (resolved_id,)).fetchone()
        if not row:
            raise ValueError("Claim input is unavailable")
        payload = _claim_payload(connection, row)
        if payload["lifecycle"] != "active" or payload.get("needs_review"):
            raise ValueError("Claim input needs review or is inactive")
    grounding, logical_grounding = [], []
    for link in payload.get("evidence", []):
        item = evidence_input(connection, link["evidence_id"])
        grounding.append({"source_id": item["source_id"], "quote": item["quote"], "stance": link["stance"]})
        logical_grounding.append({"source_id": item["source_id"], "quote": item["logical_quote"], "stance": link["stance"]})
    logical = {"statement": payload["statement"], "basis": payload["basis"],
               "grounding": sorted(logical_grounding, key=lambda item: json.dumps(item, sort_keys=True))}
    fingerprint = hashlib.sha256(json.dumps(logical, sort_keys=True).encode()).hexdigest()
    return {**logical, "grounding": grounding, "id": reference, "resolved_id": resolved_id, "input_version": fingerprint,
            "review_state": "awaiting_review" if resolved_id.startswith("proposal:") else payload.get("review_state", "accepted")}


def prepare_claim_inputs(connection, payload, expected):
    accepted = []
    payload = dict(payload)
    for key in ("subject_claim_id", "object_claim_id"):
        ref = payload[key]
        current = claim_input(connection, ref)
        if expected.get(ref) != current["input_version"]:
            raise ValueError("Claim changed during generation; relation was not saved")
        payload[key] = current["resolved_id"]
        if not current["resolved_id"].startswith("proposal:"):
            parent = ref[9:] if ref.startswith("proposal:") else "claim:" + ref
            accepted.append((parent, current["input_version"], current["resolved_id"]))
    return payload, accepted


def version(payload, kind):
    fields = ("source_id", "segment_id", "quote", "evidence_type", "image_data", "image_url", "locator", "source_url") if kind == "evidence" else (
        "operation", "statement", "basis", "evidence", "target_claim_id",
        "subject_claim_id", "object_claim_id", "relation_type")
    if kind == "claim" and payload.get("operation") == "merge_claims":
        fields += ("source_claim_id", "merged_statement")
    logical = {key: payload.get(key) for key in fields}
    return hashlib.sha256(json.dumps(logical, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def references(payload):
    result = []
    for link in payload.get("evidence") or []:
        reference = str(link.get("evidence_id") or "")
        if reference.startswith("proposal:"):
            result.append((reference[9:], "evidence"))
    for key in ("subject_claim_id", "object_claim_id"):
        reference = str(payload.get(key) or "")
        if reference.startswith("proposal:"):
            result.append((reference[9:], "claim"))
    return list(dict.fromkeys(result))


def register(connection, child_id, payload):
    for parent_id, kind in references(payload):
        parent = connection.execute("SELECT * FROM review_proposals WHERE id = ? AND status = 'awaiting_review'", (parent_id,)).fetchone()
        if not parent or parent["proposal_type"] != kind or parent_id == child_id:
            raise ValueError("Provisional dependency not found or has the wrong type")
        state = connection.execute("SELECT derivation_status FROM proposal_derivations WHERE proposal_id = ?", (parent_id,)).fetchone()
        if state and state[0] != "current":
            raise ValueError("Cannot derive from stale or invalidated proposals")
        parent_payload = json.loads(parent["payload_json"])
        if kind == "claim":
            claim_input(connection, "proposal:" + parent_id)
        connection.execute("INSERT INTO artifact_dependencies (parent_proposal_id, parent_version, child_proposal_id, dependency_mode) VALUES (?, ?, ?, 'provisional')",
            (parent_id, version(parent_payload, kind), child_id))
        connection.execute("INSERT OR IGNORE INTO proposal_derivations VALUES (?, 'current')", (child_id,))


def describe(connection, proposal_id):
    row = connection.execute("SELECT derivation_status FROM proposal_derivations WHERE proposal_id = ?", (proposal_id,)).fetchone()
    dependencies = [dict(item) for item in connection.execute("SELECT * FROM artifact_dependencies WHERE child_proposal_id = ?", (proposal_id,))]
    recompute = connection.execute("SELECT job_id FROM proposal_recomputations WHERE proposal_id = ?", (proposal_id,)).fetchone()
    replacement_ids = [item[0] for item in connection.execute("SELECT o.proposal_id FROM generation_outputs o JOIN review_proposals p ON p.id = o.proposal_id WHERE o.job_id = ?", (recompute[0],))] if recompute and recompute[0] else []
    job = connection.execute("SELECT status FROM plan_claim_jobs WHERE id = ? UNION ALL SELECT status FROM plan_relation_jobs WHERE id = ?", (recompute[0], recompute[0])).fetchone() if recompute and recompute[0] else None
    return {"status": row[0] if row else "current", "dependencies": dependencies,
            "recomputation": {"job_id": recompute[0], "status": job[0] if job else "no_inputs", "replacement_ids": replacement_ids} if recompute else None,
            "pending_count": sum(item["dependency_mode"] == "provisional" and item["derivation_status"] == "current" for item in dependencies)}


def assert_reviewable(connection, proposal_id):
    state = describe(connection, proposal_id)
    if state["status"] != "current":
        raise ValueError("Upstream knowledge changed. Recompute or discard this proposal before accepting it.")
    if state["pending_count"]:
        raise ValueError("Review the upstream Evidence / Claims first; this proposal still depends on pending knowledge.")


def _propagate(connection, parent_id, status):
    queue = [(parent_id, status)]
    visited = set()
    while queue:
        parent, parent_status = queue.pop(0)
        if (parent, parent_status) in visited:
            continue
        visited.add((parent, parent_status))
        children = connection.execute("SELECT child_proposal_id FROM artifact_dependencies WHERE parent_proposal_id = ?", (parent,)).fetchall()
        for child in children:
            child_id = child[0]
            connection.execute("UPDATE artifact_dependencies SET derivation_status = ? WHERE parent_proposal_id = ? AND child_proposal_id = ?", (parent_status, parent, child_id))
            rows = connection.execute("SELECT derivation_status, accepted_id FROM artifact_dependencies WHERE child_proposal_id = ?", (child_id,)).fetchall()
            draft = connection.execute("SELECT payload_json FROM review_proposals WHERE id = ?", (child_id,)).fetchone()
            payload = json.loads(draft[0]) if draft else {}
            invalid_ids = {row[1] for row in rows if row[0] == "invalidated"}
            accepted_inputs = any(link.get("evidence_id") and link["evidence_id"] not in invalid_ids and not str(link["evidence_id"]).startswith("proposal:") for link in payload.get("evidence") or [])
            missing_endpoint = payload.get("operation") == "create_relation" and any(row[0] == "invalidated" for row in rows)
            state = "invalidated" if missing_endpoint or (not accepted_inputs and all(row[0] == "invalidated" for row in rows)) else "stale"
            connection.execute("UPDATE proposal_derivations SET derivation_status = ? WHERE proposal_id = ?", (state, child_id))
            queue.append((child_id, state))


def evidence_changed(connection, evidence_id, *, deleted=False):
    accepted_changed(connection, "evidence", evidence_id, invalidated=deleted)


def accepted_changed(connection, kind, entity_id, *, invalidated=False):
    _propagate(connection, kind + ":" + entity_id, "invalidated" if invalidated else "stale")
    for row in connection.execute("SELECT proposal_id FROM proposal_outcomes WHERE proposal_type = ? AND decision = 'accepted' AND result_id = ?", (kind, entity_id)).fetchall():
        _propagate(connection, row[0], "invalidated" if invalidated else "stale")


def resolve(connection, row, accepted, accepted_payload, now):
    proposal_id = row["id"]
    tracked = connection.execute("SELECT 1 FROM artifact_dependencies WHERE parent_proposal_id = ? OR child_proposal_id = ?", (proposal_id, proposal_id)).fetchone()
    if not tracked:
        tracked = connection.execute("SELECT 1 FROM generation_outputs WHERE proposal_id = ?", (proposal_id,)).fetchone()
    if not tracked:
        return
    original = json.loads(row["payload_json"])
    connection.execute("INSERT INTO proposal_outcomes VALUES (?, ?, ?, ?, ?, ?)",
        (proposal_id, row["proposal_type"], row["payload_json"], "accepted" if accepted is not None else "rejected",
         accepted.get("id") if accepted is not None else None, now))
    if accepted is None:
        _propagate(connection, proposal_id, "invalidated")
        return
    if version(original, row["proposal_type"]) != version(accepted_payload, row["proposal_type"]):
        _propagate(connection, proposal_id, "stale")
        return
    edges = connection.execute("SELECT * FROM artifact_dependencies WHERE parent_proposal_id = ?", (proposal_id,)).fetchall()
    for edge in edges:
        if edge["parent_version"] != version(original, row["proposal_type"]):
            _propagate(connection, proposal_id, "stale")
            return
    for edge in edges:
        connection.execute("UPDATE artifact_dependencies SET dependency_mode = 'accepted', accepted_id = ? WHERE parent_proposal_id = ? AND child_proposal_id = ?",
            (accepted["id"], proposal_id, edge["child_proposal_id"]))
        child = connection.execute("SELECT * FROM review_proposals WHERE id = ?", (edge["child_proposal_id"],)).fetchone()
        if not child:
            continue
        payload = json.loads(child["payload_json"])
        old_version = version(payload, child["proposal_type"])
        reference = "proposal:" + proposal_id
        for link in payload.get("evidence") or []:
            if link.get("evidence_id") == reference:
                link["evidence_id"] = accepted["id"]
        for key in ("subject_claim_id", "object_claim_id"):
            if payload.get(key) == reference:
                payload[key] = accepted["id"]
        connection.execute("UPDATE review_proposals SET payload_json = ? WHERE id = ?", (json.dumps(payload, ensure_ascii=False), child["id"]))
        # Replacing a provisional ID with its accepted ID isn't a logical edit.
        connection.execute("UPDATE artifact_dependencies SET parent_version = ? WHERE parent_proposal_id = ? AND parent_version = ?",
            (version(payload, child["proposal_type"]), child["id"], old_version))
