from __future__ import annotations

import json
from typing import List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..models import Paper

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def _fetch_semanticscholar(
    query: str,
    limit: int,
    fields: Optional[List[str]] = None,
    api_key: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> List[dict]:
    params = {
        "query": query,
        "limit": min(max(limit, 1), 100),
        "fields": "title,authors,year,abstract,externalIds,url,fieldsOfStudy,openAccessPdf",
    }
    if fields:
        params["fieldsOfStudy"] = ",".join(fields)
    if year_from is not None and year_to is not None:
        params["year"] = f"{year_from}-{year_to}"
    elif year_from is not None:
        params["year"] = f"{year_from}-"
    elif year_to is not None:
        params["year"] = f"-{year_to}"
    url = f"{BASE_URL}?{urlencode(params)}"
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    try:
        request = Request(url, headers=headers)
        with urlopen(request, timeout=10) as response:
            data = response.read()
    except OSError:
        return []

    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return []
    return payload.get("data", []) or []


def search_semanticscholar(
    query: str,
    limit: int = 6,
    fields: Optional[List[str]] = None,
    api_key: str | None = None,
    query_boosts: Optional[List[str]] = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> List[Paper]:
    if not query:
        return []

    target = max(limit * 2, 8)
    raw_items: List[dict] = []
    seen_ids = set()

    variants = [query]
    for boost in (query_boosts or [])[:2]:
        variants.append(f"{query} {boost}")

    for variant_query in variants:
        for item in _fetch_semanticscholar(
            variant_query,
            max(limit, 8),
            fields,
            api_key,
            year_from,
            year_to,
        ):
            item_id = (
                (item.get("externalIds") or {}).get("DOI")
                or item.get("url")
                or item.get("title")
                or ""
            )
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            raw_items.append(item)
            if len(raw_items) >= target:
                break
        if len(raw_items) >= target:
            break

    results: List[Paper] = []
    for item in raw_items:
        title = (item.get("title") or "").strip()
        if not title:
            continue
        year = item.get("year") or 0
        authors = ", ".join(a.get("name", "") for a in item.get("authors", []) if a.get("name"))
        abstract = (item.get("abstract") or "").strip() or "No abstract provided."
        url = item.get("url") or ""
        fields_list = item.get("fieldsOfStudy") or []
        external_ids = item.get("externalIds") or {}
        doi = external_ids.get("DOI") or external_ids.get("doi") or ""
        doi_url = f"https://doi.org/{doi}" if doi else ""
        pdf_url = (item.get("openAccessPdf") or {}).get("url") or ""
        paper_id = doi or url or title
        results.append(
            Paper(
                id=paper_id,
                title=title,
                authors=authors or "Unknown",
                year=year,
                abstract=abstract,
                url=url,
                keywords=fields_list,
                source="Semantic Scholar",
                paper_url=url,
                pdf_url=pdf_url,
                doi_url=doi_url,
            )
        )
    return results
