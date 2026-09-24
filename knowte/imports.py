from __future__ import annotations

import base64
from io import BytesIO
import json
from pathlib import Path
import sqlite3
from typing import Any
from zipfile import BadZipFile, ZipFile
from .documents import parse_document, MAX_DOCUMENT_BYTES

from .knowledge import (
    create_artifact,
    create_claim,
    create_claim_relation,
    create_wiki_proposal,
    accept_project_wiki_proposal,
    finish_project_import,
    finish_wiki_import,
    get_project_import,
    get_wiki_import,
    import_evidence,
    link_project_knowledge,
    list_claims,
    list_evidence,
    save_project_document,
    save_source,
    merge_imported_wiki,
    remap_wiki_claim_links,
    stage_project_import,
    stage_wiki_import,
    store_capture,
)


MAX_IMPORT_BYTES = 100 * 1024 * 1024


def _read_package(raw: bytes) -> tuple[dict[str, Any], dict[str, Any], ZipFile]:
    if not raw or len(raw) > MAX_IMPORT_BYTES:
        raise ValueError("Knowledge package must be between 1 byte and 100 MB")
    try:
        archive = ZipFile(BytesIO(raw))
        names = set(archive.namelist())
        if "manifest.json" not in names or "data.json" not in names:
            raise ValueError("This is not a Knowte knowledge package")
        if any(name.startswith("/") or ".." in Path(name).parts for name in names):
            raise ValueError("Knowledge package contains an unsafe path")
        manifest = json.loads(archive.read("manifest.json"))
        data = json.loads(archive.read("data.json"))
    except (BadZipFile, json.JSONDecodeError, KeyError) as error:
        raise ValueError("Knowledge package is damaged or invalid") from error
    if manifest.get("application") != "Knowte":
        raise ValueError("Knowledge package was not created by Knowte")
    if manifest.get("export_schema_version") != 1:
        raise ValueError("This Knowte export schema is not supported")
    if manifest.get("export_type") not in {"wiki", "project"}:
        raise ValueError("Only Wiki and Project packages can be imported")
    if not isinstance(data, dict):
        raise ValueError("Knowledge package data is invalid")
    return manifest, data, archive


