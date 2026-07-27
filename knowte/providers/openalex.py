from __future__ import annotations

import json
from typing import List
from urllib.parse import urlencode
from urllib.request import urlopen

from ..models import Paper

OPENALEX_BASE = "https://api.openalex.org/works"


def _doi_url(value: str) -> str:
    doi = (value or "").strip()
    if not doi:
        return ""
    if doi.startswith("https://doi.org/"):
        return doi
    if doi.lower().startswith("doi:"):
        doi = doi[4:]
    return f"https://doi.org/{doi}"


def _fetch_openalex(
    query: str,
    email: str | None,
    limit: int,
    concept: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> List[dict]:
    params = {"search": query, "per_page": min(max(limit, 1), 100)}
    if email:
        params["mailto"] = email
    filters = []
    if concept:
        filters.append(f"concepts.display_name:{concept}")
    if year_from is not None:
        filters.append(f"from_publication_date:{year_from}-01-01")
    if year_to is not None:
        filters.append(f"to_publication_date:{year_to}-12-31")
    if filters:
        params["filter"] = ",".join(filters)
    url = f"{OPENALEX_BASE}?{urlencode(params)}"
    try:
        with urlopen(url, timeout=10) as response:
            data = response.read()
    except OSError:
        return []

    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return []
    return payload.get("results", []) or []


def search_openalex(
    query: str,
    email: str | None,
    limit: int = 6,
    concepts: List[str] | None = None,
    query_boosts: List[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> List[Paper]:
    if not query:
        return []

    target = max(limit * 2, 8)
    results_pool: List[dict] = []
    seen_ids = set()

    if concepts:
        variants = [(f"{query} {concept}", None) for concept in concepts[:2]]
    else:
        variants = [(query, None)]
        for boost in (query_boosts or [])[:2]:
            variants.append((f"{query} {boost}", None))

    for variant_query, concept in variants:
        for item in _fetch_openalex(
            variant_query,
            email,
            max(limit, 8),
            concept,
            year_from,
            year_to,
        ):
            item_id = item.get("id") or item.get("title") or ""
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            results_pool.append(item)
            if len(results_pool) >= target:
                break
        if len(results_pool) >= target:
            break

    papers: List[Paper] = []
    for item in results_pool:
        title = (item.get("title") or "").strip()
        if not title:
            continue
        year = item.get("publication_year") or 0
        authors = []
        for author in item.get("authorships", []) or []:
            name = author.get("author", {}).get("display_name")
            if name:
                authors.append(name)
        abstract = item.get("abstract_inverted_index")
        abstract_text = ""
        if abstract:
            tokens = []
            for word, positions in abstract.items():
                for pos in positions:
                    tokens.append((pos, word))
            abstract_text = " ".join(word for _, word in sorted(tokens))
        keywords = [
            concept.get("display_name")
            for concept in item.get("concepts", [])
            if concept.get("display_name")
        ]
        primary_location = item.get("primary_location") or {}
        best_oa_location = item.get("best_oa_location") or {}
        doi_url = _doi_url(item.get("doi") or "")
        paper_url = (
            primary_location.get("landing_page_url")
            or doi_url
            or item.get("id", "")
        )
        pdf_url = (
            primary_location.get("pdf_url")
            or best_oa_location.get("pdf_url")
            or ""
        )
        url = paper_url
        papers.append(
            Paper(
                id=item.get("id", title),
                title=title,
                authors=", ".join(authors) if authors else "Unknown",
                year=year,
                abstract=abstract_text or "No abstract provided.",
                url=url,
                keywords=keywords,
                source="OpenAlex",
                paper_url=paper_url,
                pdf_url=pdf_url,
                doi_url=doi_url,
            )
        )
    return papers
