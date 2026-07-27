from __future__ import annotations

import hashlib
import math
import re
import threading
import time
from dataclasses import replace
from typing import Dict, Iterable, List

from .areas import AREAS
from .models import Paper
from .providers.arxiv import search_arxiv
from .providers.openalex import search_openalex
from .providers.semanticscholar import search_semanticscholar
from .providers.websearch import search_web

_ACADEMIC_CACHE: Dict[tuple, tuple[float, Dict[str, List[Paper]]]] = {}
_ACADEMIC_CACHE_LOCK = threading.RLock()
_ACADEMIC_CACHE_TTL = 5 * 60
_ACADEMIC_CACHE_MAX = 64


def _credential_fingerprint(value: str | None) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _academic_cache_key(
    query: str,
    academic_sources: List[str],
    area_codes: List[str],
    email: str | None,
    semanticscholar_key: str | None,
    year_from: int | None,
    year_to: int | None,
) -> tuple:
    return (
        query.casefold(),
        tuple(academic_sources),
        tuple(sorted(area_codes)),
        (email or "").strip().casefold(),
        _credential_fingerprint(semanticscholar_key),
        year_from,
        year_to,
    )


def _cached_academic_pools(key: tuple) -> Dict[str, List[Paper]] | None:
    now = time.monotonic()
    with _ACADEMIC_CACHE_LOCK:
        cached = _ACADEMIC_CACHE.get(key)
        if cached is None:
            return None
        created, pools = cached
        if now - created > _ACADEMIC_CACHE_TTL:
            _ACADEMIC_CACHE.pop(key, None)
            return None
        return {source: list(papers) for source, papers in pools.items()}


def _store_academic_pools(key: tuple, pools: Dict[str, List[Paper]]) -> None:
    with _ACADEMIC_CACHE_LOCK:
        _ACADEMIC_CACHE[key] = (
            time.monotonic(),
            {source: list(papers) for source, papers in pools.items()},
        )
        while len(_ACADEMIC_CACHE) > _ACADEMIC_CACHE_MAX:
            oldest = next(iter(_ACADEMIC_CACHE))
            _ACADEMIC_CACHE.pop(oldest, None)


def _matches(query: str, paper: Paper) -> bool:
    tokens = [token for token in query.lower().split() if token]
    haystack = " ".join([paper.title, paper.abstract, " ".join(paper.keywords)]).lower()
    return all(token in haystack for token in tokens)


def _matches_year(paper: Paper, year_from: int | None, year_to: int | None) -> bool:
    if year_from is None and year_to is None:
        return True
    if not paper.year:
        return False
    if year_from is not None and paper.year < year_from:
        return False
    if year_to is not None and paper.year > year_to:
        return False
    return True


def _dedupe(papers: Iterable[Paper]) -> List[Paper]:
    seen = set()
    deduped = []
    for paper in papers:
        key = paper.id or paper.title.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(paper)
    return deduped


def _paper_key(paper: Paper) -> str:
    normalized_title = re.sub(r"[^a-z0-9]+", " ", paper.title.lower()).strip()
    if normalized_title:
        return f"title:{normalized_title}"
    return f"id:{paper.id.lower()}"


def _merge_academic_links(
    pools: Dict[str, List[Paper]], academic_sources: List[str]
) -> Dict[str, List[Paper]]:
    links: Dict[str, Dict[str, str]] = {}
    for source in academic_sources:
        for paper in pools.get(source, []):
            key = _paper_key(paper)
            merged = links.setdefault(
                key, {"paper_url": "", "pdf_url": "", "doi_url": ""}
            )
            for field in ("paper_url", "pdf_url", "doi_url"):
                if not merged[field]:
                    merged[field] = getattr(paper, field, "") or ""

    merged_pools: Dict[str, List[Paper]] = {}
    for source in academic_sources:
        merged_pools[source] = []
        for paper in pools.get(source, []):
            merged = links[_paper_key(paper)]
            paper_url = merged["paper_url"] or paper.paper_url or paper.url
            merged_pools[source].append(
                replace(
                    paper,
                    paper_url=paper_url,
                    pdf_url=merged["pdf_url"] or paper.pdf_url,
                    doi_url=merged["doi_url"] or paper.doi_url,
                )
            )
    return merged_pools


