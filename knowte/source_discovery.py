from __future__ import annotations

import json
import re
import hashlib
import time
import threading
from copy import deepcopy
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote, urlencode, urlparse
from urllib.error import HTTPError
from urllib.request import Request, urlopen


GRAPH_BASE_URL = "https://api.semanticscholar.org/graph/v1"
RECOMMENDATIONS_URL = "https://api.semanticscholar.org/recommendations/v1/papers/"
PAPER_FIELDS = (
    "title,authors,year,abstract,externalIds,url,fieldsOfStudy,openAccessPdf,"
    "citationCount,referenceCount"
)
_CACHE: dict[tuple, tuple[float, dict]] = {}
_COOLDOWN: dict[str, float] = {}
_REQUEST_LOCK = threading.Lock()


class DiscoveryUnavailable(ValueError):
    def __init__(self, code: str, retry_after: int = 0):
        super().__init__(code)
        self.code = code
        self.retry_after = retry_after


def _retrieval(request, api_key, list_key, counters):
    """Cache provider responses, not model decisions; serialize cooldown checks."""
    credential = hashlib.sha256(api_key.encode()).hexdigest()
    url = request if isinstance(request, str) else request.full_url
    body = None if isinstance(request, str) else request.data
    key = (credential, url, body)
    with _REQUEST_LOCK:
        now = time.time()
        for expired in [item for item, (until, _) in _CACHE.items() if until <= now]:
            del _CACHE[expired]
        cached = _CACHE.get(key)
        if cached:
            counters["cache_hits"] += 1
            payload = deepcopy(cached[1])
        else:
            remaining = _COOLDOWN.get(credential, 0) - now
            if remaining > 0:
                raise DiscoveryUnavailable("rate_limited", int(remaining) + 1)
            _COOLDOWN.pop(credential, None)
            counters["requests"] += 1
            try:
                payload = _request_json(request, api_key)
            except HTTPError as error:
                if error.code == 429:
                    value = (error.headers or {}).get("Retry-After", "60")
                    try:
                        delay = float(value)
                    except ValueError:
                        try:
                            delay = parsedate_to_datetime(value).timestamp() - now
                        except (ValueError, TypeError, OverflowError):
                            delay = 60
                    delay = max(1, min(3600, delay))
                    _COOLDOWN[credential] = time.time() + delay
                    raise DiscoveryUnavailable("rate_limited", int(delay) + 1) from error
                raise
            restricted = payload.get(list_key) is None and "elided by the publisher" in json.dumps(payload)
            if not isinstance(payload.get(list_key), list) and not restricted:
                raise ValueError("Missing paper list")
            if len(_CACHE) >= 128:
                del _CACHE[next(iter(_CACHE))]
            _CACHE[key] = (time.time() + 900, deepcopy(payload))
        if payload.get(list_key) is None:
            raise DiscoveryUnavailable("provider_restricted")
        return payload


def semantic_scholar_id(source: dict[str, Any]) -> str:
    doi_url = str(source.get("doi_url") or "").strip()
    if doi_url:
        doi = urlparse(doi_url).path.strip("/")
        if doi:
            arxiv_doi = re.fullmatch(r"10\.48550/arxiv\.(\d{4}\.\d{4,5})(?:v\d+)?", doi, re.I)
            if arxiv_doi:
                return f"ARXIV:{arxiv_doi.group(1)}"
            return f"DOI:{doi}"
    for value in (source.get("paper_url"), source.get("url")):
        url = str(value or "").strip()
        arxiv = re.search(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})(?:v\d+)?", url)
        if arxiv:
            return f"ARXIV:{arxiv.group(1)}"
        semantic = re.search(r"semanticscholar\.org/paper/(?:[^/]+/)?([0-9a-f]{40})", url, re.I)
        if semantic:
            return semantic.group(1)
    canonical = str(source.get("canonical_key") or "")
    if canonical.startswith("doi:"):
        return f"DOI:{canonical[4:]}"
    return ""


