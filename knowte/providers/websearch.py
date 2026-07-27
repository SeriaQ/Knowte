from __future__ import annotations

import json
import threading
import time
from typing import Dict, List, Optional
from urllib.parse import urlencode, urlparse
from urllib.request import ProxyHandler, Request, build_opener, urlopen

from ..models import Paper

_PAGE_CACHE: Dict[tuple, tuple[float, dict]] = {}
_PAGE_CACHE_LOCK = threading.RLock()
_PAGE_CACHE_TTL = 5 * 60
_PAGE_CACHE_MAX = 128


def _cached_payload(key: tuple) -> dict | None:
    now = time.monotonic()
    with _PAGE_CACHE_LOCK:
        cached = _PAGE_CACHE.get(key)
        if cached is None:
            return None
        created, payload = cached
        if now - created > _PAGE_CACHE_TTL:
            _PAGE_CACHE.pop(key, None)
            return None
        return payload


def _store_payload(key: tuple, payload: dict) -> None:
    with _PAGE_CACHE_LOCK:
        _PAGE_CACHE[key] = (time.monotonic(), payload)
        while len(_PAGE_CACHE) > _PAGE_CACHE_MAX:
            oldest = next(iter(_PAGE_CACHE))
            _PAGE_CACHE.pop(oldest, None)


def search_web(
    query: str,
    limit: int | None = 6,
    base_url: str | None = None,
    time_range: Optional[str] = None,
    language: Optional[str] = None,
    pages: int = 1,
    allow_external: bool = True,
    diagnostics: Optional[Dict[str, object]] = None,
) -> List[Paper]:
    if not query or not base_url:
        return []

    requested_pages = max(1, min(int(pages or 1), 10))
    if diagnostics is not None:
        diagnostics.update(
            {
                "attempted": True,
                "fetched": 0,
                "pages": [],
                "requested_pages": requested_pages,
                "external_requests": 0,
                "cache_hits": 0,
            }
        )

    results = []
    hostname = (urlparse(base_url).hostname or "").lower()
    for page_number in range(1, requested_pages + 1):
        params = {
            "q": query,
            "format": "json",
            "pageno": page_number,
            "safesearch": 1,
            "categories": "general",
        }
        if language and language.strip():
            params["language"] = language.strip()
        if time_range in {"day", "week", "month", "year"}:
            params["time_range"] = time_range
        cache_key = (
            base_url,
            query,
            page_number,
            params.get("language", ""),
            params.get("time_range", ""),
            params["safesearch"],
            params["categories"],
        )
        payload = _cached_payload(cache_key)
        cached = payload is not None
        if cached and diagnostics is not None:
            diagnostics["cache_hits"] += 1
        if payload is None:
            if not allow_external:
                if diagnostics is not None:
                    diagnostics["rate_limited"] = True
                break
            request_url = f"{base_url}?{urlencode(params)}"
            try:
                if diagnostics is not None:
                    diagnostics["external_requests"] += 1
                req = Request(request_url)
                if hostname in {"127.0.0.1", "localhost", "::1"}:
                    response_context = build_opener(ProxyHandler({})).open(
                        req, timeout=10
                    )
                else:
                    response_context = urlopen(req, timeout=10)
                with response_context as response:
                    data = response.read()
            except OSError:
                if diagnostics is not None:
                    diagnostics["error"] = "unavailable"
                return results
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                if diagnostics is not None:
                    diagnostics["error"] = "invalid_response"
                return results
        raw_items = payload.get("results", []) if isinstance(payload, dict) else []
        raw_items = raw_items or []
        if not cached and raw_items and isinstance(payload, dict):
            _store_payload(cache_key, payload)
        if not raw_items and diagnostics is not None:
            diagnostics["empty_response"] = True
        accepted_on_page = 0
        for item in raw_items:
            title = (item.get("title") or "").strip()
            if not title:
                continue
            item_url = item.get("url") or ""
            snippet = (item.get("content") or item.get("title") or "").strip()
            engines = item.get("engines") or []
            source = engines[0] if engines else "Web"
            year = 0
            published = item.get("publishedDate") or ""
            if len(published) >= 4 and published[:4].isdigit():
                year = int(published[:4])

            results.append(
                Paper(
                    id=item_url or title,
                    title=title,
                    authors="Web",
                    year=year,
                    abstract=snippet or "No summary provided.",
                    url=item_url,
                    keywords=[],
                    source=source,
                    paper_url=item_url,
                    result_type="web",
                )
            )
            accepted_on_page += 1
            if limit is not None and len(results) >= max(1, limit):
                break
        if diagnostics is not None:
            diagnostics["pages"].append(
                {
                    "page": page_number,
                    "returned": len(raw_items),
                    "accepted": accepted_on_page,
                    "cached": cached,
                }
            )
        if not raw_items or (limit is not None and len(results) >= max(1, limit)):
            break

    if diagnostics is not None:
        diagnostics["fetched"] = len(results)
        page_diagnostics = diagnostics.get("pages", [])
        diagnostics["last_page_returned"] = (
            page_diagnostics[-1]["returned"] if page_diagnostics else 0
        )
        diagnostics["has_more"] = bool(
            page_diagnostics and page_diagnostics[-1]["returned"] > 0
        )
    return results
