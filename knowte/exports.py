from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from .knowledge import (
    get_project,
    get_snapshot_file,
    get_source,
    get_wiki,
    list_claims,
    list_evidence,
)


EXPORT_SCHEMA_VERSION = 1


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _tag_names(item: dict[str, Any]) -> list[str]:
    return [str(tag.get("name") or "") for tag in item.get("tags", []) if tag.get("name")]


def _source_url(source: dict[str, Any]) -> str:
    return str(
        source.get("paper_url") or source.get("url") or source.get("doi_url") or ""
    )


def _quote(value: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in value.splitlines())


def _claims_markdown(
    claims: list[dict[str, Any]], evidence: dict[str, dict], sources: dict[str, dict]
) -> str:
    lines = ["# Knowte Claims Export", ""]
    for claim in claims:
        lines.extend([
            f"## {claim.get('statement') or 'Claim'}",
            "",
            f"Basis: {claim.get('basis', '')}",
            f"Review: {claim.get('review_state', '')}",
            f"Lifecycle: {claim.get('lifecycle', '')}",
        ])
        if tags := _tag_names(claim):
            lines.append(f"Tags: {', '.join(tags)}")
        if claim.get("evidence"):
            lines.extend(["", "### Evidence", ""])
        for link in claim.get("evidence", []):
            item = evidence.get(link.get("evidence_id", ""), {})
            source = sources.get(item.get("source_id", ""), {})
            title = item.get("source_title") or source.get("title") or "Source"
            url = _source_url(source)
            heading = f"[{title}]({url})" if url else title
            lines.extend([
                f"- **{link.get('stance', 'related')}** · {heading}",
                f"  {_quote(str(item.get('quote') or '')).replace(chr(10), chr(10) + '  ')}",
            ])
        if claim.get("relations"):
            lines.extend(["", "### Claim relations", ""])
            for relation in claim["relations"]:
                lines.append(
                    f"- `{relation.get('subject_claim_id', '')}` "
                    f"**{relation.get('relation_type', '')}** "
                    f"`{relation.get('object_claim_id', '')}`"
                )
        for annotation in claim.get("annotations", []):
            lines.append(f"- Annotation: {annotation.get('body', '')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _wiki_markdown(
    wiki: dict[str, Any], claims: dict[str, dict], evidence: dict[str, dict],
    sources: dict[str, dict],
) -> str:
    lines = ["# Knowte Wiki", ""]
    pages = wiki.get("pages", [])
    page_by_id = {page["id"]: page for page in pages}
    depths: dict[str, int] = {}

    def depth(page: dict[str, Any]) -> int:
        if page["id"] in depths:
            return depths[page["id"]]
        parent = page_by_id.get(page.get("parent_id"))
        depths[page["id"]] = 0 if parent is None else min(depth(parent) + 1, 4)
        return depths[page["id"]]

    for page in pages:
        lines.extend([f"{'#' * (depth(page) + 2)} {page.get('title') or 'Untitled'}", ""])
        if page.get("summary"):
            lines.extend([str(page["summary"]), ""])
        for claim_id in page.get("claim_ids", []):
            claim = claims.get(claim_id)
            if not claim:
                continue
            lines.append(f"- {claim.get('statement', '')}")
            for link in claim.get("evidence", []):
                item = evidence.get(link.get("evidence_id", ""), {})
                source = sources.get(item.get("source_id", ""), {})
                title, url = source.get("title") or "Source", _source_url(source)
                lines.append(f"  - {link.get('stance', '')}: [{title}]({url})" if url else f"  - {link.get('stance', '')}: {title}")
        lines.append("")
    unorganized = [
        claim_id for claim_id in wiki.get("unorganized_claim_ids", [])
        if claim_id in claims
    ]
    if unorganized:
        lines.extend(["## Unorganized", ""])
        for claim_id in unorganized:
            lines.append(f"- {claims[claim_id].get('statement', '')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _project_markdown(
    project: dict[str, Any], claims: dict[str, dict], evidence: dict[str, dict],
    sources: dict[str, dict],
) -> str:
    lines = [f"# {project.get('title') or 'Knowte Project'}", ""]
    if project.get("purpose"):
        lines.extend([str(project["purpose"]), ""])
    lines.extend(["## Claims", ""])
    body = _claims_markdown(list(claims.values()), evidence, sources).splitlines()
    lines.extend(body[2:] if len(body) > 2 else body)
    documents = project.get("documents") or []
    if documents:
        lines.extend(["", "## Generated Articles", ""])
        for document in documents:
            lines.append(f"- {document.get('title') or 'Untitled Article'}")
    return "\n".join(lines).rstrip() + "\n"


