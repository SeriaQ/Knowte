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
import sysconfig
import threading
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import (
    CONFIG_PATH,
    load_config,
    set_default_search_mode,
    set_email,
    set_enabled_backends,
    set_intelligent_max_results,
    set_max_papers,
    set_ai_settings,
    set_semanticscholar_key,
    set_searxng_url,
    set_web_ignore_year_filter,
)
from .ai import AIError
from .capture import CaptureError, capture_source_content
from .companion import CompanionStore
from .intelligent import _client_from_config, intelligent_search
from .knowledge import (
    KNOWLEDGE_DB_PATH,
    create_annotation,
    create_artifact,
    accept_claim_proposal,
    create_claim,
    create_claim_relation,
    create_claim_proposal,
    create_view,
    create_evidence,
    delete_annotation,
    discard_claim_proposal,
    delete_evidence,
    delete_view,
    get_capture_file,
    get_snapshot_file,
    get_source,
    get_source_workspace,
    get_view,
    list_claim_proposals,
    list_claims,
    list_evidence,
    list_artifacts,
    list_tags,
    list_replay_sources,
    list_sources,
    list_views,
    set_entity_tags,
    save_source,
    revise_claim,
    set_claim_lifecycle,
    store_capture,
    update_view,
)
from .plans import PLANS_PATH, create_plan, delete_plan, list_plans, update_plan
from .search import search_papers
from .searxng import (
    SearxngManagerError,
    get_searxng_job,
    get_searxng_status,
    manage_searxng,
    start_searxng_job,
)
from .usage import can_request, get_usage, record_ai_usage, record_request

_INTELLIGENT_PROGRESS = {}
_INTELLIGENT_PROGRESS_LOCK = threading.RLock()

_REVIEW_COPILOT_CORE_PROMPT = """You are the Review Copilot inside Knowte, a local-first system for collecting, examining, and turning information into durable knowledge.

Knowte distinguishes these objects:
- Source: an original paper, web page, document, or other information-bearing work.
- Evidence: a precise text excerpt or visual snapshot grounded in a Source.
- Claim: a knowledge statement synthesized from Evidence; do not treat model inference as established fact.
- Annotation: a user's note attached to an entity.
- Artifact: a purpose-led body of work that links shared knowledge without owning duplicate copies.

Use only the supplied context. Clearly distinguish what a Source or Evidence states from your own inference. Refer to supplied items by their type and index when useful. Be critical about relevance, authority, duplication, uncertainty, and missing coverage. Never claim that you changed the Library, an Artifact, or any other data.

Return a JSON object with an `answer` string and a `recommendations` array. The answer may use Markdown. Each recommendation may contain `source_index`, `decision` (`add`, `skip`, or `inspect`), and `reason`."""

_CLAIM_PROPOSAL_CAPABILITY = "claim-proposal-v1"


def _claim_proposal_prompt() -> str:
    return resource_files("knowte.prompts").joinpath("claim_proposal.md").read_text(
        encoding="utf-8"
    )


