from __future__ import annotations

import hashlib
import io
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class CaptureError(RuntimeError):
    pass


class _ReadableHTML(HTMLParser):
    _BLOCKS = {
        "article", "blockquote", "div", "figcaption", "h1", "h2", "h3",
        "h4", "h5", "h6", "li", "main", "p", "pre", "section", "td", "th",
    }
    _SKIP = {
        "aside", "button", "dialog", "footer", "form", "header", "nav",
        "noscript", "script", "style", "svg", "template",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._main_depth = 0
        self._article_depth = 0
        self._parts = {"all": [], "main": [], "article": []}
        self._segments = {"all": [], "main": [], "article": []}
        self._blocks = {"all": [], "main": [], "article": []}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIP:
            if not self._skip_depth:
                self._flush()
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in self._BLOCKS:
            self._flush()
        if tag == "main":
            self._main_depth += 1
        if tag == "article":
            self._article_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth:
            if tag in self._SKIP:
                self._skip_depth -= 1
            return
        if tag in self._BLOCKS:
            block_type = {
                "blockquote": "quote", "figcaption": "caption", "li": "list_item",
                "pre": "code", "td": "table_cell", "th": "table_header",
            }.get(tag, "heading" if re.fullmatch(r"h[1-6]", tag) else "paragraph")
            metadata = {"level": int(tag[1])} if block_type == "heading" else {}
            self._flush(
                minimum_length=3 if block_type == "heading" else 20,
                block_type=block_type,
                metadata=metadata,
            )
        if tag == "article" and self._article_depth:
            self._article_depth -= 1
        if tag == "main" and self._main_depth:
            self._main_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        self._parts["all"].append(data)
        if self._main_depth:
            self._parts["main"].append(data)
        if self._article_depth:
            self._parts["article"].append(data)

    def close(self) -> None:
        super().close()
        self._flush()

    def _flush(
        self,
        minimum_length: int = 20,
        block_type: str = "paragraph",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        for scope in self._parts:
            text = " ".join("".join(self._parts[scope]).split())
            self._parts[scope] = []
            segments = self._segments[scope]
            if (
                len(text) >= minimum_length
                and (not segments or text != segments[-1])
            ):
                segments.append(text)
                self._blocks[scope].append({
                    "type": block_type,
                    "text": text,
                    "metadata": metadata or {},
                })

    @property
    def segments(self) -> list[str]:
        return [block["text"] for block in self.blocks]

    @property
    def blocks(self) -> list[dict[str, Any]]:
        for scope in ("article", "main", "all"):
            blocks = self._blocks[scope]
            if sum(len(block["text"]) for block in blocks) >= 200 or scope == "all":
                return blocks
        return []


def preferred_capture_url(source: dict[str, Any]) -> str:
    if str(source.get("source_type") or "").strip().lower() == "paper":
        pdf_url = _pdf_url(source)
        if pdf_url:
            return pdf_url
    for value in (source.get("paper_url"), source.get("url"), source.get("pdf_url")):
        url = str(value or "").strip()
        match = re.match(
            r"https?://(?:www\.)?arxiv\.org/(?:abs|pdf)/([^/?#]+)",
            url,
            re.IGNORECASE,
        )
        if match:
            arxiv_id = re.sub(r"v\d+$", "", match.group(1), flags=re.IGNORECASE)
            return f"https://arxiv.org/html/{arxiv_id}"
    return str(
        source.get("paper_url") or source.get("url") or source.get("pdf_url") or ""
    ).strip()


def _pdf_url(source: dict[str, Any]) -> str:
    explicit = str(source.get("pdf_url") or "").strip()
    if explicit:
        return explicit
    paper_url = str(source.get("paper_url") or source.get("url") or "").strip()
    return re.sub(r"/abs/", "/pdf/", paper_url, count=1)


def _extract_pdf(raw: bytes) -> list[dict[str, str]]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(raw))
    segments = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = "\n".join(
            line.rstrip() for line in (page.extract_text() or "").splitlines()
            if line.strip()
        ).strip()
        if text:
            segments.append({"locator": f"Page {page_number}", "text": text})
    return segments


def capture_source_content(
    source: dict[str, Any],
    content_dir: Path,
    *,
    timeout: float = 30,
    max_bytes: int = 20 * 1024 * 1024,
) -> dict[str, Any]:
    url = preferred_capture_url(source)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise CaptureError("This Source does not have a capturable HTTP URL.")
    def fetch(target: str, accept: str) -> tuple[bytes, str, str]:
        request = Request(
            target,
            headers={
                "User-Agent": "Knowte/0.2 (+https://github.com/SeriaQ/Knowte)",
                "Accept": accept,
            },
        )
        with urlopen(request, timeout=timeout) as response:
            return (
                response.read(max_bytes + 1),
                response.headers.get_content_type(),
                response.geturl(),
            )

    try:
        raw, media_type, final_url = fetch(
            url, "text/html,application/xhtml+xml,application/pdf"
        )
    except HTTPError as error:
        if error.code != 404 or "arxiv.org/html/" not in url:
            raise CaptureError(f"Could not capture Source: {error}") from error
        try:
            raw, media_type, final_url = fetch(_pdf_url(source), "application/pdf")
        except (HTTPError, URLError, TimeoutError, OSError) as fallback_error:
            raise CaptureError(
                f"Could not capture arXiv HTML or PDF: {fallback_error}"
            ) from fallback_error
    except (URLError, TimeoutError, OSError) as error:
        raise CaptureError(f"Could not capture Source: {error}") from error
    if len(raw) > max_bytes:
        raise CaptureError("Source content exceeds the 20 MB capture limit.")
    if media_type == "application/pdf" or raw.startswith(b"%PDF"):
        extracted = _extract_pdf(raw)
        segments = [item["text"] for item in extracted]
        locators = [item["locator"] for item in extracted]
        suffix = "pdf"
    elif media_type in {"text/html", "application/xhtml+xml"}:
        try:
            html = raw.decode("utf-8")
        except UnicodeDecodeError:
            html = raw.decode("utf-8", errors="replace")
        parser = _ReadableHTML()
        parser.feed(html)
        parser.close()
        blocks = parser.blocks
        segments = [block["text"] for block in blocks]
        locators = [
            f"{block['type'].replace('_', ' ').title()} {index}"
            for index, block in enumerate(blocks, start=1)
        ]
        suffix = "html"
    else:
        raise CaptureError(
            f"Unsupported capture format: {media_type}."
        )
    if not segments:
        raise CaptureError("No readable content was found in this Source.")

    digest = hashlib.sha256(raw).hexdigest()
    content_dir.mkdir(parents=True, exist_ok=True)
    raw_path = content_dir / f"{digest}.{suffix}"
    if not raw_path.exists():
        raw_path.write_bytes(raw)
    return {
        "url": final_url,
        "media_type": media_type,
        "sha256": digest,
        "raw_path": str(raw_path),
        "segments": segments,
        "locators": locators,
        "blocks": blocks if suffix == "html" else [
            {"type": "page", "text": text, "metadata": {"page": index}}
            for index, text in enumerate(segments, start=1)
        ],
        "extraction_version": 2,
    }
