from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Paper:
    id: str
    title: str
    authors: str
    year: int
    abstract: str
    url: str
    keywords: List[str]
    source: str
    paper_url: str = ""
    pdf_url: str = ""
    doi_url: str = ""
    result_type: str = "paper"
