from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List

from .ai import AIConnection, AIError, OpenAICompatibleClient, cosine_similarity
from .config import ai_model_profiles, ai_role_assignments
from .search import search_papers
from .stage_skills import skill_prompt

_ACADEMIC_SOURCES = {"arxiv", "openalex", "semanticscholar"}
_EMBED_CACHE: Dict[tuple, tuple[float, List[float]]] = {}
_EMBED_CACHE_LOCK = threading.RLock()
_EMBED_CACHE_TTL = 24 * 60 * 60
_EMBED_CACHE_MAX = 4096


def _client_from_config(
    config: Dict[str, str],
    require_embedding: bool = True,
    role: str = "intelligent_search",
    profile_id: str = "",
    timeout_scope: str = "",
    skills_dir=None,
) -> OpenAICompatibleClient:
    profiles = ai_model_profiles(config)
    profile_by_id = {str(item.get("id")): item for item in profiles}
    roles = ai_role_assignments(config)
    chat_profile = profile_by_id.get(profile_id) if profile_id else None
    if chat_profile and "chat" not in chat_profile.get("capabilities", []):
        chat_profile = None
    chat_profile = chat_profile or profile_by_id.get(roles.get(role) or "")
    embedding_profile = profile_by_id.get(roles.get("embedding") or "") or {}
    chat_profile = chat_profile or {}
    base_url = str(chat_profile.get("base_url") or "").strip()
    chat_model = str(chat_profile.get("model") or "").strip()
    embedding_model = str(embedding_profile.get("model") or "").strip()
    if not base_url or not chat_model:
        raise AIError(
            "ai_unconfigured",
            "Configure AI Base URL and Language Model first.",
        )
    embedding_base_url = str(embedding_profile.get("base_url") or "").strip()
    if embedding_model and not embedding_base_url:
        raise AIError("ai_unconfigured", "Configure the Embedding Base URL.")
    timeout_key = (
        "ai_search_timeout_seconds"
        if timeout_scope == "search" or (not timeout_scope and role == "intelligent_search")
        else "ai_stage_timeout_seconds"
    )
    client = OpenAICompatibleClient(
        AIConnection(
            base_url,
            str(chat_profile.get("api_key") or ""),
            str(chat_profile.get("proxy_mode") or "auto"),
            str(chat_profile.get("proxy_url") or ""),
        ),
        chat_model,
        AIConnection(
            embedding_base_url,
            str(embedding_profile.get("api_key") or ""),
            str(embedding_profile.get("proxy_mode") or "auto"),
            str(embedding_profile.get("proxy_url") or ""),
        ),
        embedding_model,
        timeout=int(
            config.get(timeout_key)
            or config.get("ai_timeout_seconds")
            or "45"
        ),
        enable_thinking=(
            bool(chat_profile.get("enable_thinking", False))
        ),
        provider=str(chat_profile.get("provider") or "openai_compatible"),
        custom_recipe=(chat_profile.get("custom_recipe") or {}),
    )
    client.skills_dir = skills_dir
    return client