def _source_weights(academic_sources: List[str], include_web: bool) -> Dict[str, int]:
    count = len(academic_sources)
    if not include_web:
        return {source: 1 for source in academic_sources}
    if count == 3:
        academic_weight, web_weight = 3, 1
    elif count == 2:
        academic_weight, web_weight = 4, 2
    elif count == 1:
        academic_weight, web_weight = 7, 3
    else:
        return {"websearch": 1}
    return {
        **{source: academic_weight for source in academic_sources},
        "websearch": web_weight,
    }


def _allocate_quotas(total: int, weights: Dict[str, int]) -> Dict[str, int]:
    if total <= 0 or not weights:
        return {source: 0 for source in weights}
    weight_total = sum(weights.values())
    raw = {
        source: total * weight / weight_total for source, weight in weights.items()
    }
    quotas = {source: math.floor(value) for source, value in raw.items()}
    remaining = total - sum(quotas.values())
    order = sorted(
        weights,
        key=lambda source: (-(raw[source] - quotas[source]), list(weights).index(source)),
    )
    for source in order[:remaining]:
        quotas[source] += 1
    return quotas


def _weighted_slots(quotas: Dict[str, int]) -> List[str]:
    slots = []
    for source, quota in quotas.items():
        if quota <= 0:
            continue
        slots.extend(
            ((index + 1) / quota, source, index)
            for index in range(quota)
        )
    return [source for _, source, _ in sorted(slots)]


def _take_candidate(
    pool: List[Paper], positions: Dict[str, int], source: str, seen: set
) -> Paper | None:
    position = positions.get(source, 0)
    while position < len(pool):
        candidate = pool[position]
        position += 1
        key = _paper_key(candidate)
        if key in seen:
            continue
        positions[source] = position
        seen.add(key)
        return candidate
    positions[source] = position
    return None


def _select_weighted_results(
    pools: Dict[str, List[Paper]],
    quotas: Dict[str, int],
    limit: int,
    academic_sources: List[str],
) -> tuple[List[Paper], Dict[str, int]]:
    selected = []
    selected_counts = {source: 0 for source in pools}
    positions: Dict[str, int] = {}
    seen = set()
    for source in _weighted_slots(quotas):
        candidate = _take_candidate(pools.get(source, []), positions, source, seen)
        if candidate is None:
            continue
        selected.append(candidate)
        selected_counts[source] += 1

    fill_order = [*academic_sources]
    while len(selected) < limit and fill_order:
        added = False
        for source in fill_order:
            if len(selected) >= limit:
                break
            candidate = _take_candidate(
                pools.get(source, []), positions, source, seen
            )
            if candidate is not None:
                selected.append(candidate)
                selected_counts[source] += 1
                added = True
        if not added:
            break
    if len(selected) < limit and "websearch" in pools:
        while len(selected) < limit:
            candidate = _take_candidate(
                pools["websearch"], positions, "websearch", seen
            )
            if candidate is None:
                break
            selected.append(candidate)
            selected_counts["websearch"] += 1
    return selected, selected_counts


def _prepare_area_terms(area_codes: List[str]):
    arxiv_cats: List[str] = []
    openalex_concepts: List[str] = []
    s2_fields: List[str] = []
    boosts: List[str] = []
    for code in area_codes:
        area = AREAS.get(code)
        if not area:
            continue
        arxiv_cats.extend(area.get("arxiv", []))
        openalex_concepts.extend(area.get("openalex", []))
        s2_fields.extend(area.get("semanticscholar", []))
        boosts.extend(area.get("boost", []))
    return (
        list(dict.fromkeys(arxiv_cats)),
        list(dict.fromkeys(openalex_concepts)),
        list(dict.fromkeys(s2_fields)),
        list(dict.fromkeys(boosts)),
    )


