from __future__ import annotations

import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List

from .ai import AIConnection, AIError, OpenAICompatibleClient, cosine_similarity
from .search import search_papers

_ACADEMIC_SOURCES = {"arxiv", "openalex", "semanticscholar"}
_EMBED_CACHE: Dict[tuple, tuple[float, List[float]]] = {}
_EMBED_CACHE_LOCK = threading.RLock()
_EMBED_CACHE_TTL = 24 * 60 * 60
_EMBED_CACHE_MAX = 4096


def _client_from_config(
    config: Dict[str, str],
    require_embedding: bool = True,
) -> OpenAICompatibleClient:
    base_url = (config.get("ai_base_url") or "").strip()
    chat_model = (config.get("ai_chat_model") or "").strip()
    embedding_model = (config.get("ai_embedding_model") or "").strip()
    if not base_url or not chat_model:
        raise AIError(
            "ai_unconfigured",
            "Configure AI Base URL and Language Model first.",
        )
    separate_embedding = str(
        config.get("ai_embedding_separate_connection") or ""
    ).lower() in {"1", "true", "yes", "on"}
    embedding_base_url = (
        (config.get("ai_embedding_base_url") or "").strip()
        if separate_embedding
        else base_url
    )
    if embedding_model and not embedding_base_url:
        raise AIError("ai_unconfigured", "Configure the Embedding Base URL.")
    return OpenAICompatibleClient(
        AIConnection(base_url, config.get("ai_api_key") or ""),
        chat_model,
        AIConnection(
            embedding_base_url,
            (
                config.get("ai_embedding_api_key") or ""
                if separate_embedding
                else config.get("ai_api_key") or ""
            ),
        ),
        embedding_model,
        timeout=int(config.get("ai_timeout_seconds") or "45"),
        enable_thinking=(
            str(config.get("ai_enable_thinking") or "").lower()
            in {"1", "true", "yes", "on"}
            if "ai_enable_thinking" in config
            else False
        ),
    )


def _dedupe(results: List[dict]) -> List[dict]:
    seen = set()
    output = []
    for result in results:
        key = (result.get("id") or result.get("url") or result.get("title") or "").casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(result)
    return output


def _candidate_text(result: dict) -> str:
    title = str(result.get("title") or "")[:500]
    abstract = str(result.get("abstract") or "")[:3500]
    keywords = ", ".join(str(value) for value in (result.get("keywords") or [])[:20])
    return f"Title: {title}\nAbstract: {abstract}\nKeywords: {keywords}".strip()


def _expand_queries(
    client: OpenAICompatibleClient,
    query: str,
    areas: List[str],
) -> List[str]:
    area_rule = (
        "The user explicitly selected these area codes; keep every query inside them: "
        + ", ".join(areas)
        if areas
        else "No area was selected. Infer useful academic terminology without imposing a hard field filter."
    )
    payload = client.chat_json(
        "You generate retrieval queries for academic discovery. Return JSON only.",
        (
            f"Intent: {query}\n{area_rule}\n"
            "Return {\"queries\": [..]} with at most 2 concise search queries. "
            "Use terminology likely to appear in relevant papers that may not repeat the user's wording. "
            "Do not explain."
        ),
        max_tokens=256,
    )
    queries = payload.get("queries", []) if isinstance(payload, dict) else []
    cleaned = [
        str(value).strip()
        for value in queries
        if isinstance(value, str) and str(value).strip()
    ]
    return list(dict.fromkeys(cleaned))[:2]


