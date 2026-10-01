"""Read-only optimistic knowledge overlay. Never accepts proposals or writes pages."""
from __future__ import annotations

import copy
import json

from .proposal_dependencies import version, claim_input, merge_input


def project(connection, reviewed):
    from .knowledge import _WIKI_CLAIM_LINK, remap_merged_wiki_pages
    result = copy.deepcopy(reviewed)
    claims = {c["id"]: c for c in result["claims"]
              if c["lifecycle"] == "active" and not c.get("needs_review")}
    edges = list(result["graph"]["edges"])
    rows = connection.execute("""SELECT p.*, COALESCE(d.derivation_status, 'current') AS derivation
        FROM review_proposals p LEFT JOIN proposal_derivations d ON d.proposal_id = p.id
        WHERE p.proposal_type = 'claim' AND p.status = 'awaiting_review'
        ORDER BY p.created_at, p.id""").fetchall()
    pending, excluded, deferred = [], [], []
    merge_uses = {}
    for row in rows:
        payload = json.loads(row["payload_json"])
        if payload.get("operation") == "merge_claims" and row["derivation"] == "current":
            for cid in (payload.get("source_claim_id"), payload.get("target_claim_id")):
                merge_uses[cid] = merge_uses.get(cid, 0) + 1
    current, replacements, merge_replacements = [], {}, {}
    for row in rows:
        if row["derivation"] != "current":
            excluded.append(row["id"])
            continue
        payload = json.loads(row["payload_json"])
        operation = payload.get("operation", "create_claim")
        if operation == "merge_claims":
            ids = [payload["target_claim_id"], payload["source_claim_id"]]
            if any(merge_uses[cid] > 1 for cid in ids):
                deferred.append(row["id"])
                continue
            try:
                payload = merge_input(connection, payload)
            except ValueError:
                excluded.append(row["id"])
                continue
            for cid in ids:
                replacements[cid] = "proposal:" + row["id"]
                merge_replacements[cid] = replacements[cid]
                claims.pop(cid, None)
        if operation == "review_evidence_change":
            try:
                claim_input(connection, "proposal:" + row["id"])
            except ValueError:
                excluded.append(row["id"])
                continue
            replacements[payload["target_claim_id"]] = "proposal:" + row["id"]
        if operation not in {"create_claim", "create_relation", "link_evidence", "review_evidence_change", "merge_claims"}:
            deferred.append(row["id"])
            continue
        provenance = {"proposal_id": row["id"], "review_status": "awaiting_review",
                      "input_version": version(payload, "claim"),
                      "scope": json.loads(row["scope_json"])}
        current.append((row["id"], operation, payload, provenance))
        if operation in {"create_claim", "review_evidence_change", "merge_claims"}:
            claim_id = "proposal:" + row["id"]
            claims[claim_id] = {**payload, "id": claim_id, "lifecycle": "active",
                "needs_review": False, "review_state": "awaiting_review",
                "updated_at": row["created_at"], "projection": provenance}
            pending.append(row["id"])
    # Match reviewed merge semantics: remap identities, drop self-edges and dedup.
    # Ordinary revisions do not inherit old relations.
    remapped = {}
    for edge in edges:
        subject = merge_replacements.get(edge["subject_claim_id"], edge["subject_claim_id"])
        target = merge_replacements.get(edge["object_claim_id"], edge["object_claim_id"])
        if subject not in claims or target not in claims or subject == target:
            continue
        projected = {**edge, "subject_claim_id": subject, "object_claim_id": target}
        if subject != edge["subject_claim_id"] or target != edge["object_claim_id"]:
            projected["projection"] = {"review_status": "awaiting_review", "identity_merge": True}
        remapped.setdefault((subject, target, edge["relation_type"]), projected)
    edges = list(remapped.values())
    # Endpoints may precede or follow their relation in creation order.
    for proposal_id, operation, payload, provenance in current:
        if operation == "create_relation":
            subject, target = payload.get("subject_claim_id"), payload.get("object_claim_id")
            if subject not in claims or target not in claims:
                excluded.append(proposal_id)
                continue
            identity = (subject, target, payload["relation_type"])
            if not any((e["subject_claim_id"], e["object_claim_id"], e["relation_type"]) == identity for e in edges):
                edges.append({**payload, "id": "proposal:" + proposal_id, "projection": provenance})
            pending.append(proposal_id)
        elif operation == "link_evidence":
            claim = claims.get(payload.get("target_claim_id"))
            if not claim:
                excluded.append(proposal_id)
                continue
            # Preserve reviewed evidence; pending links are visibly separate.
            claim.setdefault("pending_evidence", []).append({"evidence": payload.get("evidence", []), **provenance})
            pending.append(proposal_id)
    for page in result["pages"]:
        referenced = set(page["claim_ids"]) | {match[1] for match in _WIKI_CLAIM_LINK.finditer(page["summary"])}
        if referenced.intersection(replacements):
            page["summary"] = ""
            page["projection_status"] = "stale"
        page["claim_ids"] = list(dict.fromkeys(replacements.get(cid, cid) for cid in page["claim_ids"] if replacements.get(cid, cid) in claims))
    remap_merged_wiki_pages(result["pages"], replacements)
    organization = _organization(connection, reviewed, claims)
    if organization.get("pages") is not None:
        result["pages"] = organization.pop("pages")
        result["stale_claim_ids"] = organization.get("stale_claim_ids", [])
    organized = {cid for page in result["pages"] for cid in page["claim_ids"]}
    result.update(claims=list(claims.values()), graph={"nodes": list(claims.values()), "edges": edges},
                  unorganized_claim_ids=sorted(set(claims) - organized), view="projected",
                  projection={"pending_proposal_ids": pending, "excluded_proposal_ids": excluded,
                              "deferred_proposal_ids": deferred, "organization": organization})
    return result


