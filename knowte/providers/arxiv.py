from __future__ import annotations

from typing import List
from urllib.parse import quote
from urllib.request import urlopen
import xml.etree.ElementTree as ET

from ..models import Paper

ARXIV_BASE = "http://export.arxiv.org/api/query"


def _build_area_filter(areas: List[str]) -> str:
    if not areas:
        return ""
    cats = [f"cat:{quote(cat)}" for cat in areas]
    if not cats:
        return ""
    return "+AND+(" + "+OR+".join(cats) + ")"


def _build_year_filter(year_from: int | None, year_to: int | None) -> str:
    if year_from is None and year_to is None:
        return ""
    start = f"{year_from}01010000" if year_from is not None else "000000000000"
    end = f"{year_to}12312359" if year_to is not None else "999912312359"
    return f"+AND+submittedDate:%5B{start}+TO+{end}%5D"


def search_arxiv(
    query: str,
    limit: int = 6,
    categories: List[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> List[Paper]:
    if not query:
        return []
    encoded = quote(query)
    area_clause = _build_area_filter(categories or [])
    year_clause = _build_year_filter(year_from, year_to)
    request_limit = min(max(limit, 1), 100)
    url = f"{ARXIV_BASE}?search_query=all:{encoded}{area_clause}{year_clause}&start=0&max_results={request_limit}"
    try:
        with urlopen(url, timeout=10) as response:
            data = response.read()
    except OSError:
        return []

    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return []

    papers: List[Paper] = []
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    for entry in root.findall("atom:entry", ns):
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
        authors = ", ".join(
            author.findtext("atom:name", default="", namespaces=ns) or ""
            for author in entry.findall("atom:author", ns)
        ).strip()
        published = (entry.findtext("atom:published", default="", namespaces=ns) or "")
        year = int(published[:4]) if published[:4].isdigit() else 0
        link = entry.findtext("atom:id", default="", namespaces=ns) or ""
        pdf_url = ""
        for link_node in entry.findall("atom:link", ns):
            if (
                link_node.attrib.get("title") == "pdf"
                or link_node.attrib.get("type") == "application/pdf"
            ):
                pdf_url = link_node.attrib.get("href", "")
                break
        doi = (
            entry.findtext("arxiv:doi", default="", namespaces=ns) or ""
        ).strip()
        doi_url = f"https://doi.org/{doi}" if doi else ""
        categories = [
            cat.attrib.get("term", "")
            for cat in entry.findall("atom:category", ns)
            if cat.attrib.get("term")
        ]
        if not title:
            continue
        papers.append(
            Paper(
                id=link or title,
                title=title,
                authors=authors or "Unknown",
                year=year,
                abstract=summary or "No abstract provided.",
                url=link or "",
                keywords=categories,
                source="arXiv",
                paper_url=link or "",
                pdf_url=pdf_url,
                doi_url=doi_url,
            )
        )
    return papers
