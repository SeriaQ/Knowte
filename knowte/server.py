from __future__ import annotations

import argparse
import base64
from collections import Counter
import functools
import hashlib
from importlib.metadata import PackageNotFoundError, version as package_version
from importlib.resources import files as resource_files
import json
import os
import re
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
from .ai import AIError
from .capture import CaptureError, capture_source_content
from .companion import CompanionStore
from .exports import build_knowledge_export
from .imports import (
    accept_project_import,
    accept_wiki_import,
    discard_wiki_import,
    stage_project_package_import,
    stage_wiki_package_import,
)
from .intelligent import _client_from_config, _model_name_from_config, intelligent_search
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
    find_related_claims,
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

_CLAIM_PROPOSAL_CAPABILITY = "claim-proposal-v3"
_EVIDENCE_PROPOSAL_CAPABILITY = "evidence-proposal-v2"
_WIKI_PROPOSAL_CAPABILITY = "wiki-maintainer-v1"
_WIKI_ARTICLE_CAPABILITY = "wiki-article-v1"
_PROJECT_CLAIM_RECOMMENDATION_CAPABILITY = "project-claim-recommendation-v1"


def _claim_proposal_prompt() -> str:
    return resource_files("knowte.prompts").joinpath("claim_proposal.md").read_text(
        encoding="utf-8"
    )


def _claim_audit_prompt() -> str:
    return resource_files("knowte.prompts").joinpath("claim_audit.md").read_text(
        encoding="utf-8"
    )


def _evidence_proposal_prompt() -> str:
    return resource_files("knowte.prompts").joinpath("evidence_proposal.md").read_text(
        encoding="utf-8"
    )


def _evidence_document_proposal_prompt() -> str:
    return resource_files("knowte.prompts").joinpath(
        "evidence_document_proposal.md"
    ).read_text(encoding="utf-8")


def _wiki_maintainer_prompt() -> str:
    return resource_files("knowte.prompts").joinpath("wiki_maintainer.md").read_text(
        encoding="utf-8"
    )


def _wiki_article_prompt() -> str:
    return resource_files("knowte.prompts").joinpath("wiki_article.md").read_text(
        encoding="utf-8"
    )


def _wiki_article_selection_prompt() -> str:
    return resource_files("knowte.prompts").joinpath(
        "wiki_article_selection.md"
    ).read_text(encoding="utf-8")


def _project_claim_recommendation_prompt() -> str:
    return resource_files("knowte.prompts").joinpath(
        "project_claim_recommendation.md"
    ).read_text(encoding="utf-8")


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
        valid_url = parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        locator = (doi or arxiv_id or url).casefold()
        if not locator or locator in seen:
            continue
        seen.add(locator)
        title = str(item.get("title") or "").strip()[:500]
        source_type = str(item.get("source_type") or "web").strip().lower()
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
            "pdf_url": "",
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

    def handle_error(self, request, client_address):
        error = sys.exc_info()[1]
        if isinstance(error, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)):
            return
        if isinstance(error, OSError) and getattr(error, "winerror", None) in {10053, 10054}:
            return
        super().handle_error(request, client_address)