def _copilot_settings(config: dict[str, str]) -> tuple[str, float, int, dict]:
    instructions = str(config.get("ai_copilot_instructions") or "").strip()
    prompt = _REVIEW_COPILOT_CORE_PROMPT
    if instructions:
        prompt += "\n\nUser-configured instructions:\n" + instructions
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
            payload = {
                "email": config.get("email", ""),
                "semanticscholar_api_key": "",
                "semanticscholar_api_key_configured": bool(
                    config.get("semanticscholar_api_key", "")
                ),
                "searxng_url": config.get("searxng_url", ""),
                "enabled_backends": self._parse_backends(config.get("enabled_backends")),
                "max_papers": self._parse_max_papers(config.get("max_papers")),
                "intelligent_max_results": self._parse_bounded_int(
                    config.get("intelligent_max_results"), 20, 1, 100
                ),
                "default_search_mode": (
                    config.get("default_search_mode")
                    if config.get("default_search_mode")
                    in {"keyword", "intelligent"}
                    else "keyword"
                ),
                "web_ignore_year_filter": self._parse_bool(
                    config.get("web_ignore_year_filter")
                ),
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
                "ai_copilot_instructions": config.get("ai_copilot_instructions", ""),
                "ai_copilot_temperature": copilot_temperature,
                "ai_copilot_max_tokens": copilot_max_tokens,
                "ai_copilot_advanced_parameters": copilot_advanced,
                "ai_copilot_prompt_preview": copilot_prompt,
                "ai_configured": bool(
                    config.get("ai_base_url") and config.get("ai_chat_model")
                ),
                "ai_chat_configured": bool(
                    config.get("ai_base_url") and config.get("ai_chat_model")
                ),
                "ai_embedding_configured": bool(
                    config.get("ai_embedding_model")
                    and (
                        config.get("ai_embedding_base_url")
                        if self._parse_bool(
                            config.get("ai_embedding_separate_connection")
                        )
                        else config.get("ai_base_url")
                    )
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
        if parsed.path.rstrip("/") == "/api/views":
            self._send_json({"views": list_views(self.knowledge_db_path)})
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
                    config.get("web_ignore_year_filter")
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
                and not self._parse_bool(config.get("web_ignore_year_filter"))
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
        if route not in {
            "/api/config",
            "/api/config/default-search-mode",
            "/api/searxng",
            "/api/plans",
            "/api/artifacts",
            "/api/library/sources",
            "/api/library/sources/batch",
            "/api/review/chat",
            "/api/evidence",
            "/api/claims",
            "/api/claim-relations",
            "/api/claim-proposals/generate",
            "/api/views",
            "/api/tags/entity",
            "/api/annotations",
            "/api/companion/pairing",
            "/api/companion/pair",
            "/api/companion/captures",
            "/api/companion/commit",
            "/api/companion/theme",
        } and not capture_match and not companion_confirm_match and not proposal_accept_match:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            payload = {}
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
        if route == "/api/views":
            try:
                self._send_json(
                    create_view(payload, self.knowledge_db_path),
                    HTTPStatus.CREATED,
                )
            except ValueError as error:
                self._send_json(
                    {"error": "invalid_view", "message": str(error)},
                    HTTPStatus.BAD_REQUEST,
                )
            return
        if route == "/api/claim-proposals/generate":
            evidence_ids = payload.get("evidence_ids")
            if not isinstance(evidence_ids, list):
                evidence_ids = []
            evidence_ids = list(dict.fromkeys(
                str(item) for item in evidence_ids[:12] if item
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
                client = _client_from_config(config, require_embedding=False)
                artifact = payload.get("artifact")
                artifact = artifact if isinstance(artifact, dict) else {}
                scope = {
                    "kind": "selected_evidence",
                    "evidence_ids": evidence_ids,
                    "artifact_id": str(artifact.get("id") or ""),
                    "artifact_title": str(artifact.get("title") or "")[:300],
                }
                evidence_context = [
                    {
                        "evidence_id": item["id"],
                        "type": item["evidence_type"],
                        "source_id": item["source_id"],
                        "source_title": item["source_title"],
                        "locator": item["locator"],
                        "quote": item["quote"][:5000],
                        "tags": [tag["name"] for tag in item.get("tags", [])],
                    }
                    for item in evidence_items
                ]
                request_payload = json.dumps(
                    {
                        "scope": scope,
                        "artifact": {
                            "title": str(artifact.get("title") or "")[:300],
                            "purpose": str(artifact.get("purpose") or "")[:2000],
                        },
                        "evidence": evidence_context,
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
                    try:
                        proposals.append(create_claim_proposal(
                            candidate,
                            _CLAIM_PROPOSAL_CAPABILITY,
                            config.get("ai_chat_model", ""),
                            scope,
                            self.knowledge_db_path,
                        ))
                    except ValueError:
                        continue
                if not proposals:
                    raise AIError(
                        "no_claim_proposals",
                        "The model returned no valid Claim proposals.",
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
                        "usage": latest_usage,
                    },
                    HTTPStatus.CREATED,
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
                )
                copilot_prompt, copilot_temperature, copilot_max_tokens, copilot_advanced = _copilot_settings(config)
                review_input = json.dumps(
                    {
                        "question": question,
                        "review_context": review_context,
                        "active_artifact": {
                            "title": str(artifact_context.get("title") or "")[:300],
                            "purpose": str(artifact_context.get("purpose") or "")[:1200],
                        },
                        "selected_sources": source_context,
                        "selected_evidence": evidence_context,
                        "selected_claims": claim_context,
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
                self._send_json(
                    {
                        "answer": str(review.get("answer") or "").strip(),
                        "recommendations": (
                            review.get("recommendations")
                            if isinstance(review.get("recommendations"), list)
                            else []
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
        web_ignore_year_filter = self._parse_bool(
            payload.get("web_ignore_year_filter", False)
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
        config = set_enabled_backends(enabled_backends, self.config_path)
        config = set_max_papers(max_papers, self.config_path)
        config = set_intelligent_max_results(
            intelligent_max_results, self.config_path
        )
        config = set_web_ignore_year_filter(web_ignore_year_filter, self.config_path)
        ai_field_names = {
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
            "ai_copilot_instructions",
            "ai_copilot_temperature",
            "ai_copilot_max_tokens",
            "ai_copilot_advanced_parameters",
        }
        if ai_field_names.intersection(payload):
            ai_settings = {
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
        response_payload = {
            "email": config.get("email", ""),
            "semanticscholar_api_key": "",
            "semanticscholar_api_key_configured": bool(
                config.get("semanticscholar_api_key", "")
            ),
            "searxng_url": config.get("searxng_url", ""),
            "enabled_backends": self._parse_backends(config.get("enabled_backends")),
            "max_papers": self._parse_max_papers(config.get("max_papers")),
            "intelligent_max_results": self._parse_bounded_int(
                config.get("intelligent_max_results"), 20, 1, 100
            ),
            "default_search_mode": (
                config.get("default_search_mode")
                if config.get("default_search_mode")
                in {"keyword", "intelligent"}
                else "keyword"
            ),
            "web_ignore_year_filter": self._parse_bool(
                config.get("web_ignore_year_filter")
            ),
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
            "ai_copilot_instructions": config.get("ai_copilot_instructions", ""),
            "ai_copilot_temperature": _copilot_settings(config)[1],
            "ai_copilot_max_tokens": _copilot_settings(config)[2],
            "ai_copilot_advanced_parameters": _copilot_settings(config)[3],
            "ai_copilot_prompt_preview": _copilot_settings(config)[0],
            "ai_configured": bool(
                config.get("ai_base_url") and config.get("ai_chat_model")
            ),
            "ai_chat_configured": bool(
                config.get("ai_base_url") and config.get("ai_chat_model")
            ),
            "ai_embedding_configured": bool(
                config.get("ai_embedding_model")
                and (
                    config.get("ai_embedding_base_url")
                    if self._parse_bool(
                        config.get("ai_embedding_separate_connection")
                    )
                    else config.get("ai_base_url")
                )
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
            r"/api/claim-proposals/([0-9a-f]+)", parsed.path.rstrip("/")
        )
        if proposal_match:
            deleted = discard_claim_proposal(
                proposal_match.group(1), self.knowledge_db_path
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
