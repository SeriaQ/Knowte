"""Validated local documents, using the existing Source reader and Evidence flow."""
from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path
import re
from xml.etree import ElementTree
from zipfile import ZipFile, BadZipFile

from pypdf import PdfReader

from .knowledge import save_source, store_capture, list_sources

MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
EXTENSIONS = {".pdf", ".md", ".markdown", ".txt", ".docx"}


def parse_document(raw: bytes, filename: str) -> dict:
    suffix = Path(filename).suffix.lower()
    if suffix not in EXTENSIONS:
        raise ValueError("Supported documents: PDF, Markdown, TXT, DOCX")
    if not raw or len(raw) > MAX_DOCUMENT_BYTES:
        raise ValueError("Each document must be between 1 byte and 20 MB")
    blocks, locators = [], []
    media = "text/plain"
    def add(text, kind="paragraph", locator="", metadata=None):
        blocks.append({"text": text, "type": kind, "metadata": metadata or {}})
        locators.append(locator or f"Paragraph {len(blocks)}")
    try:
        if suffix == ".pdf":
            if not raw.startswith(b"%PDF"):
                raise ValueError("Not a PDF file")
            reader = PdfReader(BytesIO(raw))
            if reader.is_encrypted and not reader.decrypt(""):
                raise ValueError("Password-protected PDF: unlock it before uploading")
            if not reader.pages or len(reader.pages) > 2000:
                raise ValueError("PDF must contain 1–2,000 pages")
            for i, page in enumerate(reader.pages, 1):
                # Keep empty pages as anchors for screenshots and correct page numbering.
                add(page.extract_text() or "", "page", f"Page {i}", {"page": i})
            media = "application/pdf"
        elif suffix == ".docx":
            with ZipFile(BytesIO(raw)) as archive:
                if sum(item.file_size for item in archive.infolist()) > 50 * 1024 * 1024:
                    raise ValueError("DOCX expands beyond the 50 MB safety limit")
                xml = archive.read("word/document.xml")
            if b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
                raise ValueError("DOCX contains unsupported XML declarations")
            root = ElementTree.fromstring(xml)
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            for paragraph in root.findall(".//w:p", ns):
                text = "".join(node.text or "" for node in paragraph.findall(".//w:t", ns)).strip()
                if text:
                    style = paragraph.find("w:pPr/w:pStyle", ns)
                    value = style.get("{" + ns["w"] + "}val", "") if style is not None else ""
                    heading = re.fullmatch(r"Heading([1-6])", value, re.I)
                    add(text, "heading" if heading else "paragraph", metadata={"level": int(heading[1])} if heading else {})
            media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
            text = raw.decode(encoding)
            if any(ord(c) < 32 and c not in "\n\r\t" for c in text):
                raise ValueError("The file contains binary data, not readable text")
            for section in re.split(r"\n\s*\n", text):
                if not section.strip():
                    continue
                heading = re.match(r"^(#{1,6})\s+(.+)$", section.strip()) if suffix != ".txt" else None
                add(heading[2] if heading else section.strip(), "heading" if heading else "code" if section.strip().startswith("```") else "paragraph", metadata={"level": len(heading[1])} if heading else {})
            media = "text/markdown" if suffix != ".txt" else "text/plain"
    except (BadZipFile, KeyError, ElementTree.ParseError, UnicodeError) as error:
        raise ValueError("Cannot parse this document. Check the file or export it as PDF/UTF-8 text.") from error
    except Exception as error:
        if isinstance(error, ValueError):
            raise
        raise ValueError(f"Cannot read this document: {error}") from error
    if not blocks:
        raise ValueError("No readable text found. Image-only DOCX should be exported as PDF.")
    return {"url": "", "media_type": media, "sha256": hashlib.sha256(raw).hexdigest(),
            "segments": [b["text"] for b in blocks], "blocks": blocks,
            "locators": locators, "extraction_version": 3}


def import_document(raw: bytes, filename: str, title: str, database: Path, content_dir: Path):
    captured = parse_document(raw, filename)  # Reject before writing any Source or file.
    digest = captured["sha256"]
    existing = next((s for s in list_sources(database) if s["canonical_key"] == f"document:{digest}"), None)
    if existing:
        return {"source": existing, "duplicate": True}
    suffix = Path(filename).suffix.lower()
    content_dir.mkdir(parents=True, exist_ok=True)
    original = content_dir / f"{digest}{suffix}"
    original.write_bytes(raw)
    captured["raw_path"] = str(original)
    source, _, _ = save_source({"title": title.strip() or Path(filename).stem,
        "document_hash": digest, "document_filename": Path(filename).name,
        "source": "Local document", "result_type": "web"}, path=database)
    workspace = store_capture(source["id"], captured, database)
    return {"source": workspace["source"], "duplicate": False,
            "text_available": any(text.strip() for text in captured["segments"])}
