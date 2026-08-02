import tempfile
import threading
import unittest
import base64
from pathlib import Path

from knowte.knowledge import (
    canonical_source_key,
    create_annotation,
    create_artifact,
    create_evidence,
    delete_annotation,
    delete_evidence,
    get_source_workspace,
    list_artifacts,
    list_sources,
    save_source,
    set_entity_tags,
    store_capture,
)


class KnowledgeStoreTests(unittest.TestCase):
    def test_artifact_requires_title_and_purpose(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            with self.assertRaisesRegex(ValueError, "title is required"):
                create_artifact({"purpose": "Understand a topic."}, database)
            with self.assertRaisesRegex(ValueError, "purpose is required"):
                create_artifact({"title": "Topic"}, database)

    def test_source_is_global_and_artifact_links_are_idempotent(self):
        source_payload = {
            "id": "https://arxiv.org/abs/2401.12345v2",
            "title": "Open model systems",
            "authors": "A. Researcher",
            "year": 2026,
            "abstract": "A useful source.",
            "url": "https://arxiv.org/abs/2401.12345",
            "paper_url": "https://arxiv.org/abs/2401.12345",
            "pdf_url": "https://arxiv.org/pdf/2401.12345",
            "doi_url": "https://doi.org/10.1000/example",
            "source": "arXiv",
            "result_type": "paper",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            artifact = create_artifact(
                {
                    "title": "Open LLM frontier",
                    "purpose": "Understand current open model technology.",
                },
                database,
            )

            first, first_created, first_link = save_source(
                source_payload,
                artifact["id"],
                database,
            )
            second, second_created, second_link = save_source(
                {**source_payload, "title": "Updated title"},
                artifact["id"],
                database,
            )

            self.assertTrue(first_created)
            self.assertTrue(first_link)
            self.assertFalse(second_created)
            self.assertFalse(second_link)
            self.assertEqual(first["id"], second["id"])
            self.assertEqual(second["title"], "Updated title")
            self.assertEqual(len(list_sources(database)), 1)
            self.assertEqual(list_artifacts(database)[0]["source_count"], 1)

    def test_canonical_key_prefers_doi_then_arxiv_then_url(self):
        self.assertEqual(
            canonical_source_key(
                {
                    "doi_url": "https://doi.org/10.1234/ABC",
                    "url": "https://example.test/paper",
                }
            ),
            "doi:10.1234/abc",
        )
        self.assertEqual(
            canonical_source_key(
                {"url": "https://arxiv.org/abs/2501.01234v3"}
            ),
            "arxiv:2501.01234",
        )
        self.assertEqual(
            canonical_source_key(
                {"url": "HTTPS://Example.Test/article/#section"}
            ),
            "url:https://example.test/article",
        )

    def test_first_reads_can_initialize_database_concurrently(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            start = threading.Barrier(3)
            errors = []

            def read_library(reader):
                start.wait()
                try:
                    reader(database)
                except Exception as error:  # pragma: no cover - assertion aid
                    errors.append(error)

            threads = [
                threading.Thread(target=read_library, args=(list_artifacts,)),
                threading.Thread(target=read_library, args=(list_sources,)),
            ]
            for thread in threads:
                thread.start()
            start.wait()
            for thread in threads:
                thread.join()

            self.assertEqual(errors, [])

    def test_capture_evidence_and_annotations_preserve_provenance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            source, _, _ = save_source(
                {
                    "title": "Qwen report",
                    "url": "https://example.test/qwen",
                    "source": "Web",
                    "result_type": "web",
                },
                path=database,
            )
            text = "Qwen uses a mixture of techniques for efficient inference."
            workspace = store_capture(
                source["id"],
                {
                    "url": "https://example.test/qwen",
                    "media_type": "text/html",
                    "sha256": "abc",
                    "raw_path": str(Path(temp_dir) / "abc.html"),
                    "segments": [text],
                },
                database,
            )
            segment = workspace["segments"][0]
            quote = "mixture of techniques"
            start = text.index(quote)
            evidence = create_evidence(
                {
                    "segment_id": segment["id"],
                    "quote": quote,
                    "start_offset": start,
                    "end_offset": start + len(quote),
                },
                database,
            )
            source_note = create_annotation(
                {
                    "target_type": "source",
                    "target_id": source["id"],
                    "body": "Read the evaluation section.",
                },
                database,
            )
            evidence_note = create_annotation(
                {
                    "target_type": "evidence",
                    "target_id": evidence["id"],
                    "body": "Potential support for the inference-efficiency Claim.",
                },
                database,
            )
            loaded = get_source_workspace(source["id"], database)

            self.assertEqual(loaded["source"]["capture_state"], "captured")
            self.assertEqual(loaded["evidence"][0]["quote"], quote)
            self.assertEqual(loaded["annotations"][0]["id"], source_note["id"])
            self.assertEqual(
                loaded["evidence"][0]["annotations"][0]["id"],
                evidence_note["id"],
            )
            tags = set_entity_tags(
                "evidence", evidence["id"], ["Architecture", "Qwen"], database
            )
            self.assertEqual([tag["name"] for tag in tags], ["Architecture", "Qwen"])
            loaded = get_source_workspace(source["id"], database)
            self.assertEqual(len(loaded["evidence"][0]["tags"]), 2)
            with self.assertRaisesRegex(ValueError, "unsupported tag entity type"):
                set_entity_tags(
                    "annotation", evidence_note["id"], ["Needs review"], database
                )
            self.assertTrue(delete_annotation(evidence_note["id"], database))
            self.assertTrue(delete_evidence(evidence["id"], database))
            loaded = get_source_workspace(source["id"], database)
            self.assertEqual(loaded["evidence"], [])

    def test_evidence_rejects_a_quote_not_in_the_capture(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            source, _, _ = save_source(
                {"title": "Source", "url": "https://example.test"},
                path=database,
            )
            workspace = store_capture(
                source["id"],
                {
                    "url": "https://example.test",
                    "media_type": "text/html",
                    "sha256": "def",
                    "raw_path": str(Path(temp_dir) / "def.html"),
                    "segments": ["Captured text is immutable."],
                },
                database,
            )
            with self.assertRaisesRegex(ValueError, "does not match"):
                create_evidence(
                    {
                        "segment_id": workspace["segments"][0]["id"],
                        "quote": "Invented",
                        "start_offset": 0,
                        "end_offset": 8,
                    },
                    database,
                )

    def test_evidence_accepts_pdf_text_normalization_differences(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            source, _, _ = save_source(
                {"title": "PDF Source", "url": "https://example.test/paper.pdf"},
                path=database,
            )
            workspace = store_capture(
                source["id"],
                {
                    "url": "https://example.test/paper.pdf",
                    "media_type": "application/pdf",
                    "sha256": "pdf-normalization",
                    "raw_path": str(Path(temp_dir) / "paper.pdf"),
                    "segments": ["A multi-\ncolumn PDF uses efficient ﬂow matching."],
                },
                database,
            )
            evidence = create_evidence(
                {
                    "segment_id": workspace["segments"][0]["id"],
                    "quote": "A multicolumn PDF uses efficient flow matching.",
                    "locator": "Page 1",
                },
                database,
            )
            self.assertEqual(evidence["locator"], "Page 1")

    def test_snapshot_evidence_keeps_region_and_image_provenance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            source, _, _ = save_source(
                {"title": "Visual Source", "url": "https://example.test/visual"},
                path=database,
            )
            workspace = store_capture(
                source["id"],
                {
                    "url": "https://example.test/visual.pdf",
                    "media_type": "application/pdf",
                    "sha256": "visual-capture",
                    "raw_path": str(Path(temp_dir) / "content" / "visual.pdf"),
                    "segments": ["Page with a chart."],
                    "locators": ["Page 1"],
                },
                database,
            )
            png = (
                b"\x89PNG\r\n\x1a\n"
                b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            )
            evidence = create_evidence(
                {
                    "evidence_type": "snapshot",
                    "segment_id": workspace["segments"][0]["id"],
                    "locator": "Page 1",
                    "anchor": {
                        "page": 1,
                        "region": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4},
                    },
                    "image_data": (
                        "data:image/png;base64,"
                        + base64.b64encode(png).decode("ascii")
                    ),
                },
                database,
            )
            loaded = get_source_workspace(source["id"], database)

            self.assertEqual(evidence["evidence_type"], "snapshot")
            self.assertTrue(loaded["evidence"][0]["has_snapshot"])
            self.assertEqual(
                loaded["evidence"][0]["anchor"]["region"]["width"],
                0.3,
            )


if __name__ == "__main__":
    unittest.main()
