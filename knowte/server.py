from __future__ import annotations

import argparse
from collections import Counter
import functools
import json
import os
import socketserver
import threading
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import (
    CONFIG_PATH,
    load_config,
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
from .intelligent import intelligent_search
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
    allowed_backends = ["arxiv", "openalex", "semanticscholar", "websearch"]
    default_backends = ["arxiv", "openalex", "semanticscholar"]

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

    def do_GET(self):
        parsed = urlparse(self.path)
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
        if route not in {"/api/config", "/api/searxng", "/api/plans"}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            payload = {}
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

    def _send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(host, port, config_path: Path | None = None):
    web_root = Path(__file__).resolve().parent / "web"
    KnowteHandler.config_path = config_path or CONFIG_PATH
    KnowteHandler.plans_path = (
        KnowteHandler.config_path.with_name("plans.json")
        if config_path is not None
        else PLANS_PATH
    )
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