def _request_json(
    request: Request | str,
    api_key: str = "",
    timeout: int = 15,
) -> dict[str, Any]:
    if isinstance(request, str):
        request = Request(request)
    request.add_header("User-Agent", "Knowte")
    if api_key:
        request.add_header("x-api-key", api_key)
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read())
    if not isinstance(payload, dict):
        raise ValueError("Invalid provider response")
    return payload


def _paper_candidate(paper: dict[str, Any]) -> dict[str, Any] | None:
    title = str(paper.get("title") or "").strip()
    if not title:
        return None
    external_ids = paper.get("externalIds") or {}
    doi = str(external_ids.get("DOI") or "").strip()
    arxiv_id = str(external_ids.get("ArXiv") or "").strip()
    paper_id = str(paper.get("paperId") or doi or arxiv_id or title).strip()
    url = str(paper.get("url") or "").strip()
    return {
        "id": paper_id,
        "title": title,
        "authors": ", ".join(
            str(author.get("name") or "").strip()
            for author in paper.get("authors", [])
            if isinstance(author, dict) and author.get("name")
        ) or "Unknown",
        "year": paper.get("year") or 0,
        "abstract": str(paper.get("abstract") or "").strip() or "No abstract provided.",
        "url": url,
        "paper_url": url,
        "pdf_url": str((paper.get("openAccessPdf") or {}).get("url") or ""),
        "doi_url": f"https://doi.org/{doi}" if doi else "",
        "arxiv_id": arxiv_id,
        "keywords": [str(item) for item in (paper.get("fieldsOfStudy") or []) if item],
        "source": "Semantic Scholar",
        "result_type": "paper",
        "citation_count": paper.get("citationCount") or 0,
        "reference_count": paper.get("referenceCount") or 0,
        "discovery_links": [],
        "citation_contexts": [],
        "citation_intents": [],
    }


def _candidate_key(candidate: dict[str, Any]) -> str:
    identifier = semantic_scholar_id(candidate)
    if identifier.startswith("ARXIV:"):
        return identifier.casefold()
    if candidate.get("doi_url"):
        return str(candidate["doi_url"]).casefold()
    if candidate.get("arxiv_id"):
        return f"arxiv:{candidate['arxiv_id']}".casefold()
    return str(candidate.get("id") or candidate.get("title") or "").casefold()