def build_knowledge_export(
    kind: str,
    entity_ids: list[str] | None,
    database_path: Path,
    content_dir: Path,
) -> tuple[str, bytes]:
    kind = str(kind or "").strip().lower()
    if kind not in {"wiki", "project"}:
        raise ValueError("Export type must be Wiki or Project")
    requested = list(dict.fromkeys(str(item) for item in (entity_ids or []) if item))
    all_evidence = {item["id"]: item for item in list_evidence(database_path)}
    all_claims = {item["id"]: item for item in list_claims(database_path)}
    wiki = get_wiki(database_path) if kind == "wiki" else {}
    project = None
    if kind == "wiki":
        claim_ids = [
            claim["id"] for claim in wiki.get("claims", [])
            if claim.get("lifecycle") == "active"
        ]
        if not claim_ids:
            raise ValueError("The Wiki has no reviewed Claims to export")
    else:
        if len(requested) != 1:
            raise ValueError("Choose one Project to export")
        project = get_project(requested[0], database_path)
        claim_ids = [claim["id"] for claim in project.get("claims", [])]
    evidence_ids = list(dict.fromkeys(
        link.get("evidence_id", "")
        for claim_id in claim_ids for link in all_claims.get(claim_id, {}).get("evidence", [])
        if link.get("evidence_id")
    ))
    if project:
        evidence_ids = list(dict.fromkeys(
            evidence_ids + [item["id"] for item in project.get("evidence", [])]
        ))

    evidence = [all_evidence[item] for item in evidence_ids if item in all_evidence]
    claims = [all_claims[item] for item in claim_ids if item in all_claims]
    source_ids = list(dict.fromkeys(
        [item.get("source_id", "") for item in evidence]
        + ([item["id"] for item in project.get("sources", [])] if project else [])
    ))
    sources = {
        source_id: get_source(source_id, database_path)
        for source_id in source_ids if source_id
    }
    evidence_by_id = {item["id"]: item for item in evidence}
    claims_by_id = {item["id"]: item for item in claims}
    wiki_payload = None
    project_payload = None
    if kind == "wiki":
        included = set(claim_ids)
        wiki_payload = {
            "pages": wiki.get("pages", []),
            "graph": {
                "nodes": claims,
                "edges": [
                    edge for edge in wiki.get("graph", {}).get("edges", [])
                    if edge.get("subject_claim_id") in included
                    and edge.get("object_claim_id") in included
                ],
            },
            "unorganized_claim_ids": [
                item for item in wiki.get("unorganized_claim_ids", []) if item in included
            ],
            "stale_claim_ids": wiki.get("stale_claim_ids", []),
            "revision": wiki.get("revision"),
        }
    elif project:
        project_payload = {
            key: project.get(key) for key in (
                "id", "title", "purpose", "status", "created_at", "updated_at",
            )
        }
        project_payload["claim_ids"] = claim_ids
        project_payload["evidence_ids"] = evidence_ids
        project_payload["source_ids"] = list(sources)
        project_payload["documents"] = project.get("documents", [])
    exported_at = _now()
    manifest = {
        "application": "Knowte",
        "export_schema_version": EXPORT_SCHEMA_VERSION,
        "export_type": kind,
        "exported_at": exported_at.isoformat(timespec="seconds"),
        "counts": {"sources": len(sources), "evidence": len(evidence), "claims": len(claims)},
        "import_behavior": (
            "trusted_wiki_review" if kind == "wiki" else "review_as_project"
        ),
        "note": (
            "A Wiki package is reviewed once, then merged with all dependent knowledge."
            if kind == "wiki" else
            "A Project package opens as a reviewable Project before its knowledge is accepted."
        ),
    }
    data = {
        "manifest": manifest,
        "sources": list(sources.values()),
        "evidence": evidence,
        "claims": claims,
        "wiki": wiki_payload,
        "project": project_payload,
    }
    markdown = _wiki_markdown(
        wiki_payload or {}, claims_by_id, evidence_by_id, sources,
    ) if kind == "wiki" else _project_markdown(
        project_payload or {}, claims_by_id, evidence_by_id, sources,
    )
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        archive.writestr("data.json", json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        archive.writestr("content.md", markdown)
        for item in evidence:
            if not item.get("has_snapshot"):
                continue
            try:
                snapshot = get_snapshot_file(item["id"], content_dir, database_path)
            except ValueError:
                continue
            archive.write(snapshot, f"assets/evidence-{item['id']}.png")
    stamp = exported_at.strftime("%Y%m%d-%H%M%S")
    return f"knowte-{kind}-{stamp}.zip", buffer.getvalue()