def _model_name_from_config(
    config: Dict[str, str], role: str, profile_id: str = ""
) -> str:
    profiles = {str(item.get("id")): item for item in ai_model_profiles(config)}
    roles = ai_role_assignments(config)
    profile = profiles.get(profile_id or roles.get(role) or "") or {}
    return str(profile.get("model") or "")


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
    verification_context: str = "",
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
                "discovery_path": str(candidate.get("discovery_path") or "")[:500],
                "citation_contexts": [
                    str(value)[:1000]
                    for value in (candidate.get("citation_contexts") or [])[:3]
                ],
                "citation_intents": [
                    str(value)[:100]
                    for value in (candidate.get("citation_intents") or [])[:6]
                ],
            }
        )
    area_rule = (
        "Treat these user-selected areas as a hard boundary: " + ", ".join(areas)
        if areas
        else "No hard academic area boundary was selected."
    )
    payload = client.chat_json(
        skill_prompt("relevance", getattr(client, "skills_dir", None)),
        (
            f"Intent or Focus: {query}\n{area_rule}\n"
            + (f"Seed context:\n{verification_context[:16000]}\n" if verification_context else "")
            + "Candidates:\n"
            f"{json.dumps(compact, ensure_ascii=False)}\n"
            "Return {\"items\":[{\"key\":\"c0\",\"tier\":\"strong|possible|excluded\","
            "\"score\":0.0,\"reason\":\"brief evidence-based reason\","
            "\"basis\":\"abstract + citation context|abstract|title only\"}]}. "
            "Include every candidate exactly once. score must be 0..1. "
            "A keyword match or citation edge alone is insufficient. When available "
            "information cannot justify strong, use possible rather than guessing."
        ),
        max_tokens=max(512, min(4096, len(compact) * 160)),
    )
    items = payload.get("items", []) if isinstance(payload, dict) else []
    verified = []
    decided_keys = set()
    for decision in items:
        if not isinstance(decision, dict):
            continue
        candidate = by_key.get(str(decision.get("key") or ""))
        if candidate is None:
            continue
        decided_keys.add(str(decision.get("key") or ""))
        tier = str(decision.get("tier") or "").strip().lower()
        if not tier and "relevant" in decision:
            tier = "strong" if decision.get("relevant") is True else "excluded"
        if tier not in {"strong", "possible", "excluded"}:
            tier = "possible"
        item = dict(candidate)
        try:
            score = float(decision.get("score", 0))
        except (TypeError, ValueError):
            score = 0.0
        item["verification_score"] = max(0.0, min(1.0, score))
        item["relevance_tier"] = tier
        item["match_reason"] = str(decision.get("reason") or "Verified against the full intent.")[:600]
        item["verification_basis"] = str(decision.get("basis") or "candidate metadata")[:200]
        if item.get("discovery_links"):
            item["discovery_path"] = (
                str(item.get("discovery_path") or "Academic graph")
                + " → LLM verify"
            )
        elif item.get("result_type") == "web":
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
    for key, candidate in by_key.items():
        if key in decided_keys:
            continue
        item = dict(candidate)
        item["relevance_tier"] = "possible"
        item["verification_score"] = 0.0
        item["match_reason"] = "The model did not return a usable assessment for this candidate."
        item["verification_basis"] = "unassessed candidate metadata"
        verified.append(item)
    return sorted(
        verified,
        key=lambda item: (
            {"strong": 2, "possible": 1, "excluded": 0}.get(
                item.get("relevance_tier"), 1
            ),
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
        fallback["relevance_tier"] = "possible"
        fallback["verification_basis"] = "LLM verification unavailable"
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
    verification_context: str = "",
) -> tuple[List[dict], List[AIError], int]:
    skill_prompt("relevance", getattr(client, "skills_dir", None))
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
                executor.submit(
                    _verify, client, query, areas, batch, verification_context
                ) if verification_context else executor.submit(
                    _verify, client, query, areas, batch
                ): batch
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
        accepted_count = sum(
            item.get("relevance_tier") != "excluded" for item in verified
        )
        if accepted_count >= target_count:
            break
    return (
        sorted(
            verified,
            key=lambda item: (
                {"strong": 2, "possible": 1, "excluded": 0}.get(
                    item.get("relevance_tier"), 1
                ),
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
    search_actions: List[dict] | None = None,
    profile_id: str = "",
    skills_dir=None,
) -> Dict[str, Any]:
    def report(stage: str, **details: Any) -> None:
        if progress is not None:
            progress(stage, details)

    academic_backends = [source for source in backends if source in _ACADEMIC_SOURCES]
    client = _client_from_config(
        config, require_embedding=bool(academic_backends), role="intelligent_search",
        profile_id=profile_id, skills_dir=skills_dir,
    )
    skill_prompt("relevance", skills_dir)
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
        "embed": {"status": "skipped", "requests": 0},
        "verify": {"status": "pending", "requests": 0},
    }

    actions = []
    for item in (search_actions or [])[:5]:
        if not isinstance(item, dict):
            continue
        action_query = str(item.get("query") or "").strip()[:500]
        target = str(item.get("target") or "both").strip().lower()
        if action_query and target in {"academic", "both"}:
            actions.append({"query": action_query, "target": "academic"})
    if not actions:
        actions = [{"query": query, "target": "academic"}]
    academic_queries = list(dict.fromkeys(
        item["query"] for item in actions
        if item["target"] in {"academic", "both"}
    ))

    academic_candidates: List[dict] = []
    if academic_backends:
        report("recall", search_actions=actions)
        for retrieval_query in academic_queries:
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

    verification_candidates = ranked_academic
    report("verify")
    assessed, verification_errors, verification_requests = _verify_batched(
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

    selected = [
        item for item in assessed if item.get("relevance_tier") != "excluded"
    ]
    excluded = [
        item for item in assessed if item.get("relevance_tier") == "excluded"
    ]
    final_results = selected[:limit]
    source_counts = dict(
        Counter(result.get("source") or "Unknown" for result in final_results)
    )
    return {
        "query": query,
        "results": final_results,
        "excluded_results": excluded,
        "count": len(final_results),
        "warnings": warnings,
        "stages": stages,
        "search_actions": actions,
        "candidate_counts": {
            "academic": len(academic_candidates),
            "verified": len(assessed),
        },
        "source_counts": source_counts,
        "request_budget": {
            "retrieval": stages["recall"]["requests"],
            "academic_retrieval": len(academic_queries) if academic_backends else 0,
            "chat": stages["verify"]["requests"],
            "embedding": stages["embed"]["requests"],
        },
        "_ai_usage": client.usage_snapshot(),
    }