def discover_related_papers(
    seeds: list[dict[str, Any]],
    api_key: str = "",
    per_lane: int = 40,
    candidate_limit: int = 160,
) -> dict[str, Any]:
    resolved = [(source, semantic_scholar_id(source)) for source in seeds]
    resolved = [(source, identifier) for source, identifier in resolved if identifier]
    if not resolved:
        raise ValueError("Selected Sources need a DOI, arXiv ID, or Semantic Scholar ID")

    candidates: dict[str, dict[str, Any]] = {}
    counters = {"requests": 0, "cache_hits": 0}
    successful_requests = 0
    failures: list[dict[str, Any]] = []
    truncated_paths: list[str] = []

    def failure(lane: str, seed_id: str, error: Exception) -> None:
        status = error.code if isinstance(error, HTTPError) else None
        code = (error.code if isinstance(error, DiscoveryUnavailable) else
                "rate_limited" if status == 429 else
                "paper_not_found" if status == 404 else
                "http_error" if status else
                "invalid_response" if isinstance(error, ValueError) else
                "timeout" if isinstance(error, TimeoutError) else "network_error")
        if code == "rate_limited":
            status = 429
        failures.append({"lane": lane, "seed_id": seed_id, "code": code, "status": status,
                         "retry_after": getattr(error, "retry_after", 0)})

    def merge(raw: dict[str, Any], link: dict[str, Any]) -> None:
        candidate = _paper_candidate(raw)
        if candidate is None:
            return
        key = _candidate_key(candidate)
        existing = candidates.get(key)
        if existing is None:
            existing = candidate
            candidates[key] = existing
        if link not in existing["discovery_links"]:
            existing["discovery_links"].append(link)
        for context in link.get("contexts", []):
            if context and context not in existing["citation_contexts"]:
                existing["citation_contexts"].append(context)
        for intent in link.get("intents", []):
            if intent and intent not in existing["citation_intents"]:
                existing["citation_intents"].append(intent)

    limit = max(1, min(int(per_lane), 100))
    for seed, identifier in resolved:
        encoded = quote(identifier, safe="")
        for lane, nested_key in (("reference", "citedPaper"), ("citation", "citingPaper")):
            url = (
                f"{GRAPH_BASE_URL}/paper/{encoded}/{lane}s?"
                + urlencode({
                    "fields": f"contexts,intents,isInfluential,{PAPER_FIELDS}",
                    "limit": limit,
                })
            )
            try:
                payload = _retrieval(url, api_key, "data", counters)
                successful_requests += 1
                if payload.get("next") is not None:
                    truncated_paths.append(lane)
            except (OSError, ValueError) as error:
                failure(lane, str(seed.get("id") or ""), error)
                continue
            for item in payload.get("data", []) or []:
                if not isinstance(item, dict) or not isinstance(item.get(nested_key), dict):
                    continue
                merge(item[nested_key], {
                    "kind": lane,
                    "seed_id": str(seed.get("id") or ""),
                    "seed_title": str(seed.get("title") or ""),
                    "contexts": [str(value)[:1200] for value in (item.get("contexts") or [])[:3]],
                    "intents": [str(value) for value in (item.get("intents") or [])[:6]],
                    "influential": bool(item.get("isInfluential")),
                })

    seed_ids = [identifier for _, identifier in resolved]
    if seed_ids:
        body = json.dumps({"positivePaperIds": seed_ids, "negativePaperIds": []}).encode("utf-8")
        request = Request(
            RECOMMENDATIONS_URL + "?" + urlencode({"limit": min(80, candidate_limit), "fields": PAPER_FIELDS}),
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            payload = _retrieval(request, api_key, "recommendedPapers", counters)
            successful_requests += 1
            for paper in payload.get("recommendedPapers", []) or []:
                if isinstance(paper, dict):
                    merge(paper, {"kind": "recommendation", "seed_id": "", "seed_title": ""})
        except (OSError, ValueError) as error:
            failure("recommendation", "", error)

    seed_keys = {_candidate_key({
        "id": identifier,
        "title": seed.get("title"),
        "doi_url": seed.get("doi_url"),
        "arxiv_id": re.search(r"(\d{4}\.\d{4,5})", identifier).group(1)
        if identifier.startswith("ARXIV:") else "",
    }) for seed, identifier in resolved}
    output = [item for key, item in candidates.items() if key not in seed_keys]
    for item in output:
        lane_names = {link["kind"] for link in item["discovery_links"]}
        labels = []
        if "reference" in lane_names:
            labels.append("Referenced by a Seed")
        if "citation" in lane_names:
            labels.append("Cites a Seed")
        if "recommendation" in lane_names:
            labels.append("Graph recommendation")
        item["discovery_path"] = " · ".join(labels)
        item["seed_coverage"] = len({
            link.get("seed_id") for link in item["discovery_links"] if link.get("seed_id")
        })
    output.sort(key=lambda item: (
        item.get("seed_coverage", 0),
        any(link.get("influential") for link in item["discovery_links"]),
        len(item["discovery_links"]),
        item.get("citation_count", 0),
    ), reverse=True)
    return {
        "candidates": output[:candidate_limit],
        **counters,
        "path_count": len(resolved) * 2 + 1,
        "successful_requests": successful_requests,
        "retrieval_failures": failures,
        "truncated_paths": sorted(set(truncated_paths)),
        "resolved_seed_count": len(resolved),
        "unresolved_seed_count": len(seeds) - len(resolved),
    }