def _organization(connection, reviewed, claims):
    from .knowledge import _WIKI_CLAIM_LINK, remap_wiki_claim_links
    row = connection.execute("SELECT * FROM wiki_projections ORDER BY rowid DESC LIMIT 1").fetchone()
    if not row:
        return {}
    info = {"id": row["id"], "plan_id": row["plan_id"], "run_id": row["run_id"], "stale_claim_ids": []}
    if connection.execute("SELECT 1 FROM wiki_projection_reviews WHERE projection_id = ?", (row["id"],)).fetchone():
        return {**info, "status": "reviewed", "reviewable": False, "review_blocked_reason": "This organization has already been reviewed.", "message": "Projected organization was applied to the reviewed Wiki."}
    if row["base_revision_id"] != (reviewed.get("revision") or {}).get("id"):
        return {**info, "status": "stale", "reviewable": False, "review_blocked_reason": "Reviewed Wiki structure changed; refresh the projection first.", "message": "Reviewed Wiki structure changed; projected organization needs refresh."}
    versions = json.loads(row["input_versions_json"])
    resolved, valid, stale = {}, set(), set()
    for ref, expected in versions.items():
        try:
            item = claim_input(connection, ref)
            resolved[ref] = item["resolved_id"]
            if item["input_version"] == expected and item["resolved_id"] in claims:
                valid.add(ref)
            elif item["resolved_id"] in claims:
                stale.add(item["resolved_id"])
        except ValueError:
            # If the stale pending Claim is no longer projected, never show its old text.
            pass
    pages, changed = [], 0
    for page in json.loads(row["payload_json"])["pages"]:
        dependencies = set(page["claim_ids"]) | {m[1] for m in _WIKI_CLAIM_LINK.finditer(page["summary"])}
        outdated = not dependencies.issubset(valid)
        changed += int(outdated)
        pages.append({"id": page["key"], "parent_id": page["parent_key"] or None,
            "title": page["title"], "summary": "" if outdated else remap_wiki_claim_links(page["summary"], resolved),
            "claim_ids": [resolved[cid] for cid in page["claim_ids"] if cid in valid],
            "projection_status": "stale" if outdated else "current"})
    pending = sum(value.startswith("proposal:") for value in resolved.values())
    reason = "Refresh stale projected Pages before reviewing the structure." if changed else f"Review {pending} pending Claim(s) first." if pending else ""
    return {**info, "pages": pages, "status": "stale" if changed else "current",
            "reviewable": not reason, "review_blocked_reason": reason,
            "stale_pages": changed, "stale_claim_ids": sorted(stale)}