def _embedding_vectors(
    client: OpenAICompatibleClient,
    texts: List[str],
) -> tuple[List[List[float]], int, int]:
    now = time.monotonic()
    keys = [
        (
            client.embedding_connection.base_url.rstrip("/"),
            client.embedding_model,
            hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )
        for text in texts
    ]
    vectors: List[List[float] | None] = [None] * len(texts)
    missing: Dict[tuple, tuple[str, List[int]]] = {}
    cache_hits = 0
    with _EMBED_CACHE_LOCK:
        for index, (key, text) in enumerate(zip(keys, texts)):
            cached = _EMBED_CACHE.get(key)
            if cached and now - cached[0] <= _EMBED_CACHE_TTL:
                vectors[index] = list(cached[1])
                cache_hits += 1
                continue
            if cached:
                _EMBED_CACHE.pop(key, None)
            if key in missing:
                missing[key][1].append(index)
            else:
                missing[key] = (text, [index])

    missing_items = list(missing.items())
    requests = 0
    for start in range(0, len(missing_items), 64):
        batch = missing_items[start : start + 64]
        batch_vectors = client.embeddings([value[0] for _, value in batch])
        requests += 1
        with _EMBED_CACHE_LOCK:
            for (key, (_, positions)), vector in zip(batch, batch_vectors):
                _EMBED_CACHE[key] = (now, list(vector))
                for position in positions:
                    vectors[position] = list(vector)
            while len(_EMBED_CACHE) > _EMBED_CACHE_MAX:
                oldest = next(iter(_EMBED_CACHE))
                _EMBED_CACHE.pop(oldest, None)
    if any(vector is None for vector in vectors):
        raise AIError("invalid_response", "Embedding vectors could not be assembled.")
    return [vector for vector in vectors if vector is not None], requests, cache_hits


def _rank_academic(
    client: OpenAICompatibleClient,
    query: str,
    candidates: List[dict],
) -> tuple[List[dict], int, int]:
    if not candidates:
        return [], 0, 0
    texts = [query, *[_candidate_text(candidate) for candidate in candidates]]
    vectors, requests, cache_hits = _embedding_vectors(client, texts)
    query_vector = vectors[0]
    ranked = []
    for candidate, vector in zip(candidates, vectors[1:]):
        item = dict(candidate)
        item["semantic_score"] = max(0.0, min(1.0, cosine_similarity(query_vector, vector)))
        ranked.append(item)
    return (
        sorted(ranked, key=lambda item: item["semantic_score"], reverse=True),
        requests,
        cache_hits,
    )


def _verify(
    client: OpenAICompatibleClient,
    query: str,
    areas: List[str],
    candidates: List[dict],
) -> List[dict]:
    if not candidates:
        return []
    compact = []
    by_key = {}
    for index, candidate in enumerate(candidates):
        key = f"c{index}"
        by_key[key] = candidate
        compact.append(
            {
                "key": key,
                "type": candidate.get("result_type", "paper"),
                "title": str(candidate.get("title") or "")[:500],
                "summary": str(candidate.get("abstract") or "")[:2500],
                "semantic_score": candidate.get("semantic_score"),
            }
        )
    area_rule = (
        "Treat these user-selected areas as a hard boundary: " + ", ".join(areas)
        if areas
        else "No hard academic area boundary was selected."
    )
    payload = client.chat_json(
        (
            "You verify research search results against the user's full intent. "
            "Return JSON only and never invent facts absent from a candidate."
        ),
        (
            f"Intent: {query}\n{area_rule}\nCandidates:\n"
            f"{json.dumps(compact, ensure_ascii=False)}\n"
            "Return {\"items\":[{\"key\":\"c0\",\"relevant\":true,"
            "\"score\":0.0,\"reason\":\"brief evidence-based reason\"}]}. "
            "Include every candidate once. score must be 0..1. "
            "A keyword match alone is insufficient."
        ),
        max_tokens=max(512, min(4096, len(compact) * 160)),
    )
    items = payload.get("items", []) if isinstance(payload, dict) else []
    verified = []
    for decision in items:
        if not isinstance(decision, dict):
            continue
        candidate = by_key.get(str(decision.get("key") or ""))
        if candidate is None or decision.get("relevant") is not True:
            continue
        item = dict(candidate)
        try:
            score = float(decision.get("score", 0))
        except (TypeError, ValueError):
            score = 0.0
        item["verification_score"] = max(0.0, min(1.0, score))
        item["match_reason"] = str(decision.get("reason") or "Verified against the full intent.")[:600]
        if item.get("result_type") == "web":
            item["discovery_path"] = "Web recall → LLM verify"
        else:
            item["discovery_path"] = (
                "Academic recall"
                + (
                    " → semantic ranking"
                    if isinstance(item.get("semantic_score"), (int, float))
                    else ""
                )
                + " → LLM verify"
            )
        verified.append(item)
    return sorted(
        verified,
        key=lambda item: (
            item.get("verification_score", 0),
            item.get("semantic_score", 0),
        ),
        reverse=True,
    )


