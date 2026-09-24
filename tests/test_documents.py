import base64
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from pypdf import PdfWriter

from knowte.documents import import_document, parse_document
from knowte.knowledge import (create_artifact, link_project_knowledge, list_sources,
                              get_source_workspace, create_evidence, create_claim, get_capture_file)
from knowte.exports import build_knowledge_export
from knowte.imports import stage_project_package_import, accept_project_import


class DocumentTests(unittest.TestCase):
    def test_text_import_dedup_read_and_extract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); db = root / "knowte.db"
            raw = b"# PPO\n\nClipping limits changes in the objective."
            first = import_document(raw, "notes.md", "RL notes", db, root / "content")
            second = import_document(raw, "renamed.md", "Other title", db, root / "content")
            self.assertTrue(second["duplicate"])
            self.assertEqual(len(list_sources(db)), 1)
            workspace = get_source_workspace(first["source"]["id"], db)
            self.assertEqual(workspace["segments"][0]["block_type"], "heading")
            segment = workspace["segments"][1]
            evidence = create_evidence({"segment_id": segment["id"], "quote": segment["text"]}, db)
            self.assertEqual(evidence["quote"], "Clipping limits changes in the objective.")

    def test_invalid_documents_are_not_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, raw in [("bad.pdf", b"fake"), ("bad.txt", b"\x00\xff"), ("blank.txt", b" \n"), ("bad.docx", b"no zip"), ("bad.exe", b"data")]:
                with self.subTest(name=name), self.assertRaises(ValueError):
                    import_document(raw, name, "", root / "knowte.db", root / "content")
            self.assertFalse((root / "content").exists())

    def test_scanned_pdf_retains_page_anchors(self):
        writer = PdfWriter(); writer.add_blank_page(width=100, height=100)
        writer.add_blank_page(width=100, height=100)
        stream = BytesIO(); writer.write(stream)
        result = parse_document(stream.getvalue(), "scanned.pdf")
        self.assertEqual(result["segments"], ["", ""])
        self.assertEqual(result["locators"], ["Page 1", "Page 2"])

    def test_docx_text_and_headings(self):
        stream = BytesIO()
        with ZipFile(stream, "w") as archive:
            archive.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>PPO</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Clip ratio</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
        result = parse_document(stream.getvalue(), "notes.docx")
        self.assertEqual(result["segments"], ["PPO", "Clip ratio"])
        self.assertEqual(result["blocks"][0]["type"], "heading")

    def test_project_roundtrip_restores_document(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); db = root / "first" / "knowte.db"
            source = import_document(b"Original readable notes.", "notes.txt", "Notes", db, db.parent / "content")["source"]
            project = create_artifact({"title": "RL", "purpose": "Learn"}, db)
            segment = get_source_workspace(source["id"], db)["segments"][0]
            evidence = create_evidence({"segment_id": segment["id"], "quote": segment["text"]}, db)
            claim = create_claim({"statement": "Readable notes exist.", "basis": "reported", "evidence": [{"evidence_id": evidence["id"], "stance": "supports"}]}, db)
            link_project_knowledge(project["id"], "claim", claim["id"], db)
            name, raw = build_knowledge_export("project", [project["id"]], db, db.parent / "content")
            target = root / "second" / "knowte.db"
            staged = stage_project_package_import(base64.b64encode(raw).decode(), name, target, target.parent / "content")
            accept_project_import(staged["project"]["id"], target, target.parent / "content")
            restored = get_source_workspace(list_sources(target)[0]["id"], target)
            self.assertEqual(restored["segments"][0]["text"], "Original readable notes.")
            original, _, _ = get_capture_file(restored["source"]["id"], target.parent / "content", target)
            self.assertEqual(original.read_bytes(), b"Original readable notes.")