def stage_project_package_import(
    encoded: str, filename: str, database_path: Path, content_dir: Path,
) -> dict[str, Any]:
    try:
        raw = base64.b64decode(str(encoded or ""), validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError("Knowledge package encoding is invalid") from error
    manifest, data, archive = _read_package(raw)
    archive.close()
    if manifest["export_type"] != "project":
        raise ValueError("Projects can only import a Knowte Project package")
    exported_project = data.get("project") if isinstance(data.get("project"), dict) else {}
    title = str(exported_project.get("title") or "Imported Wiki").strip()[:200]
    purpose = str(exported_project.get("purpose") or "Review this shared Project before using it.").strip()[:4000]
    project = create_artifact({
        "title": f"{title} · Import review",
        "purpose": purpose,
        "status": "reviewing",
    }, database_path)
    import_dir = content_dir / "imports"
    import_dir.mkdir(parents=True, exist_ok=True)
    archive_path = import_dir / f"{project['id']}.zip"
    archive_path.write_bytes(raw)
    counts = {
        key: len(data.get(key) or []) for key in ("sources", "evidence", "claims")
    }
    staged = stage_project_import(
        project["id"], filename, archive_path,
        {"export_type": "project", "counts": counts},
        database_path,
    )
    return {"project": project, "import": staged}


def stage_wiki_package_import(
    encoded: str, filename: str, database_path: Path, content_dir: Path,
) -> dict[str, Any]:
    try:
        raw = base64.b64decode(str(encoded or ""), validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError("Knowledge package encoding is invalid") from error
    manifest, data, archive = _read_package(raw)
    archive.close()
    if manifest["export_type"] != "wiki":
        raise ValueError("Wiki can only import a Knowte Wiki package")
    import_dir = content_dir / "imports"
    import_dir.mkdir(parents=True, exist_ok=True)
    counts = {key: len(data.get(key) or []) for key in ("sources", "evidence", "claims")}
    placeholder = stage_wiki_import(
        filename, import_dir / "pending", {"export_type": "wiki", "counts": counts},
        database_path,
    )
    archive_path = import_dir / f"wiki-{placeholder['id']}.zip"
    archive_path.write_bytes(raw)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE wiki_imports SET archive_path = ? WHERE id = ?",
            (str(archive_path), placeholder["id"]),
        )
    return placeholder


def _accept_package(
    staged: dict[str, Any], project_id: str, database_path: Path,
) -> dict[str, Any]:
    if not staged or staged.get("status") != "awaiting_review":
        raise ValueError("Import is not awaiting review")
    archive_path = Path(staged["archive_path"])
    try:
        raw = archive_path.read_bytes()
    except OSError as error:
        raise ValueError("Imported knowledge package is missing") from error
    manifest, data, archive = _read_package(raw)
    expected_type = "project" if project_id else "wiki"
    if manifest["export_type"] != expected_type:
        raise ValueError(f"This is not a Knowte {expected_type.title()} package")
    imported_sources = [item for item in (data.get("sources") or []) if isinstance(item, dict)]
    imported_evidence = [item for item in (data.get("evidence") or []) if isinstance(item, dict)]
    imported_claims = [item for item in (data.get("claims") or []) if isinstance(item, dict)]
    source_ids = {str(item.get("id") or "") for item in imported_sources}
    evidence_ids = {str(item.get("id") or "") for item in imported_evidence}
    if "" in source_ids or any(
        str(item.get("source_id") or "") not in source_ids for item in imported_evidence
    ):
        raise ValueError("Imported Evidence has an invalid Source reference")
    for item in imported_evidence:
        evidence_type = str(item.get("evidence_type") or "text")
        if evidence_type == "text" and not str(item.get("quote") or "").strip():
            raise ValueError("Imported text Evidence has no quote")
        if evidence_type == "snapshot" and f"assets/evidence-{item.get('id')}.png" not in archive.namelist():
            raise ValueError("Imported Snapshot Evidence is missing its image")
    for item in imported_claims:
        if not str(item.get("statement") or "").strip():
            raise ValueError("Imported Claim has no statement")
        if str(item.get("basis") or "reported") not in {"background", "reported", "inference"}:
            raise ValueError("Imported Claim uses an unsupported basis")
        linked_ids = {
            str(link.get("evidence_id") or "") for link in (item.get("evidence") or [])
            if isinstance(link, dict)
        }
        if not linked_ids.issubset(evidence_ids):
            raise ValueError("Imported Claim has an invalid Evidence reference")
        if not linked_ids and not item.get("intentionally_ungrounded"):
            raise ValueError("Imported Claim is neither grounded nor explicitly background knowledge")
    source_map: dict[str, str] = {}
    evidence_map: dict[str, str] = {}
    claim_map: dict[str, str] = {}
    created = {"sources": 0, "evidence": 0, "claims": 0}
    reused = {"sources": 0, "evidence": 0, "claims": 0}

    documents = {}
    for source in imported_sources:
        if source.get("document_hash"):
            filename = str(source.get("document_filename") or "")
            asset = f"assets/source-{source.get('id')}{Path(filename).suffix.lower()}"
            if asset not in archive.namelist() or archive.getinfo(asset).file_size > MAX_DOCUMENT_BYTES:
                raise ValueError("Local document is missing or exceeds 20 MB")
            raw = archive.read(asset)
            captured = parse_document(raw, filename)
            if captured["sha256"] != source["document_hash"]:
                raise ValueError("Local document checksum does not match")
            documents[source["id"]] = (raw, captured, Path(filename).suffix.lower())
    for source in imported_sources:
        saved, was_created, _ = save_source(source, project_id or None, database_path)
        if source.get("id") in documents:
            raw, captured, suffix = documents[source["id"]]
            document_dir = database_path.parent / "content"
            document_dir.mkdir(parents=True, exist_ok=True)
            original = document_dir / f"{captured['sha256']}{suffix}"
            original.write_bytes(raw)
            captured["raw_path"] = str(original)
            store_capture(saved["id"], captured, database_path)
        source_map[str(source.get("id") or "")] = saved["id"]
        created["sources"] += int(was_created)
        reused["sources"] += int(not was_created)

    existing_evidence = list_evidence(database_path)
    evidence_keys = {
        (item.get("source_id"), item.get("quote"), item.get("locator")): item["id"]
        for item in existing_evidence
    }
    for item in imported_evidence:
        source_id = source_map.get(str(item.get("source_id") or ""))
        if not source_id:
            continue
        key = (source_id, item.get("quote"), item.get("locator"))
        evidence_id = evidence_keys.get(key)
        if evidence_id:
            if project_id:
                link_project_knowledge(project_id, "evidence", evidence_id, database_path)
            reused["evidence"] += 1
        else:
            image_data = ""
            asset_name = f"assets/evidence-{item.get('id')}.png"
            if item.get("evidence_type") == "snapshot" and asset_name in archive.namelist():
                image_data = "data:image/png;base64," + base64.b64encode(
                    archive.read(asset_name)
                ).decode("ascii")
            imported = import_evidence(
                source_id, item, project_id, image_data, database_path,
            )
            evidence_id = imported["id"]
            evidence_keys[key] = evidence_id
            created["evidence"] += 1
        evidence_map[str(item.get("id") or "")] = evidence_id

    existing_claims = list_claims(database_path)
    claim_keys = {
        " ".join(str(item.get("statement") or "").casefold().split()): item["id"]
        for item in existing_claims if item.get("lifecycle") == "active"
    }
    for item in imported_claims:
        key = " ".join(str(item.get("statement") or "").casefold().split())
        claim_id = claim_keys.get(key)
        if claim_id:
            if project_id:
                link_project_knowledge(project_id, "claim", claim_id, database_path)
            reused["claims"] += 1
        else:
            links = []
            for link in item.get("evidence") or []:
                if not isinstance(link, dict):
                    continue
                evidence_id = evidence_map.get(str(link.get("evidence_id") or ""))
                if evidence_id:
                    links.append({
                        "evidence_id": evidence_id,
                        "stance": link.get("stance") or "supports",
                        "rationale": link.get("rationale") or "",
                    })
            payload = {
                "statement": item.get("statement"),
                "basis": item.get("basis") or "reported",
                "review_state": item.get("review_state") or "accepted",
                "evidence": links,
                "intentionally_ungrounded": bool(item.get("intentionally_ungrounded")),
                "artifact_ids": [project_id] if project_id else [],
                "created_via": "import",
                "change_note": "Accepted from a reviewed Knowte import",
                "tags": [
                    tag.get("name") if isinstance(tag, dict) else tag
                    for tag in (item.get("tags") or [])
                ],
            }
            claim = create_claim(payload, database_path)
            claim_id = claim["id"]
            claim_keys[key] = claim_id
            created["claims"] += 1
        claim_map[str(item.get("id") or "")] = claim_id

    for item in imported_claims:
        for relation in item.get("relations") or []:
            if not isinstance(relation, dict):
                continue
            subject = claim_map.get(str(relation.get("subject_claim_id") or ""))
            object_ = claim_map.get(str(relation.get("object_claim_id") or ""))
            if not subject or not object_ or subject == object_:
                continue
            try:
                create_claim_relation({
                    "subject_claim_id": subject,
                    "object_claim_id": object_,
                    "relation_type": relation.get("relation_type") or "related",
                    "rationale": relation.get("rationale") or "",
                }, database_path)
            except ValueError:
                pass

    project_payload = data.get("project") if isinstance(data.get("project"), dict) else {}
    if project_id:
        for document in project_payload.get("documents") or []:
            if isinstance(document, dict) and isinstance(document.get("content"), dict):
                content = document["content"]
                for section in content.get("sections") or []:
                    for paragraph in section.get("paragraphs") or []:
                        paragraph["claim_ids"] = [
                            claim_map[item] for item in paragraph.get("claim_ids", [])
                            if item in claim_map
                        ]
                if "selected_claim_ids" in content:
                    content["selected_claim_ids"] = [
                        claim_map[item] for item in content["selected_claim_ids"]
                        if item in claim_map
                    ]
                save_project_document({
                    "artifact_id": project_id,
                    "title": document.get("title") or "Imported Article",
                    "goal": document.get("goal") or "",
                    "content": content,
                }, database_path)
        exported_wiki = project_payload.get("wiki") or {}
        structure = exported_wiki.get("graph_state") or {}
        pages = structure.get("pages") or []
        if pages:
            for page in pages:
                page["summary"] = remap_wiki_claim_links(page.get("summary"), claim_map)
                page["claim_ids"] = [
                    claim_map[item] for item in page.get("claim_ids", [])
                    if item in claim_map
                ]
            if any(page["claim_ids"] for page in pages):
                proposal = create_wiki_proposal(
                    {"pages": pages, "gaps": structure.get("gaps", [])},
                    "project-import-v1", scope={"project_id": project_id},
                    path=database_path, proposal_type="project_wiki_patch",
                )
                accept_project_wiki_proposal(proposal["id"], database_path)
    if project_id and isinstance(data.get("wiki"), dict):
        save_project_document({
            "artifact_id": project_id,
            "title": "Imported Wiki structure",
            "goal": "Preserve the shared Wiki organization inside this Project.",
            "content": {"type": "wiki", "wiki": data["wiki"]},
        }, database_path)
    archive.close()
    imported_pages = 0
    if not project_id and isinstance(data.get("wiki"), dict):
        imported_pages = merge_imported_wiki(
            Path(staged.get("filename") or "Imported Wiki").stem,
            data["wiki"], claim_map, database_path,
        )
    return {"project_id": project_id, "created": created, "reused": reused,
            "imported_pages": imported_pages}


def accept_project_import(
    project_id: str, database_path: Path, content_dir: Path,
) -> dict[str, Any]:
    staged = get_project_import(project_id, database_path)
    result = _accept_package(staged, project_id, database_path)
    finish_project_import(project_id, "imported", database_path)
    Path(staged["archive_path"]).unlink(missing_ok=True)
    return result


def accept_wiki_import(
    import_id: str, database_path: Path, content_dir: Path,
) -> dict[str, Any]:
    staged = get_wiki_import(import_id, database_path)
    result = _accept_package(staged, "", database_path)
    finish_wiki_import(import_id, "imported", database_path)
    Path(staged["archive_path"]).unlink(missing_ok=True)
    return result


def discard_wiki_import(import_id: str, database_path: Path) -> None:
    staged = get_wiki_import(import_id, database_path)
    if not staged or staged.get("status") != "awaiting_review":
        raise ValueError("Wiki import is not awaiting review")
    finish_wiki_import(import_id, "discarded", database_path)
    try:
        Path(staged["archive_path"]).unlink()
    except OSError:
        pass