class KnowteHandler(SimpleHTTPRequestHandler):
    config_path = CONFIG_PATH
    plans_path = PLANS_PATH
    knowledge_db_path = KNOWLEDGE_DB_PATH
    content_dir = KNOWLEDGE_DB_PATH.parent / "content"
    allowed_backends = ["arxiv", "openalex", "semanticscholar", "websearch"]
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
        if parsed.path.rstrip("/") == "/api/config":
            config = load_config(self.config_path)
            copilot_prompt, copilot_temperature, copilot_max_tokens, copilot_advanced = _copilot_settings(config)
            public_profiles = _public_ai_profiles(config)
            profile_roles = ai_role_assignments(config)
            profile_by_id = {item["id"]: item for item in public_profiles}
            chat_profile = profile_by_id.get(profile_roles.get("intelligent_search", ""), {})
            embedding_profile = profile_by_id.get(profile_roles.get("embedding", ""), {})
            payload = {
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
            "/api/evidence",
            "/api/claims",
            "/api/claim-relations",
            "/api/claim-proposals/generate",
            "/api/claim-audits",
            "/api/claim-audits/preview",
            "/api/evidence-proposals/generate",
            "/api/wiki/proposals/generate",
            "/api/wiki/proposals/edit",
            "/api/wiki/articles/generate",
            "/api/project-articles/generate",
            "/api/project-documents",
            "/api/exports",
            "/api/config/export",
            "/api/project-imports",
            "/api/wiki/imports",
            "/api/tags/entity",
            "/api/tags/batch",
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
        body = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            payload = {}
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
                    config, require_embedding=False, role="wiki", profile_id=profile_id,
                )
                _, temperature, max_tokens, advanced = _copilot_settings(config, "artifact")
                current_pages = (project.get("wiki") or {}).get("graph_state", {}).get("pages", [])
                result = client.chat_json(
                    _wiki_maintainer_prompt(),
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
                    config, require_embedding=False, role="article", profile_id=profile_id,
                )
                _, temperature, max_tokens, advanced = _copilot_settings(config, "artifact")
                result = client.chat_json(
                    _project_claim_recommendation_prompt(),
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
                    config, require_embedding=False, role="claims",
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
                    _claim_audit_prompt(),
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
                    elif judgment in {"contradicts", "scope_difference"}:
                        proposal_payload = {
                            "operation": "create_relation",
                            "subject_claim_id": left_id,
                            "subject_statement": claims_by_id[left_id]["statement"],
                            "object_claim_id": right_id,
                            "object_statement": claims_by_id[right_id]["statement"],
                            "relation_type": "contradicts" if judgment == "contradicts" else "related",
                            "audit_judgment": judgment,
                            "rationale": rationale, "caveats": caveats,
                        }
                    if proposal_payload:
                        proposal_payloads.append(proposal_payload)
                if assessed_pairs != allowed_pairs:
                    raise AIError(
                        "incomplete_claim_audit",
                        "The model omitted one or more Claim pairs. Nothing from this batch was saved.",
                    )
                proposals = [create_claim_proposal(
                    proposal_payload, "claim-audit-v1",
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
                active_claims = [
                    claim for claim in wiki["claims"]
                    if claim.get("lifecycle") == "active"
                ]
                if not active_claims:
                    raise ValueError("The Wiki needs at least one active Claim to organize")
                if len(active_claims) > 200:
                    raise ValueError(
                        "Global Wiki organization currently supports up to 200 active Claims"
                    )
                config = load_config(self.config_path)
                client = _client_from_config(
                    config, require_embedding=False, role="wiki",
                    profile_id=str(payload.get("model_profile_id") or "")[:80],
                )
                _, temperature, max_tokens, advanced = _copilot_settings(config, "views")
                request_payload = json.dumps({
                    "instruction": str(payload.get("instruction") or "")[:2000],
                    "current_wiki": [
                        {
                            "title": page["title"],
                            "summary": page["summary"],
                            "parent_id": page["parent_id"],
                            "page_id": page["id"],
                            "claim_ids": page["claim_ids"],
                        }
                        for page in wiki["pages"]
                    ],
                    "claims": [
                        _wiki_claim_context(claim) for claim in active_claims
                    ],
                }, ensure_ascii=False)
                result = client.chat_json(
                    _wiki_maintainer_prompt(), request_payload,
                    temperature=min(temperature, 0.3),
                    max_tokens=max(3000, max_tokens),
                    extra_parameters=advanced,
                )
                proposal = create_wiki_proposal(
                    result,
                    _WIKI_PROPOSAL_CAPABILITY,
                    _model_name_from_config(
                        config, "wiki",
                        str(payload.get("model_profile_id") or "")[:80],
                    ),
                    {"claim_ids": [claim["id"] for claim in active_claims]},
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
                if len(selected_claims) > 200:
                    raise ValueError("Article generation currently supports up to 200 Project Claims")
                config = load_config(self.config_path)
                client = _client_from_config(
                    config, require_embedding=False, role="article",
                    profile_id=str(payload.get("model_profile_id") or "")[:80],
                )
                _, temperature, max_tokens, advanced = _copilot_settings(config, "views")
                selection = client.chat_json(
                    _wiki_article_selection_prompt(),
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
                ))[:40]
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
                    _wiki_article_prompt(),
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
            web_enabled = "websearch" in enabled
            try:
                config = load_config(self.config_path)
                client = _client_from_config(
                    config, require_embedding=False, role="intelligent_search",
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
                    selected_areas, custom_instructions
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
                            "web": web_enabled,
                        },
                        "areas": selected_areas,
                        "year_from": payload.get("year_from") or None,
                        "year_to": payload.get("year_to") or None,
                        "output": {"actions": [{
                            "query": "concise retrieval query",
                            "target": "academic|web|both",
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
                    target = str(item.get("target") or "both").lower()
                    if target == "academic" and not academic_enabled:
                        continue
                    if target == "web" and not web_enabled:
                        continue
                    if target == "both" and not (academic_enabled and web_enabled):
                        target = "academic" if academic_enabled else "web"
                    if action_query and target in {"academic", "web", "both"}:
                        actions.append({
                            "query": action_query,
                            "target": target,
                            "purpose": str(item.get("purpose") or "").strip()[:500],
                        })
                if not actions:
                    actions = [{"query": intent, "target": "both" if academic_enabled and web_enabled else ("academic" if academic_enabled else "web"), "purpose": "Search the original intent directly."}]
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
        if route == "/api/evidence-proposals/generate":
            source_ids = payload.get("source_ids")
            if not isinstance(source_ids, list):
                source_ids = []
            source_ids = list(dict.fromkeys(str(item) for item in source_ids[:6] if item))
            focus = str(payload.get("focus") or "").strip()[:2000]
            if not source_ids or not focus:
                self._send_json(
                    {"error": "source_focus_required",
                     "message": "Select at least one Source and enter a Focus."},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                workspaces = []
                for source_id in source_ids:
                    workspace = get_source_workspace(source_id, self.knowledge_db_path)
                    if not workspace.get("capture"):
                        captured = capture_source_content(workspace["source"], self.content_dir)
                        workspace = store_capture(
                            source_id, captured, self.knowledge_db_path
                        )
                    workspaces.append(workspace)
                config = load_config(self.config_path)
                client = _client_from_config(
                    config, require_embedding=False, role="evidence",
                    profile_id=str(payload.get("model_profile_id") or "")[:80],
                )
                requested_profile_id = str(payload.get("model_profile_id") or "")[:80]
                evidence_profile = next((
                    item for item in ai_model_profiles(config)
                    if str(item.get("id") or "") == requested_profile_id
                ), None) or ai_profile_for_role(config, "evidence")
                capabilities = set(evidence_profile.get("capabilities", []))
                native_documents = []
                browsable_urls = []
                source_context = []
                for workspace in workspaces:
                    source = workspace["source"]
                    source_url = source.get("url") or source.get("paper_url")
                    input_kind = "capture"
                    if capabilities & {"native_documents", "file_extraction"}:
                        try:
                            raw_path, media_type, _ = get_capture_file(
                                source["id"], self.content_dir, self.knowledge_db_path
                            )
                            if media_type == "application/pdf":
                                native_documents.append({
                                    "data": raw_path.read_bytes(),
                                    "mime_type": media_type,
                                    "filename": f"{source['id']}.pdf",
                                })
                                input_kind = "native_document"
                        except (ValueError, OSError):
                            pass
                    if (
                        input_kind == "capture"
                        and "url_fetch" in capabilities
                        and source_url
                    ):
                        browsable_urls.append(str(source_url))
                        input_kind = "url"
                    segments = []
                    budget = 0
                    if input_kind == "capture":
                        for segment in workspace.get("segments", []):
                            text = str(segment.get("text") or "")
                            if budget + len(text) > 45000:
                                break
                            segments.append({
                                "segment_id": segment["id"],
                                "locator": segment.get("locator", ""),
                                "text": text,
                            })
                            budget += len(text)
                    source_context.append({
                        "source_id": source["id"],
                        "title": source["title"],
                        "url": source_url,
                        "input_kind": input_kind,
                        "segments": segments,
                    })
                request_text = json.dumps(
                    {"focus": focus, "sources": source_context}, ensure_ascii=False
                )
                result = None
                grounded_input_used = bool(native_documents or browsable_urls)
                if grounded_input_used:
                    try:
                        result = client.grounded_json(
                            _evidence_document_proposal_prompt(), request_text,
                            documents=native_documents, urls=browsable_urls,
                            max_tokens=3500,
                        )
                    except AIError as error:
                        # Malformed output is still a completed model response. Return it
                        # to the user instead of silently spending a second request.
                        if error.code == "invalid_model_json":
                            raise
                        result = None
                    except (ValueError, OSError):
                        result = None
                if result is None:
                    # A failed grounded request falls back to locally captured text without
                    # resending native files or assuming the provider visited a URL.
                    fallback_context = []
                    for workspace in workspaces:
                        segments = []
                        budget = 0
                        for segment in workspace.get("segments", []):
                            text = str(segment.get("text") or "")
                            if budget + len(text) > 45000:
                                break
                            segments.append({
                                "segment_id": segment["id"],
                                "locator": segment.get("locator", ""),
                                "text": text,
                            })
                            budget += len(text)
                        fallback_context.append({
                            "source_id": workspace["source"]["id"],
                            "title": workspace["source"]["title"],
                            "url": workspace["source"].get("url")
                            or workspace["source"].get("paper_url"),
                            "segments": segments,
                        })
                    result = client.chat_json(
                        _evidence_proposal_prompt(), json.dumps(
                            {"focus": focus, "sources": fallback_context},
                            ensure_ascii=False,
                        ),
                        temperature=0.1, max_tokens=3500,
                    )
                candidates = result.get("evidence") if isinstance(result, dict) else []
                if not isinstance(candidates, list):
                    candidates = []
                allowed_sources = set(source_ids)
                segment_source = {
                    segment["id"]: workspace["source"]["id"]
                    for workspace in workspaces
                    for segment in workspace.get("segments", [])
                }
                scope = {"kind": "selected_sources", "source_ids": source_ids,
                         "focus": focus}
                proposals = []
                for candidate in candidates[:12]:
                    if not isinstance(candidate, dict):
                        continue
                    segment_id = str(candidate.get("segment_id") or "")
                    source_id = str(candidate.get("source_id") or segment_source.get(segment_id) or "")
                    if source_id in allowed_sources and (
                        not segment_id or segment_source.get(segment_id) != source_id
                    ):
                        workspace = next(
                            item for item in workspaces
                            if item["source"]["id"] == source_id
                        )
                        mapped = _map_document_quote(workspace, candidate.get("quote", ""))
                        if mapped:
                            segment_id, verified_quote = mapped
                            candidate = {
                                **candidate,
                                "segment_id": segment_id,
                                "quote": verified_quote,
                            }
                    if source_id not in allowed_sources or segment_source.get(segment_id) != source_id:
                        continue
                    try:
                        proposals.append(create_evidence_proposal(
                            {**candidate, "source_id": source_id},
                            _EVIDENCE_PROPOSAL_CAPABILITY,
                            _model_name_from_config(
                                config, "evidence",
                                str(payload.get("model_profile_id") or "")[:80],
                            ), scope,
                            self.knowledge_db_path,
                        ))
                    except ValueError:
                        continue
                if not proposals:
                    raise AIError(
                        "no_evidence_proposals",
                        "The model returned no exact quotations that Knowte could verify.",
                    )
                snapshot = client.usage_snapshot()
                latest_usage = record_ai_usage(
                    chat_requests=snapshot.get("chat_requests", 0),
                    chat_tokens=snapshot.get("chat_tokens", 0),
                )
                self._send_json(
                    {"proposals": proposals,
                     "summary": str(result.get("summary") or "")[:1000],
                     "usage": latest_usage}, HTTPStatus.CREATED,
                )
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
            evidence_ids = list(dict.fromkeys(
                str(item) for item in evidence_ids[:30] if item
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
                    config, require_embedding=False, role="claims",
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
                related_claims = find_related_claims(
                    " ".join([
                        focus,
                        *(item["quote"] for item in evidence_context),
                    ]),
                    context_tags, 20, self.knowledge_db_path,
                    list(dict.fromkeys(item["source_id"] for item in evidence_context)),
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
                    _claim_proposal_prompt(), request_payload,
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
                for candidate in (relations if isinstance(relations, list) else [])[:12]:
                    if not isinstance(candidate, dict):
                        continue
                    subject_id = str(candidate.get("subject_claim_id") or "")
                    object_id = str(candidate.get("object_claim_id") or "")
                    relation_type = str(candidate.get("relation_type") or "").lower()
                    if (
                        subject_id not in allowed_claims
                        or object_id not in allowed_claims
                        or subject_id == object_id
                        or relation_type not in {"supports", "contradicts", "related"}
                    ):
                        continue
                    try:
                        proposals.append(create_claim_proposal(
                            {
                                "operation": "create_relation",
                                "subject_claim_id": subject_id,
                                "subject_statement": allowed_claims[subject_id]["statement"],
                                "object_claim_id": object_id,
                                "object_statement": allowed_claims[object_id]["statement"],
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
                )
                self._send_json(
                    {"default_search_mode": config["default_search_mode"]}
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
            selected = [item for item in selected[:12] if isinstance(item, dict)]
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
            for item in evidence[:max(0, 12 - len(selected))]:
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
            for item in selected_claims[:12]:
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
                    config,
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
                    copilot_prompt,
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
        api_key_supplied = "semanticscholar_api_key" in payload
        api_key = (payload.get("semanticscholar_api_key") or "").strip()
        searxng_url = (payload.get("searxng_url") or "").strip()
        searxng_proxy = (payload.get("searxng_proxy") or "").strip()
        web_ignore_year_filter = self._parse_bool(
            payload.get("web_ignore_year_filter", True)
        )
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
        config = set_searxng_url(searxng_url, self.config_path)
        try:
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
        config = set_web_ignore_year_filter(web_ignore_year_filter, self.config_path)
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


def create_server(host, port, config_path: Path | None = None):
    web_root = Path(__file__).resolve().parent / "web"
    KnowteHandler.config_path = config_path or CONFIG_PATH
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


def main():
    parser = argparse.ArgumentParser(description="Knowte dev server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "7880")))
    parser.add_argument("--config", default=str(CONFIG_PATH))
    args = parser.parse_args()

    with create_server(args.host, args.port, Path(args.config)) as httpd:
        print(f"Knowte server running on http://{args.host}:{args.port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