def _verification_fallback(candidates: List[dict], error: AIError) -> List[dict]:
    fallback_results = []
    for item in candidates:
        fallback = dict(item)
        has_embedding_rank = isinstance(
            fallback.get("semantic_score"),
            (int, float),
        )
        source_description = (
            "embedding ranking"
            if has_embedding_rank
            else (
                "Web recall"
                if item.get("result_type") == "web"
                else "academic recall"
            )
        )
        fallback["match_reason"] = (
            f"LLM verification failed ({error.code}); this result is shown "
            f"from {source_description}."
        )
        fallback["discovery_path"] = (
            (
                "Academic recall → semantic ranking"
                if has_embedding_rank
                else "Academic recall"
            )
            if item.get("result_type") != "web"
            else "Web recall"
        )
        fallback_results.append(fallback)
    return fallback_results


def _verify_batched(
    client: OpenAICompatibleClient,
    query: str,
    areas: List[str],
    candidates: List[dict],
    batch_size: int,
    concurrency: int,
    target_count: int,
) -> tuple[List[dict], List[AIError], int]:
    batches = [
        candidates[start : start + batch_size]
        for start in range(0, len(candidates), batch_size)
    ]
    if not batches:
        return [], [], 0
    verified: List[dict] = []
    errors: List[AIError] = []
    requests = 0
    worker_count = max(1, min(concurrency, len(batches)))
    for wave_start in range(0, len(batches), worker_count):
        wave = batches[wave_start : wave_start + worker_count]
        with ThreadPoolExecutor(max_workers=len(wave)) as executor:
            pending = {
                executor.submit(_verify, client, query, areas, batch): batch
                for batch in wave
            }
            requests += len(pending)
            for future in as_completed(pending):
                batch = pending[future]
                try:
                    verified.extend(future.result())
                except AIError as error:
                    errors.append(error)
                    verified.extend(_verification_fallback(batch, error))
        if len(verified) >= target_count:
            break
    return (
        sorted(
            verified,
            key=lambda item: (
                item.get("verification_score", -1),
                item.get("semantic_score", -1),
            ),
            reverse=True,
        ),
        errors,
        requests,
    )