def search_papers(
    query: str,
    limit: int = 6,
    email: str | None = None,
    areas: List[str] | None = None,
    semanticscholar_key: str | None = None,
    backends: List[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    searxng_url: str | None = None,
    web_time_range: str | None = None,
    language: str | None = None,
    web_ignore_year_filter: bool = False,
    web_pages: int = 1,
    allow_paper_external: bool = True,
    allow_web_external: bool = True,
    diagnostics: Dict[str, object] | None = None,
) -> List[dict]:
    query = (query or "").strip()
    if not query:
        return []

    arxiv_cats, openalex_concepts, s2_fields, boosts = _prepare_area_terms(areas or [])
    requested_backends = backends or [
        "arxiv",
        "openalex",
        "semanticscholar",
        "websearch",
    ]
    enabled = set(requested_backends)
    academic_sources = [
        source
        for source in ("arxiv", "openalex", "semanticscholar")
        if source in enabled
    ]
    include_web = "websearch" in enabled and bool(searxng_url)

    fetch_limit = min(limit, 100)
    academic_cache_key = _academic_cache_key(
        query,
        academic_sources,
        areas or [],
        email,
        semanticscholar_key,
        year_from,
        year_to,
    )
    academic_results = _cached_academic_pools(academic_cache_key)
    academic_cache_hit = academic_results is not None
    academic_external_request = False
    academic_rate_limited = False
    if academic_results is None:
        academic_results = {source: [] for source in academic_sources}
        if academic_sources and allow_paper_external:
            academic_external_request = True
            if "arxiv" in enabled:
                academic_results["arxiv"] = search_arxiv(
                    query,
                    limit=fetch_limit,
                    categories=arxiv_cats,
                    year_from=year_from,
                    year_to=year_to,
                )
            if "openalex" in enabled:
                academic_results["openalex"] = search_openalex(
                    query,
                    email=email,
                    limit=fetch_limit,
                    concepts=openalex_concepts,
                    query_boosts=boosts,
                    year_from=year_from,
                    year_to=year_to,
                )
            if "semanticscholar" in enabled:
                academic_results["semanticscholar"] = search_semanticscholar(
                    query,
                    limit=fetch_limit,
                    fields=s2_fields,
                    api_key=semanticscholar_key,
                    query_boosts=boosts,
                    year_from=year_from,
                    year_to=year_to,
                )
            _store_academic_pools(academic_cache_key, academic_results)
        elif academic_sources:
            academic_rate_limited = True

    web_results = []
    web_diagnostics: Dict[str, object] = {}
    if "websearch" in enabled and searxng_url:
        web_results = search_web(
            query,
            limit=None,
            base_url=searxng_url,
            time_range=web_time_range,
            language=language,
            pages=web_pages,
            allow_external=allow_web_external,
            diagnostics=web_diagnostics,
        )
    pools = {
        "arxiv": [
            paper
            for paper in academic_results.get("arxiv", [])
            if _matches(query, paper) and _matches_year(paper, year_from, year_to)
        ],
        "openalex": [
            paper
            for paper in academic_results.get("openalex", [])
            if _matches(query, paper) and _matches_year(paper, year_from, year_to)
        ],
        "semanticscholar": [
            paper
            for paper in academic_results.get("semanticscholar", [])
            if _matches(query, paper) and _matches_year(paper, year_from, year_to)
        ],
    }
    pools = {source: pools[source] for source in academic_sources}
    pools = _merge_academic_links(pools, academic_sources)
    filtered_web = [
        paper
        for paper in web_results
        if _matches(query, paper)
        and (
            web_ignore_year_filter
            or _matches_year(paper, year_from, year_to)
        )
    ]
    if include_web:
        pools["websearch"] = filtered_web

    weights = _source_weights(academic_sources, include_web)
    if not academic_sources and include_web:
        selected = _dedupe(filtered_web)
        selected_counts = {"websearch": len(selected)}
        quotas = {"websearch": len(selected)}
    else:
        quotas = _allocate_quotas(limit, weights)
        selected, selected_counts = _select_weighted_results(
            pools, quotas, limit, academic_sources
        )
    if diagnostics is not None and "websearch" in enabled:
        web_diagnostics["accepted"] = len(filtered_web)
        diagnostics["websearch"] = web_diagnostics
    if diagnostics is not None:
        diagnostics["academic"] = {
            "cache_hit": academic_cache_hit,
            "external_request": academic_external_request,
            "rate_limited": academic_rate_limited,
            "fetch_limit": fetch_limit if academic_external_request else 0,
            "available": {
                source: len(pools.get(source, [])) for source in academic_sources
            },
        }
        diagnostics["allocation"] = {
            "weights": weights,
            "quotas": quotas,
            "available": {source: len(pool) for source, pool in pools.items()},
            "selected": selected_counts,
            "target": limit if academic_sources else len(selected),
        }

    return [
        {
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "abstract": paper.abstract,
            "url": paper.url,
            "paper_url": paper.paper_url or paper.url,
            "pdf_url": paper.pdf_url,
            "doi_url": paper.doi_url,
            "result_type": paper.result_type,
            "keywords": paper.keywords,
            "source": paper.source,
        }
        for paper in selected
    ]
