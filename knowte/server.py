from __future__ import annotations

import argparse
import base64
from collections import Counter
import functools
import hashlib
from importlib.metadata import PackageNotFoundError, version as package_version
import json
import os
import re
import shutil
import socketserver
import sys
import sysconfig
import threading
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import (
    CONFIG_PATH,
    export_config,
    load_config,
    save_config,
    obsolete_config_items,
    remove_obsolete_config_items,
    set_default_search_mode,
    set_email,
    set_enabled_backends,
    set_intelligent_max_results,
    set_max_papers,
    set_ai_settings,
    set_ai_model_profiles,
    ai_model_profiles,
    ai_available_capabilities,
    ai_role_assignments,
    ai_profile_for_role,
    set_semanticscholar_key,
    set_searxng_url,
    set_searxng_proxy,
    set_web_ignore_year_filter,
)
from .stage_skills import skill_prompt, skill_catalog, manage_skill
from .ai import AIError
from .capture import CaptureError, capture_source_content, capture_evidence_image, discover_source_images
from .documents import import_document, parse_document
from .related_pages import discover_pages, select_pages, page_url, in_scope, MAX_PAGES
from .knowledge import preview_knowledge_deletion, delete_knowledge_items, prepare_wiki_batch, merge_wiki_batch
from .companion import CompanionStore
from .exports import build_knowledge_export
from .imports import (
    accept_project_import,
    accept_wiki_import,
    discard_wiki_import,
    stage_project_package_import,
    stage_wiki_package_import,
)
from .intelligent import (
    _client_from_config,
    _model_name_from_config,
    _verify_batched,
    intelligent_search,
)
from .source_discovery import discover_related_papers
from .knowledge import (
    KNOWLEDGE_DB_PATH,
    create_annotation,
    create_artifact,
    accept_claim_proposal,
    create_claim,
    create_claim_relation,
    create_claim_proposal,
    create_claim_audit,
    preview_claim_audit,
    get_claim_audit,
    get_project,
    list_claim_audits,
    update_claim_audit_status,
    next_claim_audit_batch,
    complete_claim_audit_batch,
    create_evidence_proposal,
    create_project_claim_recommendations,
    create_evidence,
    update_evidence,
    delete_annotation,
    discard_claim_proposal,
    delete_evidence,
    delete_view,
    discard_wiki_proposal,
    get_capture_file,
    get_snapshot_file,
    get_source,
    get_source_workspace,
    get_view,
    get_wiki,
    find_claim_comparison_context,
    list_claim_proposals,
    list_evidence_proposals,
    list_project_claim_recommendations,
    list_claims,
    list_evidence,
    list_artifacts,
    list_tags,
    list_replay_sources,
    list_sources,
    list_views,
    list_wiki_proposals,
    list_wiki_imports,
    link_project_knowledge,
    list_project_documents,
    set_entity_tags,
    add_entity_tags_batch,
    save_source,
    revise_claim,
    set_claim_lifecycle,
    store_capture,
    accept_evidence_proposal,
    accept_project_claim_recommendation,
    update_view,
    create_wiki_proposal,
    create_manual_wiki_proposal,
    update_wiki_proposal,
    accept_wiki_proposal,
    reset_wiki_structure,
    accept_project_wiki_proposal,
    list_project_wiki_proposals,
    save_project_document,
)
from .plans import PLANS_PATH, create_plan, delete_plan, list_plans, update_plan
from .prompts.review_copilot import (
    review_copilot_prompt,
    review_copilot_shared_prompt,
    review_copilot_stage_prompt_previews,
)
from .prompts.search_strategy import build_search_strategy_prompt
from .search import search_papers
from .searxng import (
    SearxngManagerError,
    get_searxng_job,
    get_searxng_status,
    manage_searxng,
    start_searxng_job,
    configure_searxng_proxy,
)
from .usage import can_request, get_usage, record_ai_usage, record_request

_INTELLIGENT_PROGRESS = {}
_INTELLIGENT_PROGRESS_LOCK = threading.RLock()


def _public_ai_profiles(config: dict) -> list[dict]:
    profiles = []
    for item in ai_model_profiles(config):
        public = {key: value for key, value in item.items() if key != "api_key"}
        public["available_capabilities"] = sorted(ai_available_capabilities(item))
        public["api_key_configured"] = bool(item.get("api_key"))
        profiles.append(public)
    return profiles


def _map_document_quote(workspace: dict, quote: str) -> tuple[str, str] | None:
    """Map a native-document quotation to a captured segment without altering words."""
    quote = str(quote or "").strip()
    if not quote:
        return None
    normalized_quote = " ".join(quote.split())
    for segment in workspace.get("segments", []):
        text = str(segment.get("text") or "")
        if quote in text:
            return str(segment.get("id") or ""), quote
        compact = []
        starts = []
        ends = []
        in_space = False
        for index, character in enumerate(text):
            if character.isspace():
                if compact and not in_space:
                    compact.append(" ")
                    starts.append(index)
                    ends.append(index + 1)
                in_space = True
            else:
                compact.append(character)
                starts.append(index)
                ends.append(index + 1)
                in_space = False
        normalized_text = "".join(compact).strip()
        offset = "".join(compact).find(normalized_quote)
        if offset >= 0 and offset + len(normalized_quote) <= len(starts):
            original = text[starts[offset]:ends[offset + len(normalized_quote) - 1]].strip()
            return str(segment.get("id") or ""), original
    return None

_CLAIM_PROPOSAL_CAPABILITY = "claim-proposal-v4"
_EVIDENCE_PROPOSAL_CAPABILITY = "evidence-proposal-v2"
_WIKI_PROPOSAL_CAPABILITY = "wiki-maintainer-v1"
_WIKI_ARTICLE_CAPABILITY = "wiki-article-v1"
_PROJECT_CLAIM_RECOMMENDATION_CAPABILITY = "project-claim-recommendation-v1"


def _claim_proposal_prompt(directory=None) -> str:
    return skill_prompt("claim_proposal", directory)


def _claim_audit_prompt(directory=None) -> str:
    return skill_prompt("claim_audit", directory)


def _evidence_proposal_prompt(directory=None) -> str:
    return skill_prompt("evidence_proposal", directory)


def _evidence_document_proposal_prompt(directory=None) -> str:
    return skill_prompt("evidence_document_proposal", directory)


def _wiki_maintainer_prompt(directory=None) -> str:
    return skill_prompt("wiki_maintainer", directory)


def _wiki_article_prompt(directory=None) -> str:
    return skill_prompt("wiki_article", directory)


def _wiki_article_selection_prompt(directory=None) -> str:
    return skill_prompt("wiki_article_selection", directory)


def _project_claim_recommendation_prompt(directory=None) -> str:
    return skill_prompt("project_claim_recommendation", directory)


def _wiki_claim_context(claim: dict, include_evidence: bool = False) -> dict:
    item = {
        "id": claim["id"],
        "statement": claim.get("statement", ""),
        "basis": claim.get("basis", ""),
        "review_state": claim.get("review_state", "accepted"),
        "lifecycle": claim.get("lifecycle", "active"),
        "tags": [tag.get("name", "") for tag in claim.get("tags", [])],
        "relations": [
            {
                "subject_claim_id": relation.get("subject_claim_id", ""),
                "object_claim_id": relation.get("object_claim_id", ""),
                "relation_type": relation.get("relation_type", ""),
            }
            for relation in claim.get("relations", [])
        ],
    }
    if include_evidence:
        item["evidence"] = [
            {
                "evidence_id": evidence.get("evidence_id", ""),
                "stance": evidence.get("stance", ""),
                "source_title": evidence.get("source_title", ""),
                "locator": evidence.get("locator", ""),
                "quote": str(evidence.get("quote") or "")[:4000],
            }
            for evidence in claim.get("evidence", [])[:12]
        ]
    return item


def _normalize_wiki_article(result: dict, allowed_claim_ids: set[str]) -> dict:
    if not isinstance(result, dict):
        raise AIError("invalid_model_json", "Article response was not an object.")
    title = str(result.get("title") or "").strip()[:300]
    if not title:
        raise AIError("invalid_model_json", "Article response has no title.")
    sections = []
    for raw_section in result.get("sections", [])[:30]:
        if not isinstance(raw_section, dict):
            continue
        heading = str(raw_section.get("heading") or "").strip()[:300]
        paragraphs = []
        for raw_paragraph in raw_section.get("paragraphs", [])[:30]:
            if not isinstance(raw_paragraph, dict):
                continue
            text = str(raw_paragraph.get("text") or "").strip()[:12000]
            claim_ids = list(dict.fromkeys(
                str(item) for item in raw_paragraph.get("claim_ids", [])
                if str(item) in allowed_claim_ids
            ))
            if text and claim_ids:
                paragraphs.append({"text": text, "claim_ids": claim_ids})
        if heading and paragraphs:
            sections.append({"heading": heading, "paragraphs": paragraphs})
    if not sections:
        raise AIError("invalid_model_json", "Article response has no grounded sections.")
    return {
        "title": title,
        "introduction": str(result.get("introduction") or "").strip()[:5000],
        "sections": sections,
        "gaps": [
            str(item).strip()[:1000] for item in result.get("gaps", [])[:20]
            if str(item).strip()
        ],
        "capability_version": _WIKI_ARTICLE_CAPABILITY,
    }


def _copilot_settings(
    config: dict[str, str], context: str = "search"
) -> tuple[str, float, int, dict]:
    instructions = str(config.get("ai_copilot_instructions") or "").strip()
    prompt = review_copilot_prompt(context, instructions)
    try:
        temperature = max(0.0, min(float(config.get("ai_copilot_temperature", "0.2")), 2.0))
    except (TypeError, ValueError):
        temperature = 0.2
    try:
        max_tokens = max(1, min(int(config.get("ai_copilot_max_tokens", "1200")), 32768))
    except (TypeError, ValueError):
        max_tokens = 1200
    try:
        advanced = json.loads(config.get("ai_copilot_advanced_parameters", '{"top_p":0.9}'))
    except (TypeError, json.JSONDecodeError):
        advanced = {"top_p": 0.9}
    if not isinstance(advanced, dict):
        advanced = {"top_p": 0.9}
    reserved = {"model", "messages", "temperature", "max_tokens", "stream", "chat_template_kwargs"}
    advanced = {
        str(key): value for key, value in list(advanced.items())[:20]
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,63}", str(key))
        and str(key) not in reserved
    }
    return prompt, temperature, max_tokens, advanced


def _import_candidates(raw: str) -> list[dict]:
    text = str(raw or "").strip()[:100000]
    if not text:
        return []
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    candidate_text = fenced.group(1).strip() if fenced else text
    entries: list[dict] = []
    try:
        decoded = json.loads(candidate_text)
        if isinstance(decoded, dict):
            decoded = decoded.get("sources", [])
        if isinstance(decoded, list):
            entries = [item for item in decoded if isinstance(item, dict)][:100]
    except json.JSONDecodeError:
        entries = []
    if not entries:
        for line in text.splitlines():
            value = line.strip().lstrip("-*• ").strip()
            match = re.search(
                r"(?:https?://\S+|(?:doi:\s*)?10\.\d{4,9}/\S+|(?:arxiv:\s*)?\d{4}\.\d{4,5}(?:v\d+)?)",
                value,
                re.IGNORECASE,
            )
            if match:
                entries.append({"url": match.group(0).rstrip(".,;)]}")})
    output = []
    seen = set()
    for index, item in enumerate(entries[:100]):
        url = str(item.get("url") or "").strip()
        doi = str(item.get("doi") or "").strip()
        arxiv_id = str(item.get("arxiv_id") or "").strip()
        if url.lower().startswith("doi:"):
            doi, url = url[4:].strip(), ""
        if url.lower().startswith("arxiv:"):
            arxiv_id, url = url[6:].strip(), ""
        if not doi and re.fullmatch(r"10\.\d{4,9}/\S+", url, re.IGNORECASE):
            doi, url = url, ""
        if not arxiv_id and re.fullmatch(r"\d{4}\.\d{4,5}(?:v\d+)?", url, re.IGNORECASE):
            arxiv_id, url = url, ""
        if doi and not url:
            url = f"https://doi.org/{doi}"
        if arxiv_id and not url:
            url = f"https://arxiv.org/abs/{arxiv_id}"
        parsed = urlparse(url)
        if (parsed.hostname or "").lower() in {"arxiv.org", "www.arxiv.org"}:
            match = re.fullmatch(r"/(?:abs|pdf|html)/(\d{4}\.\d{4,5}(?:v\d+)?)(?:\.pdf)?/?", parsed.path, re.I)
            if match:
                arxiv_id = match.group(1)
                url = f"https://arxiv.org/abs/{arxiv_id}"
        if not doi and (parsed.hostname or "").lower() in {"doi.org", "dx.doi.org"}:
            doi = parsed.path.lstrip("/")
        valid_url = parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        locator = (doi or arxiv_id or url).casefold()
        if not locator or locator in seen:
            continue
        seen.add(locator)
        title = str(item.get("title") or "").strip()[:500]
        source_type = str(item.get("source_type") or ("paper" if arxiv_id or doi else "web")).strip().lower()
        why = str(item.get("why_relevant") or "").strip()[:1800]
        authors = item.get("authors") or []
        if isinstance(authors, list):
            authors = ", ".join(str(author).strip() for author in authors if str(author).strip())
        try:
            year = int(item.get("year") or 0)
        except (TypeError, ValueError):
            year = 0
        output.append({
            "id": url or locator,
            "title": title or (arxiv_id and f"arXiv {arxiv_id}") or doi or parsed.netloc or f"Imported Source {index + 1}",
            "authors": str(authors or "Unknown")[:500],
            "year": year if 1000 <= year <= 9999 else 0,
            "abstract": "Imported candidate; inspect the original Source before creating Evidence.",
            "url": url,
            "paper_url": url,
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "",
            "doi_url": f"https://doi.org/{doi}" if doi else "",
            "keywords": [],
            "source": "Third-party import",
            "result_type": "paper" if source_type in {"paper", "report"} else "web",
            "import_status": "partial" if valid_url else "unresolved",
            "import_note": why,
            "match_reason": why,
        })
    return output


def companion_extension_info() -> dict[str, str]:
    try:
        version = package_version("knowte")
    except PackageNotFoundError:
        version = "0.0.0"
    source_candidates = [
        Path(__file__).resolve().parent.parent / "browser-extension",
        Path(sysconfig.get_path("data")) / "knowte" / "browser-extension",
    ]
    source = next((candidate for candidate in source_candidates if candidate.is_dir()), None)
    if source is None:
        raise RuntimeError("The Web Companion assets are missing from this installation.")
    return {"path": str(source.resolve()), "version": version}


def _companion_capture(item: dict, content_dir: Path) -> dict:
    allowed_types = {
        "heading", "paragraph", "list_item", "quote", "code", "table_cell",
        "table_header", "caption",
    }
    blocks = []
    for raw_block in item.get("blocks") or []:
        if not isinstance(raw_block, dict):
            continue
        text = " ".join(str(raw_block.get("text") or "").split())[:100_000]
        if not text:
            continue
        block_type = str(raw_block.get("type") or "paragraph")
        blocks.append({
            "type": block_type if block_type in allowed_types else "paragraph",
            "text": text,
            "metadata": raw_block.get("metadata")
            if isinstance(raw_block.get("metadata"), dict) else {},
        })
        if len(blocks) >= 1000:
            break
    quote = str(item.get("quote") or "").strip()
    if quote and not any(quote in block["text"] for block in blocks):
        blocks.insert(0, {"type": "quote", "text": quote, "metadata": {}})
    if not blocks:
        fallback = quote or str(item.get("source", {}).get("title") or "Captured page")
        blocks = [{"type": "paragraph", "text": fallback, "metadata": {}}]
    raw = json.dumps({"blocks": blocks}, ensure_ascii=False).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    content_dir.mkdir(parents=True, exist_ok=True)
    raw_path = content_dir / f"{digest}.json"
    if not raw_path.exists():
        raw_path.write_bytes(raw)
    return {
        "url": str(item.get("source", {}).get("url") or ""),
        "media_type": "application/x-knowte-blocks+json",
        "sha256": digest,
        "raw_path": str(raw_path),
        "segments": [block["text"] for block in blocks],
        "locators": [
            f"{block['type'].replace('_', ' ').title()} {index}"
            for index, block in enumerate(blocks, start=1)
        ],
        "blocks": blocks,
        "extraction_version": 2,
    }


def _commit_companion_capture(
    item: dict,
    options: dict,
    knowledge_db_path: Path,
    content_dir: Path,
) -> dict:
    source_payload = {
        **item["source"],
        "result_type": "web",
        "source": item["source"].get("source") or "Web Companion",
    }
    artifact_id = str(options.get("artifact_id") or "")
    source, _, _ = save_source(
        source_payload, artifact_id or None, knowledge_db_path
    )
    workspace = store_capture(
        source["id"], _companion_capture(item, content_dir), knowledge_db_path
    )
    created_evidence = None
    if item["kind"] in {"text", "snapshot"}:
        quote = str(item.get("quote") or "")
        segment = next(
            (
                candidate for candidate in workspace["segments"]
                if quote and quote in candidate["text"]
            ),
            workspace["segments"][0],
        )
        start = segment["text"].find(quote) if quote else 0
        created_evidence = create_evidence(
            {
                "evidence_type": item["kind"],
                "segment_id": segment["id"],
                "quote": quote,
                "start_offset": start,
                "end_offset": start + len(quote),
                "image_data": item.get("image_data"),
                "anchor": {
                    **item.get("anchor", {}),
                    "prefix": item.get("prefix", ""),
                    "suffix": item.get("suffix", ""),
                },
                "locator": "Original web",
                "artifact_id": artifact_id,
            },
            knowledge_db_path,
        )
    target_type = "evidence" if created_evidence else "source"
    target_id = created_evidence["id"] if created_evidence else source["id"]
    tags = options.get("tags")
    if isinstance(tags, list) and tags:
        set_entity_tags(target_type, target_id, tags, knowledge_db_path)
    annotation = str(options.get("annotation") or "").strip()
    if annotation:
        create_annotation(
            {"target_type": target_type, "target_id": target_id, "body": annotation},
            knowledge_db_path,
        )
    return {"source": source, "evidence": created_evidence}


def _set_intelligent_progress(
    run_id: str,
    stage: str,
    details: dict | None = None,
) -> None:
    if not run_id:
        return
    with _INTELLIGENT_PROGRESS_LOCK:
        _INTELLIGENT_PROGRESS[run_id] = {
            "stage": stage,
            **(details or {}),
            "updated": time.monotonic(),
        }
        if len(_INTELLIGENT_PROGRESS) > 128:
            oldest = min(
                _INTELLIGENT_PROGRESS,
                key=lambda key: _INTELLIGENT_PROGRESS[key]["updated"],
            )
            _INTELLIGENT_PROGRESS.pop(oldest, None)


class KnowteTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    # Page startup opens several API/static connections at once. The default
    # backlog of five drops bursts before a request handler can even run.
    request_queue_size = 128

    def handle_error(self, request, client_address):
        error = sys.exc_info()[1]
        if isinstance(error, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)):
            return
        if isinstance(error, OSError) and getattr(error, "winerror", None) in {10053, 10054}:
            return
        super().handle_error(request, client_address)


class KnowteHandler(SimpleHTTPRequestHandler):
    library_name = "default"
    config_path = CONFIG_PATH
    plans_path = PLANS_PATH
    knowledge_db_path = KNOWLEDGE_DB_PATH
    content_dir = KNOWLEDGE_DB_PATH.parent / "content"
    allowed_backends = ["arxiv", "openalex", "semanticscholar"]
    default_backends = ["arxiv", "openalex", "semanticscholar"]
    debug_replay_query = ""
    debug_replay_artifact = ""
    companion_store = CompanionStore(CONFIG_PATH.parent)

    def _companion_token(self) -> str:
        authorization = self.headers.get("Authorization", "")
        return authorization[7:].strip() if authorization.startswith("Bearer ") else ""

    def _companion_authorized(self) -> bool:
        return self.companion_store.authenticated(self._companion_token())

    @staticmethod
    def _parse_backends(value: str | None):
        allowed = set(KnowteHandler.allowed_backends)
        parts = [p.strip() for p in (value or "").split(",") if p.strip()]
        parsed = [p for p in parts if p in allowed]
        return parsed or KnowteHandler.default_backends.copy()

    @staticmethod
    def _parse_max_papers(value: str | None):
        try:
            number = int(value or "100")
        except (ValueError, TypeError):
            number = 100
        return max(20, min(number, 1000))

    @staticmethod
    def _parse_bounded_int(value, default, minimum, maximum):
        try:
            number = int(value or default)
        except (ValueError, TypeError):
            number = default
        return max(minimum, min(number, maximum))

    @staticmethod
    def _parse_year(value: str | None):
        if value is None:
            return None
        raw = (value or "").strip()
        if not raw:
            return None
        try:
            year = int(raw)
        except (ValueError, TypeError):
            return None
        if year < 1900 or year > 2100:
            return None
        return year

    @staticmethod
    def _parse_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "yes", "on"}

    def _debug_replay_payload(
        self,
        query: str,
        *,
        intelligent: bool,
    ) -> dict | None:
        configured_query = str(self.debug_replay_query or "").strip().casefold()
        if not configured_query or query.strip().casefold() != configured_query:
            return None
        results = list_replay_sources(
            self.debug_replay_artifact,
            self.knowledge_db_path,
        )
        source_counts = dict(
            Counter(result.get("source") or "Unknown" for result in results)
        )
        verified_count = sum(
            bool(result.get("match_reason"))
            or result.get("verification_score") is not None
            for result in results
        )
        unverified_count = len(results) - verified_count
        replay = {
            "enabled": True,
            "query": self.debug_replay_query,
            "artifact": self.debug_replay_artifact,
            "source_count": len(results),
            "verified_count": verified_count,
            "unverified_count": unverified_count,
            "external_search_requests": 0,
            "ai_requests": 0,
            "filters_applied": False,
        }
        payload = {
            "query": query,
            "results": results,
            "count": len(results),
            "warnings": ["debug_replay"],
            "source_counts": source_counts,
            "usage": get_usage(),
            "debug_replay": replay,
            "enabled_backends": ["debug_replay"],
            "year_from": None,
            "year_to": None,
        }
        if intelligent:
            academic_count = sum(
                result.get("result_type") != "web" for result in results
            )
            web_count = len(results) - academic_count
            payload.update(
                {
                    "stages": {
                        "expand": {
                            "status": "skipped",
                            "requests": 0,
                            "message": "Skipped in Debug Replay.",
                        },
                        "recall": {
                            "status": "complete",
                            "requests": 0,
                            "message": "Loaded the saved baseline from Library.",
                        },
                        "embed": {
                            "status": "skipped",
                            "requests": 0,
                            "message": "Skipped in Debug Replay.",
                        },
                        "verify": {
                            "status": "skipped",
                            "requests": 0,
                            "message": (
                                f"{verified_count} baseline Source(s) retain previous "
                                f"verification; {unverified_count} have no verification "
                                "metadata."
                            ),
                        },
                    },
                    "expanded_queries": [],
                    "candidate_counts": {
                        "academic": academic_count,
                        "web": web_count,
                        "verified": verified_count,
                    },
                    "request_budget": {
                        "retrieval": 0,
                        "academic_retrieval": 0,
                        "web_retrieval": 0,
                        "chat": 0,
                        "embedding": 0,
                    },
                }
            )
        else:
            payload.update(
                {
                    "limit": len(results),
                    "search_diagnostics": {
                        "debug_replay": replay,
                    },
                    "web_pages": 0,
                    "can_find_more": False,
                }
            )
        return payload

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") == "/api/companion/info":
            try:
                self._send_json(companion_extension_info())
            except RuntimeError as error:
                self._send_json(
                    {"error": "companion_missing", "message": str(error)},
                    HTTPStatus.NOT_FOUND,
                )
            return
        if parsed.path.rstrip("/") == "/api/companion/options":
            if not self._companion_authorized():
                self._send_json({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            self._send_json({
                "artifacts": list_artifacts(self.knowledge_db_path),
                "tags": list_tags(self.knowledge_db_path),
                **self.companion_store.preferences(),
                "version": companion_extension_info()["version"],
            })
            return
        if parsed.path.rstrip("/") == "/api/companion/inbox":
            self._send_json({"items": self.companion_store.list()})
            return
        if parsed.path.rstrip("/") == "/api/health":
            payload = {"status": "ok", "service": "knowte"}
            body = json.dumps(payload).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path.rstrip("/") == "/api/skills":
            self._send_json({"skills": skill_catalog(self.config_path.parent / "skills"), "platform": sys.platform})
            return
        if parsed.path.rstrip("/") == "/api/config":
            config = load_config(self.config_path)
            copilot_prompt, copilot_temperature, copilot_max_tokens, copilot_advanced = _copilot_settings(config)
            public_profiles = _public_ai_profiles(config)
            profile_roles = ai_role_assignments(config)
            profile_by_id = {item["id"]: item for item in public_profiles}
            chat_profile = profile_by_id.get(profile_roles.get("intelligent_search", ""), {})
            embedding_profile = profile_by_id.get(profile_roles.get("embedding", ""), {})
            payload = {
                "library_name": self.library_name,
                "email": config.get("email", ""),
                "semanticscholar_api_key": "",
                "semanticscholar_api_key_configured": bool(
                    config.get("semanticscholar_api_key", "")
                ),
                "searxng_url": config.get("searxng_url", ""),
                "searxng_proxy": config.get("searxng_proxy", ""),
                "enabled_backends": self._parse_backends(config.get("enabled_backends")),
                "max_papers": self._parse_max_papers(config.get("max_papers")),
                "intelligent_max_results": self._parse_bounded_int(
                    config.get("intelligent_max_results"), 20, 1, 100
                ),
                "default_search_mode": (
                    config.get("default_search_mode")
                    if config.get("default_search_mode")
                    in {"keyword", "intelligent", "import"}
                    else "keyword"
                ),
                "search_ai_review": self._parse_bool(config.get("search_ai_review", "true" if config.get("default_search_mode") == "intelligent" else "false")),
                "web_ignore_year_filter": self._parse_bool(
                    config.get("web_ignore_year_filter", "true")
                ),
                "ai_model_profiles": public_profiles,
                "ai_role_assignments": profile_roles,
                "ai_provider": config.get("ai_provider", "openai_compatible"),
                "ai_custom_recipe": json.loads(config.get("ai_custom_recipe") or "{}"),
                "ai_base_url": config.get("ai_base_url", ""),
                "ai_api_key": "",
                "ai_api_key_configured": bool(config.get("ai_api_key", "")),
                "ai_chat_model": config.get("ai_chat_model", ""),
                "ai_embedding_model": config.get("ai_embedding_model", ""),
                "ai_embedding_separate_connection": self._parse_bool(
                    config.get("ai_embedding_separate_connection")
                ),
                "ai_enable_thinking": (
                    self._parse_bool(config.get("ai_enable_thinking"))
                    if "ai_enable_thinking" in config
                    else False
                ),
                "ai_embedding_base_url": config.get("ai_embedding_base_url", ""),
                "ai_embedding_api_key": "",
                "ai_embedding_api_key_configured": bool(
                    config.get("ai_embedding_api_key", "")
                ),
                "ai_verify_batch_size": self._parse_bounded_int(
                    config.get("ai_verify_batch_size"), 5, 1, 20
                ),
                "ai_verify_concurrency": self._parse_bounded_int(
                    config.get("ai_verify_concurrency"), 1, 1, 8
                ),
                "ai_timeout_seconds": self._parse_bounded_int(
                    config.get("ai_timeout_seconds"), 45, 5, 600
                ),
                "ai_search_timeout_seconds": self._parse_bounded_int(
                    config.get("ai_search_timeout_seconds")
                    or config.get("ai_timeout_seconds"), 45, 5, 600
                ),
                "ai_evidence_source_limit": self._parse_bounded_int(config.get("ai_evidence_source_limit"), 6, 1, 100),
                "ai_claim_evidence_limit": self._parse_bounded_int(config.get("ai_claim_evidence_limit"), 30, 1, 100),
                "ai_claim_comparison_limit": self._parse_bounded_int(config.get("ai_claim_comparison_limit"), 100, 1, 1000),
                "ai_wiki_claim_limit": self._parse_bounded_int(config.get("ai_wiki_claim_limit"), 100, 1, 1000),
                "ai_copilot_context_limit": self._parse_bounded_int(config.get("ai_copilot_context_limit"), 12, 1, 100),
                "ai_evidence_request_mode": config.get("ai_evidence_request_mode", "combined"),
                "ai_stage_timeout_seconds": self._parse_bounded_int(
                    config.get("ai_stage_timeout_seconds")
                    or config.get("ai_timeout_seconds"), 45, 5, 600
                ),
                "ai_copilot_instructions": config.get("ai_copilot_instructions", ""),
                "ai_copilot_temperature": copilot_temperature,
                "ai_copilot_max_tokens": copilot_max_tokens,
                "ai_copilot_advanced_parameters": copilot_advanced,
                "ai_copilot_prompt_preview": copilot_prompt,
                "ai_copilot_prompt_shared": review_copilot_shared_prompt(),
                "ai_copilot_prompt_previews": {
                    "search_strategy": build_search_strategy_prompt(
                        [], str(config.get("ai_copilot_instructions") or "")
                    ),
                    "evidence_proposal": _evidence_proposal_prompt(),
                    "claim_proposal": _claim_proposal_prompt(),
                    "wiki_maintenance": _wiki_maintainer_prompt(),
                    "project_claim_recommendation": _project_claim_recommendation_prompt(),
                    "article_selection": _wiki_article_selection_prompt(),
                    "article_writing": _wiki_article_prompt(),
                    **review_copilot_stage_prompt_previews(),
                },
                "ai_configured": bool(chat_profile.get("base_url") and chat_profile.get("model")),
                "ai_chat_configured": bool(chat_profile.get("base_url") and chat_profile.get("model")),
                "ai_embedding_configured": bool(
                    embedding_profile.get("base_url") and embedding_profile.get("model")
                ),
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path.rstrip("/") == "/api/intelligent-progress":
            run_id = parse_qs(parsed.query).get("run_id", [""])[0][:100]
            with _INTELLIGENT_PROGRESS_LOCK:
                state = dict(_INTELLIGENT_PROGRESS.get(run_id, {}))
            self._send_json(state)
            return
        if parsed.path.rstrip("/") == "/api/intelligent-search":
            params = parse_qs(parsed.query)
            run_id = params.get("run_id", [""])[0][:100]
            query = params.get("q", [""])[0].strip()
            if not query:
                self._send_json(
                    {"error": "empty_query", "message": "Query is required."},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            replay_payload = self._debug_replay_payload(
                query,
                intelligent=True,
            )
            if replay_payload is not None:
                self._send_json(replay_payload)
                return
            config = load_config(self.config_path)
            requested_backends = params.get("backends", [""])[0]
            backends = (
                self._parse_backends(requested_backends)
                if requested_backends.strip()
                else self._parse_backends(config.get("enabled_backends"))
            )
            warnings = []
            if "websearch" in backends and not (config.get("searxng_url") or "").strip():
                backends = [source for source in backends if source != "websearch"]
                warnings.append("websearch_unconfigured")
            if not backends:
                self._send_json(
                    {"error": "no_search_backends", "warnings": warnings},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            usage = can_request(backends=backends)
            academic_enabled = any(
                source in backends
                for source in ("arxiv", "openalex", "semanticscholar")
            )
            web_enabled = "websearch" in backends
            if (academic_enabled and not usage.get("allowed_paper", usage["allowed"])) or (
                web_enabled and not usage.get("allowed_web", True)
            ):
                self._send_json(
                    {
                        "error": "intelligent_rate_limited",
                        "usage": usage,
                        "warnings": warnings,
                    },
                    HTTPStatus.TOO_MANY_REQUESTS,
                )
                return
            areas = [
                value.strip()
                for value in params.get("areas", [""])[0].split(",")
                if value.strip()
            ]
            year_from = self._parse_year(params.get("year_from", [""])[0])
            year_to = self._parse_year(params.get("year_to", [""])[0])
            if year_from is not None and year_to is not None and year_from > year_to:
                year_from, year_to = year_to, year_from
            try:
                limit = self._parse_bounded_int(
                    params.get("limit", ["20"])[0], 20, 1, 100
                )
                raw_strategy = params.get("strategy", [""])[0]
                search_actions = json.loads(raw_strategy) if raw_strategy else []
                if not isinstance(search_actions, list):
                    search_actions = []
                web_pages = max(
                    1,
                    min(int(params.get("web_pages", ["1"])[0] or "1"), 10),
                )
                payload = intelligent_search(
                    query,
                    config,
                    limit,
                    backends,
                    areas,
                    year_from,
                    year_to,
                    web_pages,
                    progress=lambda stage, details: _set_intelligent_progress(
                        run_id, stage, details
                    ),
                    search_actions=search_actions,
                    profile_id=params.get("model_profile_id", [""])[0][:80],
                    skills_dir=self.config_path.parent / "skills",
                )
                payload["warnings"] = [*warnings, *payload.get("warnings", [])]
                payload["enabled_backends"] = backends
                payload["year_from"] = year_from
                payload["year_to"] = year_to
                budget = payload.get("request_budget", {})
                ai_usage = payload.pop("_ai_usage", {})
                latest_usage = get_usage()
                for _ in range(int(budget.get("academic_retrieval", 0))):
                    latest_usage = record_request(backends=["arxiv"])
                for _ in range(int(budget.get("web_retrieval", 0))):
                    latest_usage = record_request(backends=["websearch"])
                if ai_usage:
                    latest_usage = record_ai_usage(
                        chat_requests=ai_usage.get("chat_requests", 0),
                        chat_tokens=ai_usage.get("chat_tokens", 0),
                        embedding_requests=ai_usage.get("embedding_requests", 0),
                        embedding_tokens=ai_usage.get("embedding_tokens", 0),
                    )
                payload["usage"] = latest_usage
                self._send_json(payload, HTTPStatus.OK)
            except AIError as error:
                self._send_json(
                    {
                        "error": error.code,
                        "message": str(error),
                        "warnings": warnings,
                        "usage": get_usage(),
                    },
                    (
                        HTTPStatus.BAD_REQUEST
                        if error.code in {
                            "ai_unconfigured",
                            "invalid_base_url",
                            "chat_model_missing",
                            "embedding_model_missing",
                        }
                        else HTTPStatus.BAD_GATEWAY
                    ),
                )
            except (TypeError, ValueError):
                self._send_json(
                    {"error": "invalid_request", "message": "Invalid search parameters."},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if parsed.path.rstrip("/") == "/api/plans":
            body = json.dumps({"plans": list_plans(self.plans_path)}).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path.rstrip("/") == "/api/artifacts":
            self._send_json(
                {"artifacts": list_artifacts(self.knowledge_db_path)}
            )
            return
        project_match = re.fullmatch(
            r"/api/projects/([0-9a-f]+)", parsed.path.rstrip("/")
        )
        if project_match:
            try:
                self._send_json(get_project(
                    project_match.group(1), self.knowledge_db_path,
                ))
            except ValueError as error:
                self._send_json(
                    {"error": "project_not_found", "message": str(error)},
                    HTTPStatus.NOT_FOUND,
                )
            return
        if parsed.path.rstrip("/") == "/api/project-claim-recommendations":
            query = parse_qs(parsed.query)
            self._send_json({
                "proposals": list_project_claim_recommendations(
                    str(query.get("project_id", [""])[0]), self.knowledge_db_path
                )
            })
            return
        if parsed.path.rstrip("/") == "/api/tags":
            self._send_json({"tags": list_tags(self.knowledge_db_path)})
            return
        if parsed.path.rstrip("/") == "/api/library/sources":
            self._send_json(
                {"sources": list_sources(self.knowledge_db_path)}
            )
            return
        if parsed.path.rstrip("/") == "/api/evidence":
            self._send_json({"evidence": list_evidence(self.knowledge_db_path)})
            return
        if parsed.path.rstrip("/") == "/api/claims":
            self._send_json({"claims": list_claims(self.knowledge_db_path)})
            return
        if parsed.path.rstrip("/") == "/api/claim-proposals":
            self._send_json(
                {"proposals": list_claim_proposals(self.knowledge_db_path)}
            )
            return
        if parsed.path.rstrip("/") == "/api/claim-audits":
            self._send_json({"audits": list_claim_audits(self.knowledge_db_path)})
            return
        if parsed.path.rstrip("/") == "/api/evidence-proposals":
            self._send_json(
                {"proposals": list_evidence_proposals(self.knowledge_db_path)}
            )
            return
        if parsed.path.rstrip("/") == "/api/views":
            self._send_json({"views": list_views(self.knowledge_db_path)})
            return
        if parsed.path.rstrip("/") == "/api/wiki":
            self._send_json(get_wiki(self.knowledge_db_path))
            return
        if parsed.path.rstrip("/") == "/api/wiki/proposals":
            self._send_json(
                {"proposals": list_wiki_proposals(self.knowledge_db_path)}
            )
            return
        if parsed.path.rstrip("/") == "/api/wiki/imports":
            self._send_json({"imports": list_wiki_imports(self.knowledge_db_path)})
            return
        if parsed.path.rstrip("/") == "/api/project-documents":
            query = parse_qs(parsed.query)
            self._send_json({
                "documents": list_project_documents(
                    str(query.get("artifact_id", [""])[0]), self.knowledge_db_path
                )
            })
            return
        view_match = re.fullmatch(r"/api/views/([0-9a-f]+)", parsed.path.rstrip("/"))
        if view_match:
            try:
                self._send_json(get_view(view_match.group(1), self.knowledge_db_path))
            except ValueError as error:
                self._send_json(
                    {"error": "view_not_found", "message": str(error)},
                    HTTPStatus.NOT_FOUND,
                )
            return
        workspace_match = re.fullmatch(
            r"/api/library/sources/([0-9a-f]+)/workspace",
            parsed.path.rstrip("/"),
        )
        if workspace_match:
            try:
                self._send_json(
                    get_source_workspace(
                        workspace_match.group(1), self.knowledge_db_path
                    )
                )
            except ValueError as error:
                self._send_json(
                    {"error": "source_not_found", "message": str(error)},
                    HTTPStatus.NOT_FOUND,
                )
            return
        content_match = re.fullmatch(
            r"/api/library/sources/([0-9a-f]+)/content",
            parsed.path.rstrip("/"),
        )
        if content_match:
            try:
                file_path, media_type, digest = get_capture_file(
                    content_match.group(1),
                    self.content_dir,
                    self.knowledge_db_path,
                )
                self._send_local_file(
                    file_path,
                    media_type,
                    etag=digest,
                    disposition="inline",
                )
            except ValueError as error:
                self._send_json(
                    {"error": "content_not_found", "message": str(error)},
                    HTTPStatus.NOT_FOUND,
                )
            return
        snapshot_match = re.fullmatch(
            r"/api/evidence/([0-9a-f]+)/snapshot",
            parsed.path.rstrip("/"),
        )
        if snapshot_match:
            try:
                file_path = get_snapshot_file(
                    snapshot_match.group(1),
                    self.content_dir,
                    self.knowledge_db_path,
                )
                self._send_local_file(
                    file_path,
                    "image/png",
                    disposition="inline",
                )
            except ValueError as error:
                self._send_json(
                    {"error": "snapshot_not_found", "message": str(error)},
                    HTTPStatus.NOT_FOUND,
                )
            return
        if parsed.path.rstrip("/") == "/api/usage":
            payload = get_usage()
            body = json.dumps(payload).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path.rstrip("/") == "/api/searxng":
            payload = get_searxng_status()
            body = json.dumps(payload).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path.rstrip("/") == "/api/searxng/job":
            job_id = parse_qs(parsed.query).get("id", [""])[0]
            try:
                payload = get_searxng_job(job_id)
                status_code = HTTPStatus.OK
            except SearxngManagerError as error:
                payload = {
                    "error": error.code,
                    "message": str(error),
                }
                status_code = HTTPStatus.NOT_FOUND
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path.rstrip("/") == "/api/search":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            areas = params.get("areas", [""])[0]
            requested_limit = params.get("limit", [""])[0]
            requested_web_pages = params.get("web_pages", ["1"])[0]
            year_from = self._parse_year(params.get("year_from", [""])[0])
            year_to = self._parse_year(params.get("year_to", [""])[0])
            if year_from is not None and year_to is not None and year_from > year_to:
                year_from, year_to = year_to, year_from
            area_list = [a.strip() for a in areas.split(",") if a.strip()]
            if not query.strip():
                payload = {
                    "query": query,
                    "count": 0,
                    "results": [],
                    "usage": get_usage(),
                    "error": "empty_query",
                    "warnings": [],
                }
                body = json.dumps(payload).encode("utf-8")
                self.send_response(HTTPStatus.BAD_REQUEST)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            replay_payload = self._debug_replay_payload(
                query,
                intelligent=False,
            )
            if replay_payload is not None:
                self._send_json(replay_payload)
                return
            config = load_config(self.config_path)
            requested_backends = params.get("backends", [""])[0]
            backends = (
                self._parse_backends(requested_backends)
                if requested_backends.strip()
                else self._parse_backends(config.get("enabled_backends"))
            )
            warnings = []
            if "websearch" in backends and not (config.get("searxng_url") or "").strip():
                backends = [b for b in backends if b != "websearch"]
                warnings.append("websearch_unconfigured")
            if not backends:
                payload = {
                    "query": query,
                    "count": 0,
                    "results": [],
                    "usage": get_usage(),
                    "error": "no_search_backends",
                    "warnings": warnings,
                }
                body = json.dumps(payload).encode("utf-8")
                self.send_response(HTTPStatus.BAD_REQUEST)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            usage = can_request(backends=backends)
            effective_backends = backends.copy()

            max_papers = self._parse_max_papers(config.get("max_papers"))
            try:
                limit = int(requested_limit or str(max_papers))
            except ValueError:
                limit = max_papers
            limit = max(20, min(limit, 1000))
            try:
                web_pages = int(requested_web_pages or "1")
            except ValueError:
                web_pages = 1
            web_pages = max(1, min(web_pages, 10))
            search_diagnostics = {}
            results = search_papers(
                query,
                limit=limit,
                email=config.get("email"),
                areas=area_list,
                semanticscholar_key=config.get("semanticscholar_api_key"),
                backends=effective_backends,
                year_from=year_from,
                year_to=year_to,
                searxng_url=config.get("searxng_url"),
                web_ignore_year_filter=self._parse_bool(
                    config.get("web_ignore_year_filter", "true")
                ),
                web_pages=web_pages,
                allow_paper_external=bool(usage.get("allowed_paper", usage["allowed"])),
                allow_web_external=bool(usage.get("allowed_web", True)),
                diagnostics=search_diagnostics,
            )
            academic_diagnostics = search_diagnostics.get("academic")
            web_diagnostics = search_diagnostics.get("websearch", {})
            academic_enabled = any(
                backend in effective_backends
                for backend in ("arxiv", "openalex", "semanticscholar")
            )
            paper_external = (
                bool(academic_diagnostics.get("external_request"))
                if isinstance(academic_diagnostics, dict)
                else academic_enabled
            )
            web_external = (
                int(web_diagnostics.get("external_requests", 0)) > 0
                if isinstance(web_diagnostics, dict)
                and "external_requests" in web_diagnostics
                else "websearch" in effective_backends
            )
            recorded_backends = []
            if paper_external:
                recorded_backends.append("arxiv")
            if web_external:
                recorded_backends.append("websearch")
            usage = (
                record_request(backends=recorded_backends)
                if recorded_backends
                else get_usage()
            )
            source_counts = dict(Counter(result.get("source") or "Unknown" for result in results))
            allocation = search_diagnostics.get("allocation", {})
            available = allocation.get("available", {})
            selected_counts = allocation.get("selected", {})
            academic_has_cached_more = any(
                available.get(source, 0) > selected_counts.get(source, 0)
                for source in ("arxiv", "openalex", "semanticscholar")
                if source in effective_backends
            )
            can_find_more = (
                limit < 1000 and academic_enabled and academic_has_cached_more
            ) or (
                "websearch" in effective_backends
                and web_pages < 10
                and bool(web_diagnostics.get("has_more"))
            )
            if isinstance(academic_diagnostics, dict) and academic_diagnostics.get(
                "rate_limited"
            ):
                warnings.append("paper_rate_limited")
            if web_diagnostics.get("rate_limited"):
                warnings.append("websearch_rate_limited")
            if web_diagnostics.get("error") == "unavailable":
                warnings.append("websearch_unavailable")
            elif web_diagnostics.get("error") == "invalid_response":
                warnings.append("websearch_invalid_response")
            elif (
                web_diagnostics.get("empty_response")
                and web_diagnostics.get("fetched", 0) == 0
            ):
                warnings.append("websearch_empty_response")
            elif (
                "websearch" in effective_backends
                and web_diagnostics.get("fetched", 0) > 0
                and web_diagnostics.get("accepted", 0) == 0
            ):
                warnings.append("websearch_no_matching_results")
            if (
                "websearch" in effective_backends
                and (year_from is not None or year_to is not None)
                and not self._parse_bool(config.get("web_ignore_year_filter", "true"))
            ):
                warnings.append("websearch_strict_year_filter")
            paper_blocked = (
                academic_enabled
                and isinstance(academic_diagnostics, dict)
                and bool(academic_diagnostics.get("rate_limited"))
            )
            web_blocked = (
                "websearch" in effective_backends
                and bool(web_diagnostics.get("rate_limited"))
            )
            if not results and (
                (paper_blocked and "websearch" not in effective_backends)
                or (web_blocked and not academic_enabled)
                or (paper_blocked and web_blocked)
            ):
                error = (
                    "web_rate_limited"
                    if web_blocked and not academic_enabled
                    else "paper_rate_limited"
                )
                payload = {
                    "query": query,
                    "count": 0,
                    "results": [],
                    "usage": usage,
                    "error": error,
                    "warnings": warnings,
                }
                body = json.dumps(payload).encode("utf-8")
                self.send_response(HTTPStatus.TOO_MANY_REQUESTS)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            payload = {
                "query": query,
                "count": len(results),
                "results": results,
                "usage": usage,
                "limit": limit,
                "enabled_backends": effective_backends,
                "warnings": warnings,
                "year_from": year_from,
                "year_to": year_to,
                "source_counts": source_counts,
                "search_diagnostics": search_diagnostics,
                "web_pages": web_pages,
                "can_find_more": can_find_more,
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/")
        companion_confirm_match = re.fullmatch(
            r"/api/companion/inbox/([0-9a-f]+)/confirm", route
        )
        capture_match = re.fullmatch(
            r"/api/library/sources/([0-9a-f]+)/capture", route
        )
        proposal_accept_match = re.fullmatch(
            r"/api/claim-proposals/([0-9a-f]+)/accept", route
        )
        project_claim_recommendation_accept_match = re.fullmatch(
            r"/api/project-claim-recommendations/([0-9a-f]+)/accept", route
        )
        project_wiki_proposal_accept_match = re.fullmatch(
            r"/api/project-wiki-proposals/([0-9a-f]+)/accept", route
        )
        evidence_proposal_accept_match = re.fullmatch(
            r"/api/evidence-proposals/([0-9a-f]+)/accept", route
        )
        wiki_proposal_accept_match = re.fullmatch(
            r"/api/wiki/proposals/([0-9a-f]+)/accept", route
        )
        wiki_proposal_update_match = re.fullmatch(
            r"/api/wiki/proposals/([0-9a-f]+)", route
        )
        project_import_accept_match = re.fullmatch(
            r"/api/projects/([0-9a-f]+)/import/accept", route
        )
        wiki_import_accept_match = re.fullmatch(
            r"/api/wiki/imports/([0-9a-f]+)/accept", route
        )
        project_claims_match = re.fullmatch(
            r"/api/projects/([0-9a-f]+)/claims", route
        )
        claim_audit_action_match = re.fullmatch(
            r"/api/claim-audits/([0-9a-f]+)/(run|pause|resume|cancel)", route
        )
        if route not in {
            "/api/skills",
            "/api/config",
            "/api/config/default-search-mode",
            "/api/searxng",
            "/api/plans",
            "/api/artifacts",
            "/api/library/sources",
            "/api/library/sources/batch",
            "/api/review/chat",
            "/api/search/strategy",
            "/api/search/import",
            "/api/source-discovery",
            "/api/evidence",
            "/api/claims",
            "/api/claim-relations",
            "/api/claim-proposals/generate",
            "/api/claim-audits",
            "/api/claim-audits/preview",
            "/api/evidence-proposals/generate",
            "/api/evidence-pages/select",
            "/api/library/documents",
            "/api/wiki/proposals/generate",
            "/api/wiki/proposals/edit",
            "/api/wiki/reset",
            "/api/wiki/articles/generate",
            "/api/project-articles/generate",
            "/api/project-documents",
            "/api/exports",
            "/api/config/export",
            "/api/project-imports",
            "/api/wiki/imports",
            "/api/tags/entity",
            "/api/tags/batch",
            "/api/knowledge/delete-preview",
            "/api/knowledge/delete",
            "/api/annotations",
            "/api/companion/pairing",
            "/api/companion/pair",
            "/api/companion/captures",
            "/api/companion/commit",
            "/api/companion/theme",
            "/api/project-claim-recommendations/generate",
            "/api/project-wiki-proposals/generate",
        } and not capture_match and not companion_confirm_match and not proposal_accept_match and not evidence_proposal_accept_match and not wiki_proposal_accept_match and not wiki_proposal_update_match and not project_claim_recommendation_accept_match and not project_wiki_proposal_accept_match and not project_import_accept_match and not wiki_import_accept_match and not project_claims_match and not claim_audit_action_match:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if route == "/api/library/documents" and length > 28 * 1024 * 1024:
            self.close_connection = True
            self._send_json({"message": "Document exceeds the 20 MB limit"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        body = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            payload = {}
        if route == "/api/library/documents":
            try:
                result = import_document(
                    base64.b64decode(str(payload.get("data") or ""), validate=True),
                    str(payload.get("filename") or ""), str(payload.get("title") or ""),
                    self.knowledge_db_path, self.content_dir,
                )
                self._send_json(result, HTTPStatus.CREATED)
            except (ValueError, OSError) as error:
                self._send_json({"message": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        if route == "/api/exports":
            try:
                filename, export_body = build_knowledge_export(
                    str(payload.get("type") or ""),
                    payload.get("ids") if isinstance(payload.get("ids"), list) else [],
                    self.knowledge_db_path,
                    self.content_dir,
                )
                self._send_bytes(
                    export_body,
                    "application/zip",
                    filename,
                )
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_export", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route == "/api/config/export":
            self._send_bytes(
                export_config(
                    self.config_path,
                    bool(payload.get("redact_secrets", True)),
                ),
                "application/x-yaml",
                "knowte-config.yml",
            )
            return
        if route in {"/api/project-imports", "/api/wiki/imports"}:
            try:
                self._send_json(
                    (stage_project_package_import if route == "/api/project-imports"
                     else stage_wiki_package_import)(
                        str(payload.get("data") or ""),
                        str(payload.get("filename") or "knowte-import.zip"),
                        self.knowledge_db_path,
                        self.content_dir,
                    ),
                    HTTPStatus.CREATED,
                )
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_import", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if project_import_accept_match:
            try:
                self._send_json(accept_project_import(
                    project_import_accept_match.group(1),
                    self.knowledge_db_path,
                    self.content_dir,
                ))
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_import", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if wiki_import_accept_match:
            try:
                self._send_json(accept_wiki_import(
                    wiki_import_accept_match.group(1),
                    self.knowledge_db_path,
                    self.content_dir,
                ))
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_import", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if project_claims_match:
            claim_ids = payload.get("claim_ids")
            if not isinstance(claim_ids, list) or not claim_ids:
                self._send_json(
                    {"error": "invalid_project_claims", "message": "Select at least one Claim"},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                for claim_id in dict.fromkeys(str(item) for item in claim_ids if item):
                    link_project_knowledge(
                        project_claims_match.group(1), "claim", claim_id,
                        self.knowledge_db_path,
                    )
                self._send_json({"linked": len(set(claim_ids))})
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_project_claims", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if project_claim_recommendation_accept_match:
            try:
                self._send_json(accept_project_claim_recommendation(
                    project_claim_recommendation_accept_match.group(1),
                    self.knowledge_db_path,
                ))
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_project_recommendation", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if project_wiki_proposal_accept_match:
            try:
                self._send_json(accept_project_wiki_proposal(
                    project_wiki_proposal_accept_match.group(1), self.knowledge_db_path,
                ))
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_project_wiki", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route == "/api/skills":
            # Local file operations are restricted to this browser's local origin.
            origin = self.headers.get("Origin")
            if self.client_address[0] not in {"127.0.0.1", "::1"} or (
                origin and urlparse(origin).netloc != self.headers.get("Host")
            ):
                self._send_json({"message": "Skill file actions require local access."}, HTTPStatus.FORBIDDEN)
                return
            try:
                entry = manage_skill(
                    payload.get("stage"), payload.get("action"),
                    self.config_path.parent / "skills",
                )
                self._send_json({"skill": entry})
            except (AIError, OSError) as error:
                self._send_json({"error": "invalid_skill", "message": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        if route == "/api/project-wiki-proposals/generate":
            project_id = str(payload.get("project_id") or "").strip()
            try:
                project = get_project(project_id, self.knowledge_db_path)
                project_claims = [
                    claim for claim in project.get("claims", [])
                    if claim.get("lifecycle") == "active"
                ]
                if not project_claims:
                    raise ValueError("Add at least one active Claim before organizing the Project Wiki")
                config = load_config(self.config_path)
                profile_id = str(payload.get("model_profile_id") or "")[:80]
                client = _client_from_config(
                    config, skills_dir=self.config_path.parent / "skills", require_embedding=False, role="wiki", profile_id=profile_id,
                )
                _, temperature, max_tokens, advanced = _copilot_settings(config, "artifact")
                current_pages = (project.get("wiki") or {}).get("graph_state", {}).get("pages", [])
                result = client.chat_json(
                    skill_prompt("project_wiki", self.config_path.parent / "skills"),
                    json.dumps({
                        "instruction": "Organize only this Project's Claims into a compact Project Wiki.",
                        "project": {"title": project["title"], "purpose": project["purpose"]},
                        "current_wiki": current_pages,
                        "claims": [_wiki_claim_context(claim) for claim in project_claims],
                    }, ensure_ascii=False),
                    temperature=min(temperature, 0.3),
                    max_tokens=max(3000, max_tokens), extra_parameters=advanced,
                )
                proposal = create_wiki_proposal(
                    result, _WIKI_PROPOSAL_CAPABILITY,
                    _model_name_from_config(config, "wiki", profile_id),
                    {"project_id": project_id, "claim_ids": [claim["id"] for claim in project_claims]},
                    self.knowledge_db_path, proposal_type="project_wiki_patch",
                )
                snapshot = client.usage_snapshot()
                usage = record_ai_usage(
                    chat_requests=snapshot.get("chat_requests", 0),
                    chat_tokens=snapshot.get("chat_tokens", 0),
                )
                self._send_json({"proposal": proposal, "usage": usage}, HTTPStatus.CREATED)
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_project_wiki", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            except AIError as error:
                self._send_json(
                    {"error": error.code, "message": str(error), "usage": get_usage()},
                    HTTPStatus.BAD_REQUEST if error.code in {"ai_unconfigured", "chat_model_missing"}
                    else HTTPStatus.SERVICE_UNAVAILABLE,
                )
            return
        if route == "/api/project-claim-recommendations/generate":
            project_id = str(payload.get("project_id") or "").strip()
            candidate_ids = payload.get("candidate_ids")
            if not project_id or not isinstance(candidate_ids, list):
                self._send_json(
                    {"error": "invalid_project_scope", "message": "Choose a Project and Claim scope."},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                project = get_project(project_id, self.knowledge_db_path)
                allowed_ids = set(dict.fromkeys(str(item) for item in candidate_ids[:200] if item))
                linked_ids = {item["id"] for item in project.get("claims", [])}
                candidates = [
                    _wiki_claim_context(claim, include_evidence=True)
                    for claim in list_claims(self.knowledge_db_path)
                    if claim["id"] in allowed_ids
                    and claim.get("lifecycle") == "active"
                    and claim["id"] not in linked_ids
                ]
                if not candidates:
                    raise ValueError("The selected scope contains no available Claims")
                config = load_config(self.config_path)
                profile_id = str(payload.get("model_profile_id") or "")[:80]
                client = _client_from_config(
                    config, skills_dir=self.config_path.parent / "skills", require_embedding=False, role="article", profile_id=profile_id,
                )
                _, temperature, max_tokens, advanced = _copilot_settings(config, "artifact")
                result = client.chat_json(
                    _project_claim_recommendation_prompt(self.config_path.parent / "skills"),
                    json.dumps({
                        "project": {"title": project["title"], "purpose": project["purpose"]},
                        "candidate_claims": candidates,
                    }, ensure_ascii=False),
                    temperature=min(temperature, 0.3),
                    max_tokens=max(1800, max_tokens),
                    extra_parameters=advanced,
                )
                recommendations = (
                    result.get("recommendations", []) if isinstance(result, dict) else []
                )
                valid = [
                    item for item in recommendations if isinstance(item, dict)
                    and str(item.get("claim_id") or "") in {claim["id"] for claim in candidates}
                ]
                proposals = create_project_claim_recommendations(
                    project_id, valid, _PROJECT_CLAIM_RECOMMENDATION_CAPABILITY,
                    _model_name_from_config(config, "article", profile_id),
                    {"candidate_ids": [claim["id"] for claim in candidates]},
                    self.knowledge_db_path,
                )
                snapshot = client.usage_snapshot()
                usage = record_ai_usage(
                    chat_requests=snapshot.get("chat_requests", 0),
                    chat_tokens=snapshot.get("chat_tokens", 0),
                )
                self._send_json({"proposals": proposals, "usage": usage}, HTTPStatus.CREATED)
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_project_scope", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            except AIError as error:
                self._send_json(
                    {"error": error.code, "message": str(error), "usage": get_usage()},
                    HTTPStatus.BAD_REQUEST if error.code in {"ai_unconfigured", "chat_model_missing"}
                    else HTTPStatus.SERVICE_UNAVAILABLE,
                )
            return
        if claim_audit_action_match:
            audit_id, action = claim_audit_action_match.groups()
            try:
                if action != "run":
                    status = {
                        "pause": "paused", "resume": "running", "cancel": "cancelled",
                    }[action]
                    self._send_json(update_claim_audit_status(
                        audit_id, status, self.knowledge_db_path,
                    ))
                    return
                audit, batch = next_claim_audit_batch(
                    audit_id, 8, self.knowledge_db_path,
                )
                if not batch:
                    if audit["status"] in {"ready", "running"}:
                        audit = complete_claim_audit_batch(
                            audit_id, [], 0, path=self.knowledge_db_path,
                        )
                    self._send_json({"audit": audit, "proposals": []})
                    return
                if audit["status"] == "ready":
                    audit = update_claim_audit_status(
                        audit_id, "running", self.knowledge_db_path,
                    )
                config = load_config(self.config_path)
                profile_id = audit.get("model_profile_id", "")
                client = _client_from_config(
                    config, skills_dir=self.config_path.parent / "skills", require_embedding=False, role="claims",
                    profile_id=profile_id,
                )
                pairs_payload = []
                pair_keys = []
                for item in batch:
                    left, right = item["left"], item["right"]
                    pair_keys.append({
                        "left_claim_id": left["id"], "right_claim_id": right["id"],
                    })
                    pairs_payload.append({
                        "existing_relations": [relation for relation in left.get("relations", [])
                                               if {relation["subject_claim_id"], relation["object_claim_id"]} == {left["id"], right["id"]}],
                        "left": {
                            "claim_id": left["id"], "statement": left["statement"],
                            "basis": left["basis"], "review_state": left["review_state"],
                            "tags": [tag["name"] for tag in left.get("tags", [])],
                            "grounding": [{
                                "evidence_id": evidence["evidence_id"],
                                "stance": evidence["stance"],
                                "source_title": evidence["source_title"],
                                "quote": evidence["quote"][:1200],
                            } for evidence in left.get("evidence", [])[:8]],
                        },
                        "right": {
                            "claim_id": right["id"], "statement": right["statement"],
                            "basis": right["basis"], "review_state": right["review_state"],
                            "tags": [tag["name"] for tag in right.get("tags", [])],
                            "grounding": [{
                                "evidence_id": evidence["evidence_id"],
                                "stance": evidence["stance"],
                                "source_title": evidence["source_title"],
                                "quote": evidence["quote"][:1200],
                            } for evidence in right.get("evidence", [])[:8]],
                        },
                    })
                result = client.chat_json(
                    _claim_audit_prompt(self.config_path.parent / "skills"),
                    json.dumps({"pairs": pairs_payload}, ensure_ascii=False),
                    temperature=0.05, max_tokens=3200,
                    allow_text_fallback=True,
                )
                if isinstance(result, dict) and result.get("_structured_output_degraded"):
                    raw = str(result.get("answer") or "")
                    audit = complete_claim_audit_batch(
                        audit_id, [], 0, raw_response=raw,
                        error="The model response could not be parsed as JSON. Nothing was saved.",
                        path=self.knowledge_db_path,
                    )
                    self._send_json({"audit": audit, "proposals": []}, HTTPStatus.BAD_GATEWAY)
                    return
                if not isinstance(result, dict) or not isinstance(result.get("assessments"), list):
                    raise AIError(
                        "invalid_claim_audit",
                        "The model did not return a complete Claim audit batch. Nothing was saved.",
                    )
                allowed_pairs = {
                    tuple(sorted((item["left_claim_id"], item["right_claim_id"])))
                    for item in pair_keys
                }
                claims_by_id = {
                    claim["id"]: claim for item in batch
                    for claim in (item["left"], item["right"])
                }
                proposal_payloads = []
                assessed_pairs = set()
                for assessment in (result.get("assessments") or [])[:len(batch)]:
                    if not isinstance(assessment, dict):
                        continue
                    left_id = str(assessment.get("left_claim_id") or "")
                    right_id = str(assessment.get("right_claim_id") or "")
                    if tuple(sorted((left_id, right_id))) not in allowed_pairs:
                        continue
                    assessed_pairs.add(tuple(sorted((left_id, right_id))))
                    judgment = str(assessment.get("judgment") or "").lower()
                    rationale = str(assessment.get("rationale") or "")[:2000]
                    caveats = assessment.get("caveats") or []
                    proposal_payload = None
                    if judgment in {"same", "revises"}:
                        target_id = str(assessment.get("target_claim_id") or "")
                        source_id = str(assessment.get("source_claim_id") or "")
                        if {target_id, source_id} == {left_id, right_id}:
                            proposal_payload = {
                                "operation": "merge_claims",
                                "target_claim_id": target_id,
                                "target_statement": claims_by_id[target_id]["statement"],
                                "source_claim_id": source_id,
                                "source_statement": claims_by_id[source_id]["statement"],
                                "merged_statement": str(assessment.get("merged_statement") or "")[:4000],
                                "audit_judgment": judgment,
                                "rationale": rationale, "caveats": caveats,
                            }
                    elif judgment in {"supports", "related", "contradicts", "scope_difference"}:
                        if judgment == "supports" and not (assessment.get("subject_claim_id") and assessment.get("object_claim_id")):
                            raise AIError("invalid_claim_audit", "Support relations require an explicit direction.")
                        subject_id = str(assessment.get("subject_claim_id") or left_id)
                        object_id = str(assessment.get("object_claim_id") or right_id)
                        if {subject_id, object_id} != {left_id, right_id}:
                            raise AIError("invalid_claim_audit", "Invalid relation endpoints. Nothing from this batch was saved.")
                        proposal_payload = {
                            "operation": "create_relation",
                            "subject_claim_id": subject_id,
                            "subject_statement": claims_by_id[subject_id]["statement"],
                            "object_claim_id": object_id,
                            "object_statement": claims_by_id[object_id]["statement"],
                            "relation_type": "related" if judgment == "scope_difference" else judgment,
                            "audit_judgment": judgment,
                            "rationale": rationale, "caveats": caveats,
                        }
                    existing_relations = [relation for relation in claims_by_id[left_id].get("relations", [])
                                          if {relation["subject_claim_id"], relation["object_claim_id"]} == {left_id, right_id}]
                    relation_keys = ("subject_claim_id", "object_claim_id", "relation_type")
                    reviewed_keys = [tuple(review.get(key) for key in relation_keys) for review in assessment.get("relation_reviews") or []]
                    if len(reviewed_keys) != len(set(reviewed_keys)) or set(reviewed_keys) != {tuple(relation[key] for key in relation_keys) for relation in existing_relations}:
                        raise AIError("incomplete_claim_audit", "The model omitted or duplicated an existing relation review. Nothing from this batch was saved.")
                    if proposal_payload and proposal_payload["operation"] == "create_relation" and any(
                        all(relation[key] == proposal_payload[key] for key in ("subject_claim_id", "object_claim_id", "relation_type"))
                        for relation in existing_relations
                    ):
                        proposal_payload = None
                    for review in assessment.get("relation_reviews") or []:
                        old = next((relation for relation in existing_relations if all(
                            relation[key] == review.get(key) for key in ("subject_claim_id", "object_claim_id", "relation_type")
                        )), None)
                        if old is None:
                            raise AIError("invalid_claim_audit", "Unknown relation in audit review. Nothing from this batch was saved.")
                        action = review.get("action")
                        if action == "keep":
                            continue
                        replacement = review.get("replacement_type") if action == "replace" else "remove"
                        if action not in {"remove", "replace"} or replacement not in {"supports", "contradicts", "related", "remove"}:
                            raise AIError("invalid_claim_audit", "Invalid relation review action.")
                        subject_id, object_id = old["subject_claim_id"], old["object_claim_id"]
                        if review.get("reverse") and action == "replace":
                            subject_id, object_id = object_id, subject_id
                        proposal_payloads.append({
                            "operation": "revise_relation", "existing_relation": old,
                            "subject_claim_id": subject_id, "object_claim_id": object_id,
                            "subject_statement": claims_by_id[subject_id]["statement"],
                            "object_statement": claims_by_id[object_id]["statement"],
                            "relation_type": replacement, "rationale": str(review.get("rationale") or "")[:2000],
                        })
                        if proposal_payload and proposal_payload["operation"] == "create_relation" and replacement != "remove":
                            proposal_payload = None
                    if proposal_payload:
                        proposal_payloads.append(proposal_payload)
                if assessed_pairs != allowed_pairs:
                    raise AIError(
                        "incomplete_claim_audit",
                        "The model omitted one or more Claim pairs. Nothing from this batch was saved.",
                    )
                proposals = [create_claim_proposal(
                    proposal_payload, "claim-audit-v2",
                    _model_name_from_config(config, "claims", profile_id),
                    {"audit_id": audit_id, "scope": audit.get("scope", {})},
                    self.knowledge_db_path,
                ) for proposal_payload in proposal_payloads]
                snapshot = client.usage_snapshot()
                usage = record_ai_usage(
                    chat_requests=snapshot.get("chat_requests", 0),
                    chat_tokens=snapshot.get("chat_tokens", 0),
                )
                audit = complete_claim_audit_batch(
                    audit_id, pair_keys, len(proposals),
                    model=_model_name_from_config(config, "claims", profile_id),
                    path=self.knowledge_db_path,
                )
                self._send_json({"audit": audit, "proposals": proposals, "usage": usage})
            except (AIError, ValueError) as error:
                try:
                    audit = complete_claim_audit_batch(
                        audit_id, [], 0, error=str(error), path=self.knowledge_db_path,
                    )
                except ValueError:
                    audit = None
                self._send_json(
                    {"error": getattr(error, "code", "claim_audit_failed"),
                     "message": str(error), "audit": audit},
                    HTTPStatus.BAD_GATEWAY,
                )
            return
        if route == "/api/claim-audits/preview":
            scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
            self._send_json(preview_claim_audit(scope, self.knowledge_db_path))
            return
        if route == "/api/claim-audits":
            scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
            audit = create_claim_audit(
                scope, str(payload.get("model_profile_id") or "")[:80],
                self.knowledge_db_path,
            )
            self._send_json(audit, HTTPStatus.CREATED)
            return
        if proposal_accept_match:
            try:
                claim = accept_claim_proposal(
                    proposal_accept_match.group(1), payload, self.knowledge_db_path
                )
                self._send_json(claim, HTTPStatus.CREATED)
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_claim_proposal", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if evidence_proposal_accept_match:
            try:
                evidence = accept_evidence_proposal(
                    evidence_proposal_accept_match.group(1), payload,
                    self.knowledge_db_path,
                )
                self._send_json(evidence, HTTPStatus.CREATED)
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_evidence_proposal", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if wiki_proposal_accept_match:
            try:
                self._send_json(
                    accept_wiki_proposal(
                        wiki_proposal_accept_match.group(1), self.knowledge_db_path
                    )
                )
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_wiki_proposal", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if wiki_proposal_update_match:
            try:
                self._send_json(update_wiki_proposal(
                    wiki_proposal_update_match.group(1), payload,
                    self.knowledge_db_path,
                ))
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_wiki_proposal", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route == "/api/companion/pairing":
            self._send_json(
                self.companion_store.create_pairing(str(payload.get("theme") or "auto")),
                HTTPStatus.CREATED,
            )
            return
        if route == "/api/companion/theme":
            self.companion_store.set_theme(str(payload.get("theme") or "auto"))
            self._send_json(self.companion_store.preferences())
            return
        if route == "/api/companion/pair":
            try:
                token = self.companion_store.pair(
                    str(payload.get("code") or ""), str(payload.get("nonce") or "")
                )
                self._send_json({
                    "token": token,
                    **self.companion_store.preferences(),
                    "version": companion_extension_info()["version"],
                })
            except ValueError as error:
                self._send_json(
                    {"error": "pairing_failed", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route == "/api/companion/captures":
            if not self._companion_authorized():
                self._send_json({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                self._send_json(
                    self.companion_store.add(payload), HTTPStatus.CREATED
                )
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_capture", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route == "/api/companion/commit":
            if not self._companion_authorized():
                self._send_json({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                item = self.companion_store.add(payload)
                result = _commit_companion_capture(
                    item,
                    payload.get("options")
                    if isinstance(payload.get("options"), dict) else {},
                    self.knowledge_db_path,
                    self.content_dir,
                )
                self.companion_store.remove(item["id"])
                self._send_json(result, HTTPStatus.CREATED)
            except ValueError as error:
                self._send_json(
                    {"error": "commit_failed", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if companion_confirm_match:
            item_id = companion_confirm_match.group(1)
            try:
                item = self.companion_store.get(item_id)
                result = _commit_companion_capture(
                    item, payload, self.knowledge_db_path, self.content_dir
                )
                self.companion_store.remove(item_id)
                self._send_json(result, HTTPStatus.CREATED)
            except ValueError as error:
                self._send_json(
                    {"error": "confirm_failed", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if capture_match:
            source_id = capture_match.group(1)
            try:
                source = get_source(source_id, self.knowledge_db_path)
                if source.get("document_hash"):
                    original, _, _ = get_capture_file(source_id, self.content_dir, self.knowledge_db_path)
                    captured = parse_document(original.read_bytes(), source["document_filename"])
                    captured["raw_path"] = str(original)
                else:
                    captured = capture_source_content(source, self.content_dir)
                self._send_json(
                    store_capture(source_id, captured, self.knowledge_db_path),
                    HTTPStatus.CREATED,
                )
            except ValueError as error:
                self._send_json(
                    {"error": "source_not_found", "message": str(error)},
                    HTTPStatus.NOT_FOUND,
                )
            except CaptureError as error:
                self._send_json(
                    {"error": "capture_failed", "message": str(error)},
                    HTTPStatus.BAD_GATEWAY,
                )
            return
        if route == "/api/evidence":
            try:
                self._send_json(
                    create_evidence(payload, self.knowledge_db_path),
                    HTTPStatus.CREATED,
                )
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_evidence", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route == "/api/tags/entity":
            names = payload.get("tags")
            if not isinstance(names, list):
                self._send_json(
                    {"error": "invalid_tags", "message": "tags must be a list"},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                tags = set_entity_tags(
                    str(payload.get("entity_type") or ""),
                    str(payload.get("entity_id") or ""),
                    names,
                    self.knowledge_db_path,
                )
                self._send_json({"tags": tags})
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_tags", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route in {"/api/knowledge/delete-preview", "/api/knowledge/delete"}:
            try:
                if route.endswith("delete-preview"):
                    result = preview_knowledge_deletion(payload.get("entity_type"), payload.get("entity_ids"), self.knowledge_db_path)
                else:
                    result = delete_knowledge_items(payload.get("entity_type"), payload.get("entity_ids"), payload.get("token"), self.knowledge_db_path)
                self._send_json(result)
            except ValueError as error:
                self._send_json({"message": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        if route == "/api/tags/batch":
            names = payload.get("tags")
            entity_ids = payload.get("entity_ids")
            if not isinstance(names, list) or not isinstance(entity_ids, list):
                self._send_json(
                    {"error": "invalid_tags", "message": "entity_ids and tags must be lists"},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                tags_by_entity = add_entity_tags_batch(
                    str(payload.get("entity_type") or ""), entity_ids, names,
                    self.knowledge_db_path,
                )
                self._send_json({
                    "updated": len(tags_by_entity),
                    "tags_by_entity": tags_by_entity,
                })
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_tags", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route == "/api/annotations":
            try:
                self._send_json(
                    create_annotation(payload, self.knowledge_db_path),
                    HTTPStatus.CREATED,
                )
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_annotation", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route == "/api/claims":
            try:
                self._send_json(
                    create_claim(payload, self.knowledge_db_path),
                    HTTPStatus.CREATED,
                )
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_claim", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route == "/api/claim-relations":
            try:
                self._send_json(
                    create_claim_relation(payload, self.knowledge_db_path),
                    HTTPStatus.CREATED,
                )
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_claim_relation", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route == "/api/wiki/proposals/generate":
            try:
                wiki = get_wiki(self.knowledge_db_path)
                config = load_config(self.config_path)
                batch_limit = self._parse_bounded_int(config.get("ai_wiki_claim_limit"), 100, 1, 1000)
                active_claims, batch_scope = prepare_wiki_batch(wiki, batch_limit)
                if not active_claims:
                    raise ValueError("The Wiki needs at least one reviewed active Claim to organize")
                client = _client_from_config(
                    config, skills_dir=self.config_path.parent / "skills", require_embedding=False, role="wiki",
                    profile_id=str(payload.get("model_profile_id") or "")[:80],
                )
                _, temperature, max_tokens, advanced = _copilot_settings(config, "views")
                directory = [{"title": page["title"], "summary": page["summary"],
                              "parent_id": page["parent_id"], "page_id": page["id"],
                              "claim_count": len(page["claim_ids"])} for page in wiki["pages"]]
                reference_pages = []
                if batch_scope["partial"] and directory:
                    selection = client.chat_json(
                        skill_prompt("wiki_context_selection", self.config_path.parent / "skills"),
                        json.dumps({"directory": directory,
                                    "claims": [_wiki_claim_context(claim) for claim in active_claims]}, ensure_ascii=False),
                        temperature=min(temperature, 0.3), max_tokens=1000, extra_parameters=advanced,
                    )
                    page_ids = selection.get("page_ids")
                    pages_by_id = {page["id"]: page for page in wiki["pages"]}
                    if (not isinstance(page_ids, list) or len(page_ids) > 5
                            or any(not isinstance(pid, str) or pid not in pages_by_id for pid in page_ids)
                            or len(set(page_ids)) != len(page_ids)):
                        raise ValueError("Wiki reference selection returned invalid Page ids")
                    selected_ids = set(batch_scope["claim_ids"])
                    references = {claim["id"]: claim for claim in wiki["claims"]
                                  if claim["id"] not in selected_ids and claim["lifecycle"] == "active"
                                  and not claim.get("needs_review")}
                    # Up to ten Claims per page: a large page cannot consume all context.
                    for pid in page_ids:
                        ids = [cid for cid in pages_by_id[pid]["claim_ids"] if cid in references]
                        reference_pages.append({"page_id": pid, "available_claim_count": len(ids),
                                                "truncated": len(ids) > 10,
                                                "claims": [_wiki_claim_context(references[cid]) for cid in ids[:10]]})
                request_payload = json.dumps({
                    "batch_mode": batch_scope["partial"],
                    "batch_instruction": "In batch mode return only selected Claims. Reuse an existing page_id as key to place Claims there; its title and parent remain unchanged. Existing Pages and unselected Claims are preserved by the application. New Pages may use existing page_ids as parent_key.",
                    "instruction": str(payload.get("instruction") or "")[:2000],
                    "current_wiki": directory,
                    "reference_pages": reference_pages,
                    "reference_instruction": "Reference Claims are read-only context, not assignment targets. Samples marked truncated are incomplete; preserve existing summaries where the sample cannot justify changing them.",
                    "claims": [
                        _wiki_claim_context(claim) for claim in active_claims
                    ],
                }, ensure_ascii=False)
                result = client.chat_json(
                    _wiki_maintainer_prompt(self.config_path.parent / "skills"), request_payload,
                    temperature=min(temperature, 0.3),
                    max_tokens=max(3000, max_tokens),
                    extra_parameters=advanced,
                )
                if batch_scope["partial"]:
                    result = merge_wiki_batch(result, wiki, batch_scope["claim_ids"])
                else:
                    assigned = [cid for page in result.get("pages", []) for cid in page.get("claim_ids", [])]
                    if len(assigned) != len(active_claims) or set(assigned) != set(batch_scope["claim_ids"]):
                        raise ValueError("Wiki organization must assign every selected Claim exactly once")
                proposal = create_wiki_proposal(
                    result,
                    _WIKI_PROPOSAL_CAPABILITY,
                    _model_name_from_config(
                        config, "wiki",
                        str(payload.get("model_profile_id") or "")[:80],
                    ),
                    batch_scope,
                    self.knowledge_db_path,
                )
                snapshot = client.usage_snapshot()
                latest_usage = record_ai_usage(
                    chat_requests=snapshot.get("chat_requests", 0),
                    chat_tokens=snapshot.get("chat_tokens", 0),
                )
                self._send_json(
                    {"proposal": proposal, "usage": latest_usage},
                    HTTPStatus.CREATED,
                )
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_wiki_request", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            except AIError as error:
                self._send_json(
                    {"error": error.code, "message": str(error), "usage": get_usage()},
                    HTTPStatus.BAD_REQUEST
                    if error.code in {"ai_unconfigured", "chat_model_missing"}
                    else HTTPStatus.SERVICE_UNAVAILABLE,
                )
            return
        if route == "/api/wiki/reset":
            if payload.get("confirmed") is not True:
                self._send_json({"message": "Confirm the Wiki structure reset first."}, HTTPStatus.BAD_REQUEST)
                return
            self._send_json(reset_wiki_structure(self.knowledge_db_path))
            return
        if route == "/api/wiki/proposals/edit":
            try:
                self._send_json(
                    {"proposal": create_manual_wiki_proposal(self.knowledge_db_path)},
                    HTTPStatus.CREATED,
                )
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_wiki_proposal", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route in {"/api/wiki/articles/generate", "/api/project-articles/generate"}:
            goal = str(payload.get("goal") or "").strip()[:2000]
            if not goal:
                self._send_json(
                    {"error": "goal_required", "message": "Describe what this Article should help you understand."},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                project_id = str(payload.get("project_id") or "").strip()
                if not project_id:
                    raise ValueError("Choose a Project before generating an Article")
                project = get_project(project_id, self.knowledge_db_path)
                claim_ids = {claim["id"] for claim in project.get("claims", [])}
                selected_claims = [
                    claim for claim in project.get("claims", [])
                    if claim["id"] in claim_ids and claim.get("lifecycle") == "active"
                ]
                if not selected_claims:
                    raise ValueError("This Project has no active Claims for an Article")
                if len(selected_claims) > 100:
                    raise ValueError("Article generation currently supports up to 100 Project Claims")
                config = load_config(self.config_path)
                client = _client_from_config(
                    config, skills_dir=self.config_path.parent / "skills", require_embedding=False, role="article",
                    profile_id=str(payload.get("model_profile_id") or "")[:80],
                )
                _, temperature, max_tokens, advanced = _copilot_settings(config, "views")
                selection = client.chat_json(
                    _wiki_article_selection_prompt(self.config_path.parent / "skills"),
                    json.dumps({
                        "goal": goal,
                        "project": {
                            "title": project["title"],
                            "purpose": project["purpose"],
                        },
                        "claims": [
                            _wiki_claim_context(claim) for claim in selected_claims
                        ],
                    }, ensure_ascii=False),
                    temperature=min(temperature, 0.25),
                    max_tokens=min(max(1200, max_tokens), 3000),
                    extra_parameters=advanced,
                )
                valid_ids = {claim["id"] for claim in selected_claims}
                chosen_ids = list(dict.fromkeys(
                    str(item) for item in (
                        selection.get("claim_ids", [])
                        if isinstance(selection, dict) else []
                    )
                    if str(item) in valid_ids
                ))[:100]
                if not chosen_ids:
                    raise AIError(
                        "no_article_material",
                        "The model selected no valid Project Claims for this Article.",
                    )
                chosen_set = set(chosen_ids)
                chosen_claims = sorted(
                    (claim for claim in selected_claims if claim["id"] in chosen_set),
                    key=lambda claim: chosen_ids.index(claim["id"]),
                )
                result = client.chat_json(
                    _wiki_article_prompt(self.config_path.parent / "skills"),
                    json.dumps({
                        "goal": goal,
                        "selection_rationale": str(
                            selection.get("rationale") or ""
                        )[:2000],
                        "outline": (
                            selection.get("outline")
                            if isinstance(selection.get("outline"), list) else []
                        ),
                        "claims": [
                            _wiki_claim_context(claim, include_evidence=True)
                            for claim in chosen_claims
                        ],
                    }, ensure_ascii=False),
                    temperature=min(temperature, 0.4),
                    max_tokens=max(3000, max_tokens),
                    extra_parameters=advanced,
                )
                article = _normalize_wiki_article(result, chosen_set)
                article["selected_claim_ids"] = chosen_ids
                snapshot = client.usage_snapshot()
                latest_usage = record_ai_usage(
                    chat_requests=snapshot.get("chat_requests", 0),
                    chat_tokens=snapshot.get("chat_tokens", 0),
                )
                self._send_json({"article": article, "usage": latest_usage})
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_article_request", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            except AIError as error:
                self._send_json(
                    {"error": error.code, "message": str(error), "usage": get_usage()},
                    HTTPStatus.BAD_REQUEST
                    if error.code in {"ai_unconfigured", "chat_model_missing"}
                    else HTTPStatus.SERVICE_UNAVAILABLE,
                )
            return
        if route == "/api/project-documents":
            try:
                self._send_json(
                    save_project_document(payload, self.knowledge_db_path),
                    HTTPStatus.CREATED,
                )
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_project_document", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route == "/api/search/import":
            candidates = _import_candidates(str(payload.get("content") or ""))
            existing_urls = {
                str(item.get("url") or "").rstrip("/").casefold()
                for item in list_sources(self.knowledge_db_path)
                if item.get("url")
            }
            for candidate in candidates:
                if str(candidate.get("url") or "").rstrip("/").casefold() in existing_urls:
                    candidate["import_status"] = "duplicate"
            self._send_json({"results": candidates, "count": len(candidates)})
            return
        if route == "/api/search/strategy":
            intent = str(payload.get("intent") or "").strip()[:2000]
            if not intent:
                self._send_json(
                    {"error": "empty_intent", "message": "Enter a search intent first."},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            enabled = payload.get("backends") if isinstance(payload.get("backends"), list) else []
            academic_enabled = any(
                item in {"arxiv", "openalex", "semanticscholar"} for item in enabled
            )
            try:
                config = load_config(self.config_path)
                client = _client_from_config(
                    config, skills_dir=self.config_path.parent / "skills", require_embedding=False, role="intelligent_search",
                    profile_id=str(payload.get("model_profile_id") or "")[:80],
                )
                custom_instructions = str(
                    config.get("ai_copilot_instructions") or ""
                ).strip()
                selected_areas = (
                    payload.get("areas")
                    if isinstance(payload.get("areas"), list)
                    else []
                )
                strategy_prompt = build_search_strategy_prompt(
                    selected_areas, custom_instructions, self.config_path.parent / "skills"
                )
                _, copilot_temperature, copilot_max_tokens, copilot_advanced = (
                    _copilot_settings(config)
                )
                strategy = client.chat_json(
                    strategy_prompt,
                    json.dumps({
                        "intent": intent,
                        "available_channels": {
                            "academic": academic_enabled,
                        },
                        "areas": selected_areas,
                        "year_from": payload.get("year_from") or None,
                        "year_to": payload.get("year_to") or None,
                        "output": {"actions": [{
                            "query": "concise retrieval query",
                            "target": "academic",
                            "purpose": "why this retrieval action exists",
                        }]},
                    }, ensure_ascii=False),
                    temperature=copilot_temperature,
                    max_tokens=copilot_max_tokens,
                    extra_parameters=copilot_advanced,
                )
                actions = []
                for item in strategy.get("actions", []) if isinstance(strategy, dict) else []:
                    if not isinstance(item, dict):
                        continue
                    action_query = str(item.get("query") or "").strip()[:500]
                    target = str(item.get("target") or "academic").lower()
                    if target == "academic" and not academic_enabled:
                        continue
                    if action_query and target == "academic":
                        actions.append({
                            "query": action_query,
                            "target": target,
                            "purpose": str(item.get("purpose") or "").strip()[:500],
                        })
                if not actions:
                    actions = [{"query": intent, "target": "academic", "purpose": "Search the original intent directly."}]
                snapshot = client.usage_snapshot()
                usage = record_ai_usage(
                    chat_requests=snapshot.get("chat_requests", 0),
                    chat_tokens=snapshot.get("chat_tokens", 0),
                )
                self._send_json({"actions": actions[:5], "usage": usage})
            except AIError as error:
                self._send_json(
                    {"error": error.code, "message": str(error), "usage": get_usage()},
                    HTTPStatus.BAD_REQUEST if error.code == "ai_unconfigured" else HTTPStatus.SERVICE_UNAVAILABLE,
                )
            return
        if route == "/api/source-discovery":
            source_ids = payload.get("source_ids")
            if not isinstance(source_ids, list):
                source_ids = []
            source_ids = list(dict.fromkeys(
                str(item) for item in source_ids[:3] if item
            ))
            focus = str(payload.get("focus") or "").strip()[:2000]
            if not source_ids:
                self._send_json(
                    {"error": "source_required", "message": "Select one to three Seed Sources."},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            if not can_request(backends=["semanticscholar"]).get("allowed_paper", True):
                self._send_json(
                    {"error": "paper_rate_limited", "message": "The academic request limit has been reached."},
                    HTTPStatus.TOO_MANY_REQUESTS,
                )
                return
            try:
                library = list_sources(self.knowledge_db_path)
                by_id = {str(item.get("id") or ""): item for item in library}
                seeds = [by_id[item] for item in source_ids if item in by_id]
                if len(seeds) != len(source_ids):
                    raise ValueError("One or more selected Seed Sources no longer exist")
                config = load_config(self.config_path)
                discovered = discover_related_papers(
                    seeds,
                    str(config.get("semanticscholar_api_key") or ""),
                )
                latest_usage = get_usage()
                for _ in range(discovered.get("requests", 0)):
                    latest_usage = record_request(backends=["semanticscholar"])
                if not discovered.get("successful_requests"):
                    failures = discovered.get("retrieval_failures", [])
                    reasons = ", ".join(sorted({
                        f"{item['code']}" + (f" (HTTP {item['status']})" if item.get("status") else "")
                        for item in failures
                    }))
                    retry_after = max((item.get("retry_after", 0) for item in failures), default=0)
                    self._send_json({
                        "error": "discovery_retrieval_failed",
                        "message": "Semantic Scholar retrieval failed on all paths: "
                            + (reasons or "no successful response")
                            + (f". Retry in {retry_after} seconds" if retry_after else "")
                            + ". No relevance assessment was run. This does not mean no related papers exist.",
                        "retrieval_failures": failures, "usage": latest_usage,
                    }, HTTPStatus.BAD_GATEWAY)
                    return
                existing_urls = {
                    str(value).rstrip("/").casefold()
                    for source in library
                    for value in (
                        source.get("url"), source.get("paper_url"),
                        source.get("pdf_url"), source.get("doi_url"),
                    )
                    if value
                }
                existing_titles = {
                    str(source.get("title") or "").strip().casefold()
                    for source in library if source.get("title")
                }
                candidates = [
                    item for item in discovered["candidates"]
                    if str(item.get("title") or "").strip().casefold() not in existing_titles
                    and not any(
                        str(item.get(field) or "").rstrip("/").casefold() in existing_urls
                        for field in ("url", "paper_url", "pdf_url", "doi_url")
                        if item.get(field)
                    )
                ]
                if not candidates:
                    self._send_json({
                        **discovered, "results": [], "excluded_results": [],
                        "empty_reason": "already_saved" if discovered["candidates"] else "no_candidates",
                        "already_saved_count": len(discovered["candidates"]),
                        "retrieved_count": len(discovered["candidates"]),
                        "assessed_count": 0, "unassessed_count": 0,
                        "candidate_count": 0, "usage": latest_usage,
                    })
                    return
                client = _client_from_config(
                    config, skills_dir=self.config_path.parent / "skills", require_embedding=False, role="source_discovery",
                    profile_id=str(payload.get("model_profile_id") or "")[:80],
                )
                seed_context = json.dumps({
                    "seeds": [{
                        "title": seed.get("title"),
                        "year": seed.get("year"),
                        "abstract": str(seed.get("abstract") or "")[:5000],
                    } for seed in seeds],
                }, ensure_ascii=False)
                intent = focus or "Find Sources with a material intellectual or technical relationship to the Seed Sources."
                assessed, errors, chat_requests = _verify_batched(
                    client, intent, [], candidates,
                    self._parse_bounded_int(config.get("ai_verify_batch_size"), 5, 1, 20),
                    self._parse_bounded_int(config.get("ai_verify_concurrency"), 1, 1, 8),
                    20,
                    verification_context=seed_context,
                )
                results = [
                    item for item in assessed
                    if item.get("relevance_tier") != "excluded"
                ][:20]
                excluded = [
                    item for item in assessed
                    if item.get("relevance_tier") == "excluded"
                ]
                snapshot = client.usage_snapshot()
                latest_usage = record_ai_usage(
                    chat_requests=snapshot.get("chat_requests", chat_requests),
                    chat_tokens=snapshot.get("chat_tokens", 0),
                )
                self._send_json({
                    "seeds": [{"id": item["id"], "title": item["title"]} for item in seeds],
                    "focus": focus,
                    "results": results,
                    "excluded_results": excluded,
                    "candidate_count": len(candidates),
                    "retrieved_count": len(discovered["candidates"]),
                    "already_saved_count": len(discovered["candidates"]) - len(candidates),
                    "assessed_count": len(assessed),
                    "unassessed_count": max(0, len(candidates) - len(assessed)),
                    "undisplayed_count": max(0, len(assessed) - len(excluded) - len(results)),
                    "truncated_paths": discovered.get("truncated_paths", []),
                    "cache_hits": discovered.get("cache_hits", 0),
                    "path_count": discovered.get("path_count", 0),
                    "requests": discovered.get("requests", 0),
                    "successful_requests": discovered.get("successful_requests", 0),
                    "retrieval_failures": discovered.get("retrieval_failures", []),
                    "resolved_seed_count": discovered.get("resolved_seed_count", 0),
                    "unresolved_seed_count": discovered.get("unresolved_seed_count", 0),
                    "warnings": [f"verification_failed:{error.code}" for error in errors],
                    "usage": latest_usage,
                })
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_source_discovery", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            except AIError as error:
                self._send_json(
                    {"error": error.code, "message": str(error), "usage": get_usage()},
                    HTTPStatus.BAD_REQUEST
                    if error.code in {"ai_unconfigured", "chat_model_missing"}
                    else HTTPStatus.SERVICE_UNAVAILABLE,
                )
            return
        if route == "/api/evidence-pages/select":
            client = None
            try:
                ids = payload.get("source_ids")
                focus = str(payload.get("focus") or "").strip()[:2000]
                limit = int(payload.get("max_pages", 4))
                config = load_config(self.config_path)
                source_limit = self._parse_bounded_int(config.get("ai_evidence_source_limit"), 6, 1, 100)
                if not isinstance(ids, list) or not 1 <= len(ids) <= source_limit or not focus or not 1 <= limit <= MAX_PAGES:
                    raise ValueError(f"Choose 1–{source_limit} webpage Sources, a Focus, and a total page limit of 1–{MAX_PAGES}")
                sources = [get_source(str(sid), self.knowledge_db_path) for sid in dict.fromkeys(ids)]
                if any(s.get("document_hash") or s.get("source_type") == "paper" for s in sources):
                    raise ValueError("Related pages is for webpages. Use Selected pages for papers and uploaded documents.")
                pages, warnings = discover_pages(sources)
                if not pages:
                    raise ValueError("No accessible page directory was found; no model request was made")
                config = load_config(self.config_path)
                client = _client_from_config(config, skills_dir=self.config_path.parent / "skills", require_embedding=False,
                                             role="evidence", profile_id=str(payload.get("model_profile_id") or "")[:80])
                selected, summary = select_pages(client, pages, focus, limit, self.config_path.parent / "skills")
                response = {"pages": selected, "summary": summary, "warnings": warnings,
                            "candidate_count": len(pages), "request_mode": config.get("ai_evidence_request_mode", "combined")}
                status = HTTPStatus.OK
            except (AIError, ValueError, OSError, TypeError) as error:
                response = {"message": str(error)}
                status = HTTPStatus.BAD_GATEWAY if isinstance(error, AIError) else HTTPStatus.BAD_REQUEST
            if client is not None:
                snapshot = client.usage_snapshot()
                response["usage"] = record_ai_usage(chat_requests=snapshot.get("chat_requests", 0), chat_tokens=snapshot.get("chat_tokens", 0))
            self._send_json(response, status)
            return
        if route == "/api/evidence-proposals/generate":
            source_ids = payload.get("source_ids")
            if not isinstance(source_ids, list):
                source_ids = []
            selection_limit = self._parse_bounded_int(load_config(self.config_path).get("ai_evidence_source_limit"), 6, 1, 100)
            if len(source_ids) > selection_limit:
                self._send_json({"message": f"Select at most {selection_limit} items for this run."}, HTTPStatus.BAD_REQUEST)
                return
            source_ids = list(dict.fromkeys(str(item) for item in source_ids if item))
            focus = str(payload.get("focus") or "").strip()[:2000]
            if not source_ids or not focus:
                self._send_json(
                    {"error": "source_focus_required",
                     "message": "Select at least one Source and enter a Focus."},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                config = load_config(self.config_path)
                profile_id = str(payload.get("model_profile_id") or "")[:80]
                client = _client_from_config(config, skills_dir=self.config_path.parent / "skills", require_embedding=False, role="evidence", profile_id=profile_id)
                profile = next((item for item in ai_model_profiles(config) if item["id"] == profile_id), None) or ai_profile_for_role(config, "evidence")
                capabilities = set(profile.get("capabilities", []))
                related_workspaces = {}
                related_pages = payload.get("related_pages")
                request_mode = config.get("ai_evidence_request_mode", "combined")
                seed_ids = list(source_ids)
                if related_pages is not None:
                    if not isinstance(related_pages, list) or not 1 <= len(related_pages) <= MAX_PAGES:
                        raise ValueError(f"Related page count must be between 1 and {MAX_PAGES}; requests are never silently split")
                    request_mode = payload.get("related_request_mode", request_mode)
                    if request_mode not in {"combined", "individual"}:
                        raise ValueError("Invalid related-page request mode")
                    seeds = {sid: get_source(sid, self.knowledge_db_path) for sid in seed_ids}
                    saved = {page_url(s["url"]): s for s in list_sources(self.knowledge_db_path) if str(s.get("url") or "").startswith(("http://", "https://"))}
                    source_ids = []
                    for page in related_pages:
                        if not isinstance(page, dict):
                            raise ValueError("Invalid related page")
                        parent = seeds.get(str(page.get("parent_source_id") or ""))
                        url = page_url(page.get("url"))
                        if parent is None or not in_scope(url, parent.get("url") or parent.get("paper_url")):
                            raise ValueError("Selected related page is outside the seed website/version")
                        source = saved.get(url)
                        if source:
                            workspace = get_source_workspace(source["id"], self.knowledge_db_path)
                        else:
                            source = {"id": hashlib.sha256(url.encode()).hexdigest()[:32], "url": url,
                                      "title": str(page.get("title") or url)[:1000], "source_type": "web",
                                      "parent_source_id": parent["id"]}
                            workspace = {"source": source, "segments": [], "capture": None, "pending_source": True}
                        if source["id"] not in related_workspaces:
                            related_workspaces[source["id"]] = workspace
                            source_ids.append(source["id"])
                groups = [[sid] for sid in source_ids] if request_mode == "individual" else [source_ids]
                proposals, warnings, summaries = [], [], []
                for group in groups:
                    try:
                        workspaces, documents, urls, manifest = [], [], [], []
                        for source_id in group:
                            workspace = related_workspaces.get(source_id) or get_source_workspace(source_id, self.knowledge_db_path)
                            source = workspace["source"]
                            url = source.get("url") or source.get("paper_url")
                            kind = "capture"
                            local_document = bool(source.get("document_hash"))
                            local_pdf = local_document and workspace.get("capture", {}).get("media_type") == "application/pdf"
                            is_pdf = local_pdf or bool(source.get("pdf_url")) or source.get("source_type") == "paper" or str(url).split("?")[0].endswith(".pdf")
                            if is_pdf and capabilities & {"native_documents", "file_extraction"}:
                                if local_pdf:
                                    original, _, _ = get_capture_file(source_id, self.content_dir, self.knowledge_db_path)
                                    captured = {"media_type": "application/pdf", "raw_path": str(original)}
                                elif workspace.get("pending_source"):
                                    import tempfile
                                    with tempfile.TemporaryDirectory(prefix="knowte-related-") as temporary:
                                        captured = capture_source_content(source, Path(temporary), parse_pdf=False)
                                        document_bytes = Path(captured["raw_path"]).read_bytes()
                                else:
                                    captured = capture_source_content(source, self.content_dir, parse_pdf=False)
                                if captured["media_type"] != "application/pdf":
                                    raise CaptureError("Source did not return a PDF. Choose URL Fetch or text explicitly.")
                                documents.append({"data": document_bytes if workspace.get("pending_source") else Path(captured["raw_path"]).read_bytes(), "mime_type": "application/pdf", "filename": f"{source_id}.pdf"})
                                kind = "native_document"
                            elif "url_fetch" in capabilities and url:
                                urls.append(str(url))
                                kind = "url"
                            elif not workspace.get("segments"):
                                if workspace.get("pending_source"):
                                    import tempfile
                                    with tempfile.TemporaryDirectory(prefix="knowte-related-") as temporary:
                                        captured = capture_source_content(source, Path(temporary))
                                    workspace["segments"] = [{"id": f"{source_id}-{i}", "text": text,
                                        "locator": captured["locators"][i]} for i, text in enumerate(captured["segments"])]
                                else:
                                    captured = capture_source_content(source, self.content_dir)
                                    workspace = store_capture(source_id, captured, self.knowledge_db_path)
                            segments, budget = [], 0
                            if kind == "capture":
                                if not any(str(s.get("text") or "").strip() for s in workspace.get("segments", [])):
                                    raise ValueError("No extractable text. Use a native PDF model, or capture Evidence manually in Inspect.")
                                for segment in workspace.get("segments", []):
                                    text = str(segment.get("text") or "")[:max(0, 45000 - budget)]
                                    if not text:
                                        continue
                                    segments.append({"segment_id": segment["id"], "locator": segment.get("locator", ""), "text": text})
                                    budget += len(text)
                                if sum(len(item.get("text", "")) for item in workspace.get("segments", [])) > budget:
                                    warnings.append(f"{source['title']}: text truncated to 45,000 characters.")
                            workspaces.append(workspace)
                            images = []
                            if url and not is_pdf and not local_document:
                                try:
                                    images = discover_source_images(str(url))
                                except (CaptureError, OSError, ValueError) as error:
                                    warnings.append(f"{source['title']}: image discovery unavailable: {error}")
                            manifest.append({"source_id": source_id, "title": source["title"], "url": url, "input_kind": kind, "segments": segments, "images": images})
                        request_text = json.dumps({"focus": focus, "sources": manifest}, ensure_ascii=False)
                        if documents or urls:
                            result = client.grounded_json(_evidence_document_proposal_prompt(self.config_path.parent / "skills"), request_text, documents=documents, urls=urls, max_tokens=3500)
                        else:
                            prompt = _evidence_document_proposal_prompt if any(item["images"] for item in manifest) else _evidence_proposal_prompt
                            result = client.chat_json(prompt(self.config_path.parent / "skills"), request_text, temperature=0.1, max_tokens=3500)
                        candidates = result.get("evidence", [])
                        if result.get("summary"):
                            summaries.append(str(result["summary"])[:1000])
                        created = 0
                        for candidate in candidates[:12] if isinstance(candidates, list) else []:
                            if not isinstance(candidate, dict):
                                continue
                            sid = str(candidate.get("source_id") or "")
                            if not sid:
                                sid = next((w["source"]["id"] for w in workspaces if any(s["id"] == candidate.get("segment_id") for s in w.get("segments", []))), "")
                            workspace = next((w for w in workspaces if w["source"]["id"] == sid), None)
                            if workspace is None:
                                continue
                            entry = next(item for item in manifest if item["source_id"] == sid)
                            if candidate.get("evidence_type") == "snapshot":
                                asset = next((item for item in entry["images"] if item["image_url"] == candidate.get("image_url")), None)
                                if asset is None:
                                    warnings.append(f"{entry['title']}: proposed image was not in this page's original image directory.")
                                    continue
                                try:
                                    candidate = {**candidate, "image_data": capture_evidence_image(asset["image_url"]),
                                                 "quote": asset["caption"], "image_alt": asset["alt"],
                                                 "segment_id": "", "verification": "external_unverified"}
                                except (CaptureError, OSError, ValueError) as error:
                                    warnings.append(f"{entry['title']}: {error}")
                                    continue
                            mapped = _map_document_quote(workspace, candidate.get("quote", ""))
                            if candidate.get("evidence_type") == "snapshot":
                                pass
                            elif mapped:
                                segment_id, quote = mapped
                                candidate = {**candidate, "quote": quote, "segment_id": segment_id, "verification": "local_match"}
                            elif entry["input_kind"] != "capture":
                                candidate = {**candidate, "segment_id": "", "verification": "external_unverified"}
                            else:
                                warnings.append(f"{entry['title']}: an excerpt did not match captured text.")
                                continue
                            try:
                                related_source = None
                                if workspace.get("pending_source"):
                                    related_source = {"title": workspace["source"]["title"], "url": entry["url"],
                                                      "parent_source_id": workspace["source"]["parent_source_id"]}
                                    candidate = {**candidate, "segment_id": "", "verification": "external_unverified"}
                                proposals.append(create_evidence_proposal(
                                    {**candidate, "source_id": sid, "source_url": entry["url"], "related_source": related_source},
                                    _EVIDENCE_PROPOSAL_CAPABILITY, _model_name_from_config(config, "evidence", profile_id),
                                    {"kind": "related_pages" if related_pages is not None else "selected_sources", "source_ids": group, "seed_source_ids": seed_ids, "focus": focus,
                                     "summary": str(result.get("summary") or "")[:2000],
                                     "inputs": [{"source_id": item["source_id"], "title": item["title"], "url": item["url"], "input_kind": item["input_kind"],
                                                 "text_characters": sum(len(s["text"]) for s in item["segments"])} for item in manifest]},
                                    self.knowledge_db_path,
                                ))
                                created += 1
                            except ValueError as error:
                                warnings.append(f"{entry['title']}: {error}")
                        if not created:
                            warnings.append("No usable Evidence returned for: " + ", ".join(item["title"] for item in manifest))
                    except (AIError, CaptureError, ValueError, OSError) as error:
                        warnings.append(f"Sources {', '.join(group)}: {error}")
                snapshot = client.usage_snapshot()
                latest_usage = record_ai_usage(chat_requests=snapshot.get("chat_requests", 0), chat_tokens=snapshot.get("chat_tokens", 0))
                self._send_json({"proposals": proposals, "warnings": warnings, "summary": "\n".join(summaries), "usage": latest_usage}, HTTPStatus.CREATED)
            except (AIError, CaptureError) as error:
                self._send_json(
                    {"error": getattr(error, "code", "evidence_proposal_failed"),
                     "message": str(error)}, HTTPStatus.BAD_GATEWAY,
                )
            except ValueError as error:
                self._send_json(
                    {"error": "source_not_found", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route == "/api/claim-proposals/generate":
            evidence_ids = payload.get("evidence_ids")
            if not isinstance(evidence_ids, list):
                evidence_ids = []
            selection_limit = self._parse_bounded_int(load_config(self.config_path).get("ai_claim_evidence_limit"), 30, 1, 100)
            if len(evidence_ids) > selection_limit:
                self._send_json({"message": f"Select at most {selection_limit} items for this run."}, HTTPStatus.BAD_REQUEST)
                return
            evidence_ids = list(dict.fromkeys(
                str(item) for item in evidence_ids if item
            ))
            evidence_items = [
                item for item in list_evidence(self.knowledge_db_path)
                if item["id"] in evidence_ids
            ]
            if not evidence_items:
                self._send_json(
                    {
                        "error": "evidence_required",
                        "message": "Select at least one Evidence item.",
                    },
                    HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                config = load_config(self.config_path)
                client = _client_from_config(
                    config, skills_dir=self.config_path.parent / "skills", require_embedding=False, role="claims",
                    profile_id=str(payload.get("model_profile_id") or "")[:80],
                )
                artifact = payload.get("artifact")
                artifact = artifact if isinstance(artifact, dict) else {}
                focus = str(payload.get("focus") or "").strip()[:2000]
                scope = {
                    "kind": "selected_evidence",
                    "evidence_ids": evidence_ids,
                    "artifact_id": str(artifact.get("id") or ""),
                    "artifact_title": str(artifact.get("title") or "")[:300],
                    "focus": focus,
                }
                evidence_context = [
                    {
                        "evidence_id": item["id"],
                        "type": item["evidence_type"],
                        "source_id": item["source_id"],
                        "source_title": item["source_title"],
                        "source_provider": item.get("source_provider", ""),
                        "locator": item["locator"],
                        "quote": item["quote"][:5000],
                        "tags": [tag["name"] for tag in item.get("tags", [])],
                    }
                    for item in evidence_items
                ]
                context_tags = list(dict.fromkeys(
                    tag
                    for item in evidence_context
                    for tag in item.get("tags", [])
                    if tag
                ))
                related_claims, comparison_scope = find_claim_comparison_context(
                    evidence_context, focus,
                    self._parse_bounded_int(config.get("ai_claim_comparison_limit"), 100, 1, 1000),
                    self.knowledge_db_path,
                )
                scope["comparison_claim_ids"] = [
                    item["claim_id"] for item in related_claims
                ]
                request_payload = json.dumps(
                    {
                        "scope": scope,
                        "focus": focus,
                        "artifact": {
                            "title": str(artifact.get("title") or "")[:300],
                            "purpose": str(artifact.get("purpose") or "")[:2000],
                        },
                        "evidence": evidence_context,
                        "existing_claims": related_claims,
                        "instruction": str(payload.get("instruction") or "")[:2000],
                    },
                    ensure_ascii=False,
                )
                result = client.chat_json(
                    _claim_proposal_prompt(self.config_path.parent / "skills"), request_payload,
                    temperature=0.1, max_tokens=3000,
                )
                candidates = result.get("claims") if isinstance(result, dict) else []
                if not isinstance(candidates, list):
                    candidates = []
                allowed_evidence = set(evidence_ids)
                allowed_claims = {
                    item["claim_id"]: item for item in related_claims
                }
                proposals = []
                new_claim_refs = {}
                duplicate_refs = set()
                for candidate in candidates[:20]:
                    if isinstance(candidate, dict) and candidate.get("temp_id"):
                        reference = str(candidate["temp_id"])
                        if reference in new_claim_refs:
                            duplicate_refs.add(reference)
                        new_claim_refs[reference] = None
                for candidate in candidates[:20]:
                    if not isinstance(candidate, dict):
                        continue
                    links = []
                    for link in candidate.get("evidence") or []:
                        if not isinstance(link, dict):
                            continue
                        if str(link.get("evidence_id") or "") not in allowed_evidence:
                            continue
                        links.append(link)
                    candidate = {**candidate, "evidence": links}
                    if not links or not any(
                        str(link.get("stance") or "supports").lower()
                        in {"supports", "limits"}
                        for link in links
                    ):
                        continue
                    if str(candidate.get("basis") or "").lower() == "inference" and len({
                        link.get("evidence_id") for link in links
                    }) < 2:
                        continue
                    try:
                        proposals.append(create_claim_proposal(
                            {**candidate, "operation": "create_claim"},
                            _CLAIM_PROPOSAL_CAPABILITY,
                            _model_name_from_config(
                                config, "claims",
                                str(payload.get("model_profile_id") or "")[:80],
                            ),
                            scope,
                            self.knowledge_db_path,
                        ))
                        reference = str(candidate.get("temp_id") or "")
                        if reference and reference not in duplicate_refs and reference not in allowed_claims:
                            new_claim_refs[reference] = {
                                "claim_id": "proposal:" + proposals[-1]["id"],
                                "statement": candidate.get("statement", ""),
                            }
                    except ValueError:
                        continue
                updates = result.get("existing_claim_updates") if isinstance(result, dict) else []
                for candidate in (updates if isinstance(updates, list) else [])[:20]:
                    if not isinstance(candidate, dict):
                        continue
                    target_id = str(candidate.get("claim_id") or "")
                    target = allowed_claims.get(target_id)
                    if not target:
                        continue
                    links = []
                    for link in candidate.get("evidence") or []:
                        if not isinstance(link, dict):
                            continue
                        if str(link.get("evidence_id") or "") in allowed_evidence:
                            links.append(link)
                    if not links:
                        continue
                    try:
                        proposals.append(create_claim_proposal(
                            {
                                "operation": "link_evidence",
                                "target_claim_id": target_id,
                                "target_statement": target["statement"],
                                "evidence": links,
                                "rationale": str(candidate.get("rationale") or "")[:2000],
                                "caveats": candidate.get("caveats") or [],
                            },
                            _CLAIM_PROPOSAL_CAPABILITY,
                            _model_name_from_config(
                                config, "claims",
                                str(payload.get("model_profile_id") or "")[:80],
                            ), scope, self.knowledge_db_path,
                        ))
                    except ValueError:
                        continue
                relations = result.get("claim_relations") if isinstance(result, dict) else []
                relation_targets = {**allowed_claims, **{key: value for key, value in new_claim_refs.items() if value and key not in duplicate_refs}}
                for candidate in (relations if isinstance(relations, list) else [])[:20]:
                    if not isinstance(candidate, dict):
                        continue
                    subject_id = str(candidate.get("subject_claim_id") or "")
                    object_id = str(candidate.get("object_claim_id") or "")
                    relation_type = str(candidate.get("relation_type") or "").lower()
                    if (
                        subject_id not in relation_targets
                        or object_id not in relation_targets
                        or subject_id == object_id
                        or relation_type not in {"supports", "contradicts", "related"}
                    ):
                        continue
                    try:
                        proposals.append(create_claim_proposal(
                            {
                                "operation": "create_relation",
                                "subject_claim_id": relation_targets[subject_id]["claim_id"],
                                "subject_statement": relation_targets[subject_id]["statement"],
                                "object_claim_id": relation_targets[object_id]["claim_id"],
                                "object_statement": relation_targets[object_id]["statement"],
                                "relation_type": relation_type,
                                "rationale": str(candidate.get("rationale") or "")[:2000],
                                "evidence": [],
                            },
                            _CLAIM_PROPOSAL_CAPABILITY,
                            _model_name_from_config(
                                config, "claims",
                                str(payload.get("model_profile_id") or "")[:80],
                            ), scope, self.knowledge_db_path,
                        ))
                    except ValueError:
                        continue
                skipped_items = [
                    {
                        "evidence_ids": [
                            str(item) for item in candidate.get("evidence_ids", [])[:12]
                            if str(item) in allowed_evidence
                        ],
                        "reason": str(candidate.get("reason") or "")[:1000],
                    }
                    for candidate in (
                        result.get("skipped", [])
                        if isinstance(result.get("skipped"), list) else []
                    )[:20]
                    if isinstance(candidate, dict) and str(candidate.get("reason") or "").strip()
                ]
                if not proposals and not skipped_items:
                    raise AIError(
                        "no_claim_proposals",
                        "The model returned neither valid Claim changes nor skip explanations.",
                    )
                snapshot = client.usage_snapshot()
                latest_usage = record_ai_usage(
                    chat_requests=snapshot.get("chat_requests", 0),
                    chat_tokens=snapshot.get("chat_tokens", 0),
                )
                self._send_json(
                    {
                        "proposals": proposals,
                        "summary": str(result.get("summary") or "")[:1000],
                        "skipped": skipped_items,
                        "comparison_claim_count": len(related_claims),
                        "comparison_scope": {
                            **comparison_scope,
                            "total_claim_count": len(list_claims(self.knowledge_db_path)),
                            "tag_count": len(context_tags),
                            "source_count": len({item["source_id"] for item in evidence_context}),
                        },
                        "usage": latest_usage,
                    },
                    HTTPStatus.CREATED if proposals else HTTPStatus.OK,
                )
            except AIError as error:
                self._send_json(
                    {"error": error.code, "message": str(error)},
                    HTTPStatus.BAD_GATEWAY,
                )
            return
        if route == "/api/config/default-search-mode":
            try:
                config = set_default_search_mode(
                    str(payload.get("mode") or ""),
                    self.config_path,
                    ai_review=payload.get("ai_review"),
                )
                self._send_json(
                    {"default_search_mode": config["default_search_mode"],
                     "search_ai_review": self._parse_bool(config.get("search_ai_review", "false"))}
                )
            except ValueError as error:
                self._send_json(
                    {
                        "error": "invalid_default_search_mode",
                        "message": str(error),
                    },
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route == "/api/artifacts":
            try:
                artifact = create_artifact(payload, self.knowledge_db_path)
                self._send_json(artifact, HTTPStatus.CREATED)
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_artifact", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route == "/api/library/sources":
            source_payload = payload.get("source")
            if not isinstance(source_payload, dict):
                self._send_json(
                    {
                        "error": "invalid_source",
                        "message": "source is required",
                    },
                    HTTPStatus.BAD_REQUEST,
                )
                return
            artifact_id = str(payload.get("artifact_id") or "").strip() or None
            try:
                source, source_created, link_created = save_source(
                    source_payload,
                    artifact_id,
                    self.knowledge_db_path,
                )
                self._send_json(
                    {
                        "source": source,
                        "source_created": source_created,
                        "artifact_link_created": link_created,
                    },
                    (
                        HTTPStatus.CREATED
                        if source_created
                        else HTTPStatus.OK
                    ),
                )
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_source", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route == "/api/library/sources/batch":
            sources = payload.get("sources")
            if not isinstance(sources, list) or not sources or len(sources) > 100:
                self._send_json(
                    {
                        "error": "invalid_sources",
                        "message": "Select between 1 and 100 Sources.",
                    },
                    HTTPStatus.BAD_REQUEST,
                )
                return
            artifact_id = str(payload.get("artifact_id") or "").strip() or None
            saved = []
            try:
                for source_payload in sources:
                    if not isinstance(source_payload, dict):
                        raise ValueError("each source must be an object")
                    source, source_created, link_created = save_source(
                        source_payload,
                        artifact_id,
                        self.knowledge_db_path,
                    )
                    saved.append(
                        {
                            "source": source,
                            "source_created": source_created,
                            "artifact_link_created": link_created,
                        }
                    )
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_source", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            self._send_json(
                {
                    "saved": saved,
                    "count": len(saved),
                    "sources_created": sum(
                        item["source_created"] for item in saved
                    ),
                    "artifact_links_created": sum(
                        item["artifact_link_created"] for item in saved
                    ),
                },
                HTTPStatus.CREATED
                if any(item["source_created"] for item in saved)
                else HTTPStatus.OK,
            )
            return
        if route == "/api/review/chat":
            question = str(payload.get("question") or "").strip()
            review_context = str(payload.get("context") or "search").strip()[:40]
            selected = payload.get("sources")
            if not question:
                self._send_json(
                    {"error": "empty_question", "message": "Enter a question."},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            if not isinstance(selected, list):
                selected = []
            context_limit = self._parse_bounded_int(load_config(self.config_path).get("ai_copilot_context_limit"), 12, 1, 100)
            context_count = sum(len(payload.get(key) or []) for key in ("sources", "evidence", "claims") if isinstance(payload.get(key), list))
            if context_count > context_limit:
                self._send_json({"message": f"Context supports {context_limit} items."}, HTTPStatus.BAD_REQUEST)
                return
            selected = [item for item in selected if isinstance(item, dict)]
            workspace_cache = {}
            source_context = []
            for index, item in enumerate(selected):
                resolved = item
                annotations = item.get("annotations", [])
                source_id = str(item.get("id") or "")[:80]
                if source_id:
                    try:
                        workspace = get_source_workspace(
                            source_id, self.knowledge_db_path
                        )
                        workspace_cache[source_id] = workspace
                        resolved = {**item, **workspace["source"]}
                        annotations = workspace["annotations"]
                    except ValueError:
                        pass
                source_context.append({
                    "index": index + 1,
                    "id": source_id,
                    "title": str(resolved.get("title") or "")[:300],
                    "authors": str(resolved.get("authors") or "")[:300],
                    "year": resolved.get("year"),
                    "source": str(resolved.get("source") or "")[:100],
                    "abstract": str(resolved.get("abstract") or "")[:1800],
                    "match_reason": str(item.get("match_reason") or "")[:800],
                    "tags": [
                        str(tag.get("name") or "")[:80]
                        for tag in resolved.get("tags", [])[:20]
                        if isinstance(tag, dict)
                    ],
                    "annotations": [
                        str(annotation.get("body") or "")[:800]
                        for annotation in annotations[:8]
                        if isinstance(annotation, dict)
                    ],
                })
            evidence = payload.get("evidence")
            if not isinstance(evidence, list):
                evidence = []
            evidence_context = []
            snapshot_images = []
            for item in evidence:
                if not isinstance(item, dict):
                    continue
                evidence_id = str(item.get("id") or "")[:80]
                source_id = str(item.get("source_id") or "")[:80]
                resolved = item
                source_title = str(item.get("source_title") or "")[:300]
                if evidence_id and source_id:
                    try:
                        workspace = workspace_cache.get(source_id)
                        if workspace is None:
                            workspace = get_source_workspace(
                                source_id, self.knowledge_db_path
                            )
                            workspace_cache[source_id] = workspace
                        resolved = next(
                            candidate for candidate in workspace["evidence"]
                            if candidate["id"] == evidence_id
                        )
                        source_title = str(workspace["source"].get("title") or "")[:300]
                    except (ValueError, StopIteration):
                        resolved = item
                evidence_type = str(resolved.get("evidence_type") or "text")[:30]
                context_item = {
                    "index": len(evidence_context) + 1,
                    "id": evidence_id,
                    "type": evidence_type,
                    "source_title": source_title,
                    "locator": str(resolved.get("locator") or "")[:200],
                    "annotations": [
                        str(annotation.get("body") or "")[:800]
                        for annotation in resolved.get("annotations", [])[:8]
                        if isinstance(annotation, dict)
                    ],
                    "tags": [
                        str(tag.get("name") or "")[:80]
                        for tag in resolved.get("tags", [])[:20]
                        if isinstance(tag, dict)
                    ],
                }
                if evidence_type == "snapshot":
                    context_item["visual_content"] = "Attached image"
                    if len(snapshot_images) < 4 and evidence_id:
                        try:
                            snapshot_path = get_snapshot_file(
                                evidence_id, self.content_dir, self.knowledge_db_path
                            )
                            encoded = base64.b64encode(snapshot_path.read_bytes()).decode("ascii")
                            snapshot_images.append(
                                {"type": "image_url", "image_url": {
                                    "url": f"data:image/png;base64,{encoded}"
                                }}
                            )
                        except (OSError, ValueError):
                            context_item["visual_content"] = "Snapshot unavailable"
                else:
                    context_item["quote"] = str(resolved.get("quote") or "")[:3000]
                evidence_context.append(context_item)
            artifact = payload.get("artifact")
            artifact_context = artifact if isinstance(artifact, dict) else {}
            selected_claims = payload.get("claims")
            if not isinstance(selected_claims, list):
                selected_claims = []
            claim_context = []
            for item in selected_claims:
                if not isinstance(item, dict):
                    continue
                claim_context.append({
                    "id": str(item.get("id") or "")[:80],
                    "statement": str(item.get("statement") or "")[:4000],
                    "basis": str(item.get("basis") or "")[:30],
                    "review_state": str(item.get("review_state") or "accepted")[:30],
                    "lifecycle": str(item.get("lifecycle") or "")[:30],
                    "evidence": [
                        {
                            "stance": str(link.get("stance") or "")[:30],
                            "source_title": str(link.get("source_title") or "")[:300],
                            "locator": str(link.get("locator") or "")[:300],
                            "quote": str(link.get("quote") or "")[:3000],
                        }
                        for link in item.get("evidence", [])[:12]
                        if isinstance(link, dict)
                    ],
                })
            conversation = payload.get("conversation")
            if not isinstance(conversation, list):
                conversation = []
            conversation_context = [
                {
                    "role": (
                        "assistant"
                        if str(item.get("role") or "") == "assistant"
                        else "user"
                    ),
                    "content": str(item.get("content") or "")[:2000],
                    "context_refs": [
                        {
                            "type": str(reference.get("type") or "")[:20],
                            "id": str(reference.get("id") or "")[:80],
                        }
                        for reference in item.get("context_refs", [])[:12]
                        if isinstance(reference, dict)
                    ],
                }
                for item in conversation[-8:]
                if isinstance(item, dict) and str(item.get("content") or "").strip()
            ]
            try:
                config = load_config(self.config_path)
                client = _client_from_config(
                    config, skills_dir=self.config_path.parent / "skills",
                    require_embedding=False,
                    role="copilot",
                    profile_id=str(payload.get("model_profile_id") or "")[:80],
                    timeout_scope="search" if review_context == "search" else "stage",
                )
                copilot_prompt, copilot_temperature, copilot_max_tokens, copilot_advanced = _copilot_settings(
                    config, review_context
                )
                review_input = json.dumps(
                    {
                        "question": question,
                        "review_context": review_context,
                        "active_artifact": {
                            "title": str(artifact_context.get("title") or "")[:300],
                            "purpose": str(artifact_context.get("purpose") or "")[:1200],
                        },
                        "search_strategy": (
                            payload.get("search_strategy")
                            if isinstance(payload.get("search_strategy"), dict)
                            else {}
                        ),
                        "selected_sources": source_context,
                        "selected_evidence": evidence_context,
                        "selected_claims": claim_context,
                        "wiki_context": (
                            payload.get("wiki_context")
                            if isinstance(payload.get("wiki_context"), dict)
                            else {}
                        ),
                        "recent_conversation": conversation_context,
                    },
                    ensure_ascii=False,
                )
                user_content = (
                    [{"type": "text", "text": review_input}, *snapshot_images]
                    if snapshot_images else review_input
                )
                review = client.chat_json(
                    review_copilot_prompt(review_context, config.get("ai_copilot_instructions", ""), self.config_path.parent / "skills"),
                    user_content,
                    temperature=copilot_temperature,
                    max_tokens=copilot_max_tokens,
                    extra_parameters=copilot_advanced,
                    allow_text_fallback=True,
                )
                if not isinstance(review, dict):
                    raise AIError(
                        "invalid_model_json",
                        "Review response was not an object.",
                    )
                snapshot = client.usage_snapshot()
                latest_usage = record_ai_usage(
                    chat_requests=snapshot.get("chat_requests", 0),
                    chat_tokens=snapshot.get("chat_tokens", 0),
                )
                proposed_search_actions = []
                if review_context == "search" and isinstance(review.get("search_actions"), list):
                    for item in review["search_actions"][:5]:
                        if not isinstance(item, dict):
                            continue
                        action_query = str(item.get("query") or "").strip()[:500]
                        target = str(item.get("target") or "both").strip().lower()
                        if action_query and target in {"academic", "web", "both"}:
                            proposed_search_actions.append({
                                "query": action_query,
                                "target": target,
                                "purpose": str(item.get("purpose") or "").strip()[:500],
                            })
                self._send_json(
                    {
                        "answer": str(review.get("answer") or "").strip(),
                        "recommendations": (
                            review.get("recommendations")
                            if review_context == "library"
                            and isinstance(review.get("recommendations"), list)
                            else []
                        ),
                        "search_actions": proposed_search_actions,
                        "structured_output_degraded": bool(
                            review.get("_structured_output_degraded")
                        ),
                        "usage": latest_usage,
                    }
                )
            except AIError as error:
                self._send_json(
                    {
                        "error": error.code,
                        "message": str(error),
                        "usage": get_usage(),
                    },
                    HTTPStatus.BAD_REQUEST
                    if error.code in {"ai_unconfigured", "chat_model_missing"}
                    else HTTPStatus.SERVICE_UNAVAILABLE,
                )
            return
        if route == "/api/plans":
            try:
                response_payload = create_plan(payload, self.plans_path)
                status_code = HTTPStatus.CREATED
            except ValueError as error:
                response_payload = {"error": "invalid_plan", "message": str(error)}
                status_code = HTTPStatus.BAD_REQUEST
            response = json.dumps(response_payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            return
        if route == "/api/searxng":
            if self.library_name != "default":
                self._send_json(
                    {"message": "A separate library cannot manage the shared Docker search container."},
                    HTTPStatus.CONFLICT,
                )
                return
            action = str(payload.get("action") or "").strip()
            try:
                def save_managed_setup(response_payload):
                    config = load_config(self.config_path)
                    backends = self._parse_backends(config.get("enabled_backends"))
                    if "websearch" not in backends:
                        backends.append("websearch")
                    set_searxng_url(str(response_payload["url"]), self.config_path)
                    set_enabled_backends(backends, self.config_path)

                if action in {"setup", "update"}:
                    response_payload = start_searxng_job(
                        action,
                        on_complete=save_managed_setup if action == "setup" else None,
                    )
                    status_code = HTTPStatus.ACCEPTED
                else:
                    response_payload = manage_searxng(
                        action,
                        remove_image=(
                            self._parse_bool(payload.get("remove_image"))
                            if action == "remove"
                            else False
                        ),
                    )
                    status_code = HTTPStatus.OK
                if action == "remove":
                    config = load_config(self.config_path)
                    if config.get("searxng_url") == response_payload.get("removed_url"):
                        backends = [
                            backend
                            for backend in self._parse_backends(
                                config.get("enabled_backends")
                            )
                            if backend != "websearch"
                        ]
                        if not backends:
                            backends = ["arxiv", "openalex", "semanticscholar"]
                        set_searxng_url("", self.config_path)
                        set_enabled_backends(backends, self.config_path)
            except SearxngManagerError as error:
                response_payload = {
                    "state": error.code,
                    "error": error.code,
                    "message": str(error),
                }
                status_code = (
                    HTTPStatus.BAD_REQUEST
                    if error.code == "invalid_action"
                    else HTTPStatus.CONFLICT
                    if error.code in {"container_name_conflict", "job_in_progress"}
                    else HTTPStatus.SERVICE_UNAVAILABLE
                )
            response = json.dumps(response_payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            return

        email = (payload.get("email") or "").strip()
        obsolete_items = obsolete_config_items(load_config(self.config_path))
        if obsolete_items and not self._parse_bool(
            payload.get("confirm_remove_obsolete_config")
        ):
            self._send_json(
                {
                    "error": "obsolete_config_confirmation_required",
                    "message": (
                        "Saving Config will remove settings from older "
                        "Knowte versions."
                    ),
                    "obsolete_config_items": obsolete_items,
                },
                HTTPStatus.CONFLICT,
            )
            return
        api_key_supplied = "semanticscholar_api_key" in payload
        api_key = (payload.get("semanticscholar_api_key") or "").strip()
        requested_backends = payload.get("enabled_backends", self.default_backends)
        if not isinstance(requested_backends, list):
            requested_backends = []
        allowed_backends = set(self.allowed_backends)
        enabled_backends = [
            backend
            for backend in requested_backends
            if isinstance(backend, str) and backend in allowed_backends
        ]
        if not enabled_backends:
            response = json.dumps({"error": "no_search_backends"}).encode("utf-8")
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            return
        max_papers = self._parse_max_papers(str(payload.get("max_papers") or "100"))
        intelligent_max_results = self._parse_bounded_int(
            payload.get("intelligent_max_results"), 20, 1, 100
        )
        config = set_email(email, self.config_path)
        if api_key_supplied:
            config = set_semanticscholar_key(api_key, self.config_path)
        if "searxng_url" in payload:
            config = set_searxng_url(
                str(payload.get("searxng_url") or "").strip(), self.config_path
            )
        if "searxng_proxy" in payload:
            searxng_proxy = str(payload.get("searxng_proxy") or "").strip()
            try:
                if self.library_name == "default":
                    configure_searxng_proxy(searxng_proxy)
            except SearxngManagerError as error:
                self._send_json(
                    {"error": error.code, "message": str(error)}, HTTPStatus.BAD_REQUEST
                )
                return
            config = set_searxng_proxy(searxng_proxy, self.config_path)
        config = set_enabled_backends(enabled_backends, self.config_path)
        config = set_max_papers(max_papers, self.config_path)
        config = set_intelligent_max_results(
            intelligent_max_results, self.config_path
        )
        if "web_ignore_year_filter" in payload:
            config = set_web_ignore_year_filter(
                self._parse_bool(payload.get("web_ignore_year_filter")), self.config_path
            )
        ai_field_names = {
            "ai_model_profiles",
            "ai_role_assignments",
            "ai_provider",
            "ai_custom_recipe",
            "ai_base_url",
            "ai_api_key",
            "ai_chat_model",
            "ai_embedding_model",
            "ai_embedding_separate_connection",
            "ai_enable_thinking",
            "ai_embedding_base_url",
            "ai_embedding_api_key",
            "ai_verify_batch_size",
            "ai_verify_concurrency",
            "ai_timeout_seconds",
            "ai_search_timeout_seconds",
            "ai_stage_timeout_seconds",
            "ai_evidence_source_limit",
            "ai_claim_evidence_limit",
            "ai_claim_comparison_limit",
            "ai_wiki_claim_limit",
            "ai_copilot_context_limit",
            "ai_evidence_request_mode",
            "ai_copilot_instructions",
            "ai_copilot_temperature",
            "ai_copilot_max_tokens",
            "ai_copilot_advanced_parameters",
        }
        if "ai_model_profiles" in payload or "ai_role_assignments" in payload:
            try:
                config = set_ai_model_profiles(
                    payload.get("ai_model_profiles", []),
                    payload.get("ai_role_assignments", {}),
                    self.config_path,
                )
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_ai_profiles", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
                return
        legacy_ai_fields = ai_field_names - {"ai_model_profiles", "ai_role_assignments"}
        if legacy_ai_fields.intersection(payload):
            ai_settings = {
                "ai_provider": payload.get("ai_provider"),
                "ai_custom_recipe": payload.get("ai_custom_recipe"),
                "ai_base_url": payload.get("ai_base_url"),
                "ai_chat_model": payload.get("ai_chat_model"),
                "ai_embedding_model": payload.get("ai_embedding_model"),
                "ai_embedding_separate_connection": self._parse_bool(
                    payload.get("ai_embedding_separate_connection")
                ),
                "ai_enable_thinking": self._parse_bool(
                    payload.get("ai_enable_thinking")
                ),
                "ai_embedding_base_url": payload.get("ai_embedding_base_url"),
                "ai_verify_batch_size": payload.get("ai_verify_batch_size"),
                "ai_verify_concurrency": payload.get("ai_verify_concurrency"),
                "ai_timeout_seconds": payload.get("ai_timeout_seconds"),
                "ai_search_timeout_seconds": payload.get("ai_search_timeout_seconds"),
                "ai_stage_timeout_seconds": payload.get("ai_stage_timeout_seconds"),
                "ai_evidence_source_limit": payload.get("ai_evidence_source_limit"),
                "ai_claim_evidence_limit": payload.get("ai_claim_evidence_limit"),
                "ai_claim_comparison_limit": payload.get("ai_claim_comparison_limit"),
                "ai_wiki_claim_limit": payload.get("ai_wiki_claim_limit"),
                "ai_copilot_context_limit": payload.get("ai_copilot_context_limit"),
                "ai_evidence_request_mode": payload.get("ai_evidence_request_mode"),
                "ai_copilot_instructions": payload.get("ai_copilot_instructions"),
                "ai_copilot_temperature": payload.get("ai_copilot_temperature"),
                "ai_copilot_max_tokens": payload.get("ai_copilot_max_tokens"),
                "ai_copilot_advanced_parameters": payload.get("ai_copilot_advanced_parameters"),
            }
            if "ai_api_key" in payload:
                ai_settings["ai_api_key"] = payload.get("ai_api_key")
            if "ai_embedding_api_key" in payload:
                ai_settings["ai_embedding_api_key"] = payload.get(
                    "ai_embedding_api_key"
                )
            config = set_ai_settings(ai_settings, self.config_path)
        config = remove_obsolete_config_items(self.config_path)
        public_profiles = _public_ai_profiles(config)
        profile_roles = ai_role_assignments(config)
        profile_by_id = {item["id"]: item for item in public_profiles}
        chat_profile = profile_by_id.get(profile_roles.get("intelligent_search", ""), {})
        embedding_profile = profile_by_id.get(profile_roles.get("embedding", ""), {})
        response_payload = {
            "email": config.get("email", ""),
            "semanticscholar_api_key": "",
            "semanticscholar_api_key_configured": bool(
                config.get("semanticscholar_api_key", "")
            ),
            "searxng_url": config.get("searxng_url", ""),
            "searxng_proxy": config.get("searxng_proxy", ""),
            "enabled_backends": self._parse_backends(config.get("enabled_backends")),
            "max_papers": self._parse_max_papers(config.get("max_papers")),
            "intelligent_max_results": self._parse_bounded_int(
                config.get("intelligent_max_results"), 20, 1, 100
            ),
            "default_search_mode": (
                config.get("default_search_mode")
                if config.get("default_search_mode")
                in {"keyword", "intelligent", "import"}
                else "keyword"
            ),
            "search_ai_review": self._parse_bool(config.get("search_ai_review", "true" if config.get("default_search_mode") == "intelligent" else "false")),
            "web_ignore_year_filter": self._parse_bool(
                config.get("web_ignore_year_filter", "true")
            ),
            "ai_model_profiles": public_profiles,
            "ai_role_assignments": profile_roles,
            "ai_provider": config.get("ai_provider", "openai_compatible"),
            "ai_custom_recipe": json.loads(config.get("ai_custom_recipe") or "{}"),
            "ai_base_url": config.get("ai_base_url", ""),
            "ai_api_key": "",
            "ai_api_key_configured": bool(config.get("ai_api_key", "")),
            "ai_chat_model": config.get("ai_chat_model", ""),
            "ai_embedding_model": config.get("ai_embedding_model", ""),
            "ai_embedding_separate_connection": self._parse_bool(
                config.get("ai_embedding_separate_connection")
            ),
            "ai_enable_thinking": (
                self._parse_bool(config.get("ai_enable_thinking"))
                if "ai_enable_thinking" in config
                else False
            ),
            "ai_embedding_base_url": config.get("ai_embedding_base_url", ""),
            "ai_embedding_api_key": "",
            "ai_embedding_api_key_configured": bool(
                config.get("ai_embedding_api_key", "")
            ),
            "ai_verify_batch_size": self._parse_bounded_int(
                config.get("ai_verify_batch_size"), 5, 1, 20
            ),
            "ai_verify_concurrency": self._parse_bounded_int(
                config.get("ai_verify_concurrency"), 1, 1, 8
            ),
            "ai_timeout_seconds": self._parse_bounded_int(
                config.get("ai_timeout_seconds"), 45, 5, 600
            ),
            "ai_search_timeout_seconds": self._parse_bounded_int(
                config.get("ai_search_timeout_seconds")
                or config.get("ai_timeout_seconds"), 45, 5, 600
            ),
            "ai_evidence_source_limit": self._parse_bounded_int(config.get("ai_evidence_source_limit"), 6, 1, 100),
            "ai_claim_evidence_limit": self._parse_bounded_int(config.get("ai_claim_evidence_limit"), 30, 1, 100),
            "ai_claim_comparison_limit": self._parse_bounded_int(config.get("ai_claim_comparison_limit"), 100, 1, 1000),
            "ai_wiki_claim_limit": self._parse_bounded_int(config.get("ai_wiki_claim_limit"), 100, 1, 1000),
            "ai_copilot_context_limit": self._parse_bounded_int(config.get("ai_copilot_context_limit"), 12, 1, 100),
            "ai_evidence_request_mode": config.get("ai_evidence_request_mode", "combined"),
            "ai_stage_timeout_seconds": self._parse_bounded_int(
                config.get("ai_stage_timeout_seconds")
                or config.get("ai_timeout_seconds"), 45, 5, 600
            ),
            "ai_copilot_instructions": config.get("ai_copilot_instructions", ""),
            "ai_copilot_temperature": _copilot_settings(config)[1],
            "ai_copilot_max_tokens": _copilot_settings(config)[2],
            "ai_copilot_advanced_parameters": _copilot_settings(config)[3],
            "ai_copilot_prompt_preview": _copilot_settings(config)[0],
            "ai_copilot_prompt_shared": review_copilot_shared_prompt(),
            "ai_copilot_prompt_previews": {
                "search_strategy": build_search_strategy_prompt(
                    [], str(config.get("ai_copilot_instructions") or "")
                ),
                "evidence_proposal": _evidence_proposal_prompt(),
                "claim_proposal": _claim_proposal_prompt(),
                "wiki_maintenance": _wiki_maintainer_prompt(),
                "project_claim_recommendation": _project_claim_recommendation_prompt(),
                "article_selection": _wiki_article_selection_prompt(),
                "article_writing": _wiki_article_prompt(),
                **review_copilot_stage_prompt_previews(),
            },
            "ai_configured": bool(chat_profile.get("base_url") and chat_profile.get("model")),
            "ai_chat_configured": bool(chat_profile.get("base_url") and chat_profile.get("model")),
            "ai_embedding_configured": bool(
                embedding_profile.get("base_url") and embedding_profile.get("model")
            ),
        }
        response = json.dumps(response_payload).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_PUT(self):
        parsed = urlparse(self.path)
        evidence_match = re.fullmatch(r"/api/evidence/([0-9a-f]+)", parsed.path.rstrip("/"))
        if evidence_match:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                self._send_json(update_evidence(evidence_match.group(1), payload, self.knowledge_db_path))
            except (ValueError, TypeError) as error:
                self._send_json({"message": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        view_match = re.fullmatch(r"/api/views/([0-9a-f]+)", parsed.path.rstrip("/"))
        if view_match:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length > 0 else b""
            try:
                payload = json.loads(body.decode("utf-8")) if body else {}
                self._send_json(
                    update_view(
                        view_match.group(1), payload, self.knowledge_db_path
                    )
                )
            except (json.JSONDecodeError, ValueError) as error:
                self._send_json(
                    {"error": "invalid_view", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        claim_match = re.fullmatch(r"/api/claims/([0-9a-f]+)", parsed.path.rstrip("/"))
        if claim_match:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length > 0 else b""
            try:
                payload = json.loads(body.decode("utf-8")) if body else {}
                if "lifecycle" in payload and "statement" not in payload:
                    claim = set_claim_lifecycle(
                        claim_match.group(1), payload.get("lifecycle"),
                        self.knowledge_db_path,
                    )
                else:
                    claim = revise_claim(
                        claim_match.group(1), payload, self.knowledge_db_path
                    )
                self._send_json(claim)
            except (json.JSONDecodeError, ValueError) as error:
                self._send_json(
                    {"error": "invalid_claim", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        prefix = "/api/plans/"
        if not parsed.path.startswith(prefix):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        plan_id = parsed.path[len(prefix):].strip("/")
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
            plan = update_plan(plan_id, payload, self.plans_path)
            if plan is None:
                response_payload = {"error": "plan_not_found"}
                status_code = HTTPStatus.NOT_FOUND
            else:
                response_payload = plan
                status_code = HTTPStatus.OK
        except (json.JSONDecodeError, ValueError) as error:
            response_payload = {"error": "invalid_plan", "message": str(error)}
            status_code = HTTPStatus.BAD_REQUEST
        response = json.dumps(response_payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        wiki_import_match = re.fullmatch(
            r"/api/wiki/imports/([0-9a-f]+)", parsed.path.rstrip("/")
        )
        if wiki_import_match:
            try:
                discard_wiki_import(wiki_import_match.group(1), self.knowledge_db_path)
                self._send_json({"deleted": True})
            except ValueError:
                self._send_json({"deleted": False}, HTTPStatus.NOT_FOUND)
            return
        wiki_proposal_match = re.fullmatch(
            r"/api/wiki/proposals/([0-9a-f]+)", parsed.path.rstrip("/")
        )
        if wiki_proposal_match:
            deleted = discard_wiki_proposal(
                wiki_proposal_match.group(1), self.knowledge_db_path
            )
            self._send_json(
                {"deleted": deleted},
                HTTPStatus.OK if deleted else HTTPStatus.NOT_FOUND,
            )
            return
        view_match = re.fullmatch(r"/api/views/([0-9a-f]+)", parsed.path.rstrip("/"))
        if view_match:
            deleted = delete_view(view_match.group(1), self.knowledge_db_path)
            self._send_json(
                {"deleted": deleted},
                HTTPStatus.OK if deleted else HTTPStatus.NOT_FOUND,
            )
            return
        companion_match = re.fullmatch(
            r"/api/companion/inbox/([0-9a-f]+)", parsed.path.rstrip("/")
        )
        if companion_match:
            deleted = self.companion_store.remove(companion_match.group(1))
            self._send_json(
                {"deleted": deleted},
                HTTPStatus.OK if deleted else HTTPStatus.NOT_FOUND,
            )
            return
        proposal_match = re.fullmatch(
            r"/api/(?:claim|evidence)-proposals/([0-9a-f]+)|"
            r"/api/project-claim-recommendations/([0-9a-f]+)|"
            r"/api/project-wiki-proposals/([0-9a-f]+)",
            parsed.path.rstrip("/")
        )
        if proposal_match:
            deleted = discard_claim_proposal(
                proposal_match.group(1) or proposal_match.group(2) or proposal_match.group(3),
                self.knowledge_db_path,
            )
            self._send_json(
                {"deleted": deleted},
                HTTPStatus.OK if deleted else HTTPStatus.NOT_FOUND,
            )
            return
        evidence_match = re.fullmatch(r"/api/evidence/([0-9a-f]+)", parsed.path)
        annotation_match = re.fullmatch(
            r"/api/annotations/([0-9a-f]+)", parsed.path
        )
        if evidence_match or annotation_match:
            deleted = (
                delete_evidence(evidence_match.group(1), self.knowledge_db_path)
                if evidence_match
                else delete_annotation(annotation_match.group(1), self.knowledge_db_path)
            )
            self._send_json(
                {"deleted": deleted},
                HTTPStatus.OK if deleted else HTTPStatus.NOT_FOUND,
            )
            return
        prefix = "/api/plans/"
        if not parsed.path.startswith(prefix):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        plan_id = parsed.path[len(prefix):].strip("/")
        deleted = delete_plan(plan_id, self.plans_path)
        response_payload = {"deleted": deleted}
        response = json.dumps(response_payload).encode("utf-8")
        self.send_response(HTTPStatus.OK if deleted else HTTPStatus.NOT_FOUND)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        return

    def do_OPTIONS(self):
        if urlparse(self.path).path.rstrip("/") in {
            "/api/companion/pair", "/api/companion/captures",
            "/api/companion/commit", "/api/companion/options",
        }:
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def end_headers(self):
        if urlparse(self.path).path.rstrip("/") in {
            "/api/companion/pair", "/api/companion/captures",
            "/api/companion/commit", "/api/companion/options",
        }:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header(
                "Access-Control-Allow-Headers", "Authorization, Content-Type"
            )
            self.send_header(
                "Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS"
            )
        super().end_headers()

    def _send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, body: bytes, media_type: str, filename: str):
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _send_local_file(
        self,
        path: Path,
        media_type: str,
        *,
        etag: str = "",
        disposition: str = "inline",
    ):
        size = path.stat().st_size
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(size))
        self.send_header(
            "Content-Disposition",
            f'{disposition}; filename="{path.name}"',
        )
        if etag:
            self.send_header("ETag", f'"{etag}"')
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        with path.open("rb") as source:
            while chunk := source.read(64 * 1024):
                self.wfile.write(chunk)


def create_server(host, port, config_path: Path | None = None, *, library_name="default"):
    web_root = Path(__file__).resolve().parent / "web"
    KnowteHandler.config_path = config_path or CONFIG_PATH
    KnowteHandler.library_name = library_name
    KnowteHandler.plans_path = (
        KnowteHandler.config_path.with_name("plans.json")
        if config_path is not None
        else PLANS_PATH
    )
    KnowteHandler.knowledge_db_path = (
        KnowteHandler.config_path.with_name("knowte.db")
        if config_path is not None
        else KNOWLEDGE_DB_PATH
    )
    KnowteHandler.content_dir = (
        KnowteHandler.config_path.parent / "content"
        if config_path is not None
        else KNOWLEDGE_DB_PATH.parent / "content"
    )
    KnowteHandler.companion_store = CompanionStore(
        KnowteHandler.config_path.parent
    )
    KnowteHandler.debug_replay_query = os.getenv(
        "KNOWTE_DEBUG_REPLAY_QUERY",
        "",
    ).strip()
    KnowteHandler.debug_replay_artifact = os.getenv(
        "KNOWTE_DEBUG_REPLAY_ARTIFACT",
        "",
    ).strip()
    handler = functools.partial(KnowteHandler, directory=str(web_root))
    server = KnowteTCPServer((host, port), handler)
    return server


def prepare_library_config(source: Path, name: str, *, create=True) -> Path:
    """Create a separate library or resolve an existing one without modifying it."""
    if name.lower() == "default":
        if create:
            raise ValueError("The default library already exists; use --mount default or omit both options.")
        return source
    if not re.fullmatch(r"[\w-]{1,64}", name) or name.lower() in {
        "content", "skills", "searxng", "con", "prn", "aux", "nul",
        *{f"com{i}" for i in range(1, 10)}, *{f"lpt{i}" for i in range(1, 10)},
    }:
        raise ValueError("Library NAME must be 1–64 letters, digits, underscores or hyphens, and not a reserved folder/device name.")
    directory = source.parent / name
    if directory.is_symlink():
        raise ValueError("Library directory must not be a symbolic link.")
    target = directory / "config.yml"
    if not create:
        if not target.is_file() or target.is_symlink():
            raise ValueError(f"Library '{name}' was not found or has no regular config.yml; create it with --new {name}.")
        return target
    try:
        directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    except FileExistsError:
        raise ValueError(f"Library directory '{name}' already exists; use --mount {name}.") from None
    skills = source.parent / "skills"
    if skills.is_dir():
        shutil.copytree(skills, directory / "skills")
    if source.is_file():
        shutil.copyfile(source, target)
        target.chmod(0o600)
    else:
        save_config(load_config(source), target)
    return target


def main():
    parser = argparse.ArgumentParser(description="Knowte dev server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--config", default=str(CONFIG_PATH),
                        help="Default library configuration; named libraries live beside it")
    library = parser.add_mutually_exclusive_group()
    library.add_argument("--new", metavar="NAME", help="Create and mount a new named library")
    library.add_argument("--mount", metavar="NAME", help="Mount an existing library (default: default)")
    args = parser.parse_args()
    config_path = Path(args.config).expanduser().resolve()
    name = args.new if args.new is not None else args.mount if args.mount is not None else "default"
    if name.lower() == "default":
        name = "default"
    try:
        config_path = prepare_library_config(config_path, name, create=args.new is not None)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    from . import usage
    usage.USAGE_DIR = config_path.parent
    usage.USAGE_PATH = config_path.parent / "usage.json"
    print(f"Library {name} — data: {config_path.parent}")
    port = args.port if args.port is not None else int(os.getenv("PORT", "7880"))
    with create_server(args.host, port, config_path, library_name=name) as httpd:
        print(f"Knowte server running on http://{args.host}:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