def intelligent_search(
    query: str,
    config: Dict[str, str],
    limit: int,
    backends: List[str],
    areas: List[str],
    year_from: int | None,
    year_to: int | None,
    web_pages: int = 1,
    progress: Callable[[str, Dict[str, Any]], None] | None = None,
) -> Dict[str, Any]:
    def report(stage: str, **details: Any) -> None:
        if progress is not None:
            progress(stage, details)

    academic_backends = [source for source in backends if source in _ACADEMIC_SOURCES]
    include_web = "websearch" in backends and bool(config.get("searxng_url"))
    client = _client_from_config(config, require_embedding=bool(academic_backends))
    candidate_limit = max(
        20,
        min(int(config.get("max_papers") or "100"), 100),
    )
    verify_batch_size = max(
        1,
        min(int(config.get("ai_verify_batch_size") or "5"), 20),
    )
    verify_concurrency = max(
        1,
        min(int(config.get("ai_verify_concurrency") or "1"), 8),
    )
    warnings: List[str] = []
    stages: Dict[str, Any] = {
        "recall": {"status": "complete", "requests": 0},
        "expand": {"status": "skipped", "requests": 0},
        "embed": {"status": "skipped", "requests": 0},
        "verify": {"status": "pending", "requests": 0},
    }

    expanded_queries: List[str] = []
    if academic_backends:
        report("expand")
        try:
            expanded_queries = _expand_queries(client, query, areas)
            stages["expand"] = {"status": "complete", "requests": 1}
        except AIError as error:
            warnings.append(f"query_expansion_failed:{error.code}")
            stages["expand"] = {"status": "degraded", "requests": 1}

    academic_candidates: List[dict] = []
    if academic_backends:
        report(
            "recall",
            expanded_queries=expanded_queries,
            expansion_status=stages["expand"]["status"],
        )
        for retrieval_query in [query, *expanded_queries]:
            academic_candidates.extend(
                search_papers(
                    retrieval_query,
                    limit=candidate_limit,
                    email=config.get("email"),
                    areas=areas,
                    semanticscholar_key=config.get("semanticscholar_api_key"),
                    backends=academic_backends,
                    year_from=year_from,
                    year_to=year_to,
                    strict_match=False,
                )
            )
            stages["recall"]["requests"] += 1
    academic_candidates = _dedupe(academic_candidates)

    web_candidates: List[dict] = []
    if include_web:
        report("recall")
        web_candidates = search_papers(
            query,
            limit=limit,
            backends=["websearch"],
            year_from=year_from,
            year_to=year_to,
            searxng_url=config.get("searxng_url"),
            web_ignore_year_filter=str(
                config.get("web_ignore_year_filter") or ""
            ).lower() in {"1", "true", "yes", "on"},
            web_pages=web_pages,
            strict_match=False,
        )
        stages["recall"]["requests"] += 1

    ranked_academic = academic_candidates
    if academic_candidates and client.embedding_model:
        report("embed")
        try:
            ranked_academic, requests, cache_hits = _rank_academic(
                client, query, academic_candidates
            )
            stages["embed"] = {
                "status": "complete",
                "requests": requests,
                "cache_hits": cache_hits,
            }
        except AIError as error:
            warnings.append(f"embedding_failed:{error.code}")
            stages["embed"] = {"status": "degraded", "requests": 1}
    elif academic_candidates:
        warnings.append("embedding_unconfigured")
        stages["embed"] = {"status": "skipped", "requests": 0}

    if ranked_academic and web_candidates:
        academic_slots = max(1, round(limit * 0.7))
        web_slots = max(1, limit - academic_slots)
        verification_candidates = [
            *ranked_academic[:academic_slots],
            *web_candidates[:web_slots],
        ]
        used = {
            item.get("id") or item.get("url") or item.get("title")
            for item in verification_candidates
        }
        verification_candidates.extend(
            item
            for item in [*ranked_academic, *web_candidates]
            if (item.get("id") or item.get("url") or item.get("title")) not in used
        )
    else:
        verification_candidates = [*ranked_academic, *web_candidates]
    report("verify")
    selected, verification_errors, verification_requests = _verify_batched(
        client,
        query,
        areas,
        verification_candidates,
        verify_batch_size,
        verify_concurrency,
        limit,
    )
    if verification_errors:
        error = verification_errors[0]
        warnings.extend(
            f"verification_failed:{code}"
            for code in dict.fromkeys(item.code for item in verification_errors)
        )
        stages["verify"] = {
            "status": "degraded",
            "requests": verification_requests,
            "completed_batches": verification_requests - len(verification_errors),
            "failed_batches": len(verification_errors),
            "error": error.code,
            "message": (
                f"{len(verification_errors)} of {verification_requests} "
                f"verification batch(es) failed. {error}"
            ),
        }
    else:
        stages["verify"] = {
            "status": "complete",
            "requests": verification_requests,
            "completed_batches": verification_requests,
            "failed_batches": 0,
        }

    final_limit = limit if academic_backends else len(web_candidates)
    final_results = selected[:final_limit]
    return {
        "query": query,
        "results": final_results,
        "count": len(final_results),
        "warnings": warnings,
        "stages": stages,
        "expanded_queries": expanded_queries,
        "candidate_counts": {
            "academic": len(academic_candidates),
            "web": len(web_candidates),
            "verified": len(selected),
        },
        "request_budget": {
            "retrieval": stages["recall"]["requests"],
            "academic_retrieval": (
                1 + len(expanded_queries) if academic_backends else 0
            ),
            "web_retrieval": 1 if include_web else 0,
            "chat": stages["expand"]["requests"] + stages["verify"]["requests"],
            "embedding": stages["embed"]["requests"],
        },
        "_ai_usage": client.usage_snapshot(),
    }
