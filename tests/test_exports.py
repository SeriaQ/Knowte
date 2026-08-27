import base64
import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from knowte.exports import build_knowledge_export
from knowte.imports import (
    accept_project_import,
    accept_wiki_import,
    stage_project_package_import,
    stage_wiki_package_import,
)
from knowte.knowledge import (
    accept_wiki_proposal,
    create_artifact,
    create_claim,
    create_evidence,
    create_wiki_proposal,
    get_project,
    get_wiki,
    list_wiki_imports,
    link_project_knowledge,
    list_claims,
    save_source,
    store_capture,
)
from knowte.server import create_server


class KnowledgeExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = self.root / "knowte.db"
        self.content = self.root / "content"
        source, _, _ = save_source({
            "title": "Qwen Report", "url": "https://example.test/qwen",
        }, path=self.database)
        workspace = store_capture(source["id"], {
            "url": source["url"], "media_type": "text/html",
            "sha256": "export-test", "raw_path": str(self.content / "source.html"),
            "segments": ["Qwen uses grouped-query attention for efficient inference."],
            "locators": ["Architecture"],
        }, self.database)
        segment = workspace["segments"][0]
        self.evidence = create_evidence({
            "segment_id": segment["id"], "quote": segment["text"],
            "start_offset": 0, "end_offset": len(segment["text"]),
        }, self.database)
        self.claim = create_claim({
            "statement": "Qwen uses grouped-query attention.", "basis": "reported",
            "evidence": [{"evidence_id": self.evidence["id"], "stance": "supports"}],
        }, self.database)

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def _archive(body):
        return ZipFile(BytesIO(body))

    def test_wiki_export_contains_all_active_claims_including_unorganized(self):
        proposal = create_wiki_proposal({
            "summary": "Organize Qwen knowledge.",
            "pages": [{"key": "qwen", "title": "Qwen", "parent_key": "",
                       "claim_ids": [self.claim["id"]]}],
        }, "wiki-maintainer-v1", path=self.database)
        accept_wiki_proposal(proposal["id"], self.database)
        unorganized = create_claim({
            "statement": "This reviewed Claim has not been assigned to a Page.",
            "basis": "background",
        }, self.database)
        filename, body = build_knowledge_export("wiki", [], self.database, self.content)
        self.assertRegex(filename, r"^knowte-wiki-\d{8}-\d{6}\.zip$")
        with self._archive(body) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            data = json.loads(archive.read("data.json"))
            markdown = archive.read("content.md").decode("utf-8")
        self.assertEqual(manifest["import_behavior"], "trusted_wiki_review")
        self.assertEqual({item["id"] for item in data["claims"]},
                         {self.claim["id"], unorganized["id"]})
        self.assertIn(unorganized["id"], data["wiki"]["unorganized_claim_ids"])
        self.assertIn("## Unorganized", markdown)

    def test_project_export_closes_over_claim_provenance(self):
        project = create_artifact({
            "title": "Qwen architecture", "purpose": "Understand Qwen design.",
        }, self.database)
        link_project_knowledge(project["id"], "claim", self.claim["id"], self.database)
        filename, body = build_knowledge_export(
            "project", [project["id"]], self.database, self.content,
        )
        self.assertRegex(filename, r"^knowte-project-\d{8}-\d{6}\.zip$")
        with self._archive(body) as archive:
            data = json.loads(archive.read("data.json"))
        self.assertEqual(data["project"]["id"], project["id"])
        self.assertEqual(data["claims"][0]["id"], self.claim["id"])
        self.assertEqual(data["evidence"][0]["id"], self.evidence["id"])
        self.assertEqual(data["sources"][0]["title"], "Qwen Report")

    def test_evidence_and_claims_are_not_export_boundaries(self):
        for kind in ("evidence", "claims"):
            with self.assertRaisesRegex(ValueError, "Wiki or Project"):
                build_knowledge_export(kind, [], self.database, self.content)

    def test_wiki_import_is_reviewed_once_then_merged_with_its_items(self):
        proposal = create_wiki_proposal({
            "summary": "Organize imported knowledge.",
            "pages": [{"key": "qwen", "title": "Qwen", "parent_key": "",
                       "claim_ids": [self.claim["id"]]}],
        }, "wiki-maintainer-v1", path=self.database)
        accept_wiki_proposal(proposal["id"], self.database)
        _, body = build_knowledge_export("wiki", [], self.database, self.content)
        target_root = self.root / "target"
        target_database = target_root / "knowte.db"
        target_content = target_root / "content"
        staged = stage_wiki_package_import(
            base64.b64encode(body).decode("ascii"), "shared-wiki.zip",
            target_database, target_content,
        )
        self.assertEqual(list_claims(target_database), [])
        self.assertEqual(get_wiki(target_database)["claims"], [])
        self.assertEqual(list_wiki_imports(target_database)[0]["status"], "awaiting_review")
        result = accept_wiki_import(staged["id"], target_database, target_content)
        self.assertEqual(result["created"]["claims"], 1)
        self.assertEqual(len(list_claims(target_database)), 1)
        self.assertGreaterEqual(len(get_wiki(target_database)["pages"]), 1)

    def test_wiki_and_project_packages_cannot_cross_import_boundaries(self):
        project = create_artifact({"title": "P", "purpose": "Test"}, self.database)
        _, wiki_body = build_knowledge_export("wiki", [], self.database, self.content)
        _, project_body = build_knowledge_export(
            "project", [project["id"]], self.database, self.content,
        )
        with self.assertRaisesRegex(ValueError, "Project package"):
            stage_project_package_import(base64.b64encode(wiki_body).decode(), "wiki.zip",
                                         self.root / "p.db", self.root / "p-content")
        with self.assertRaisesRegex(ValueError, "Wiki package"):
            stage_wiki_package_import(base64.b64encode(project_body).decode(), "project.zip",
                                      self.root / "w.db", self.root / "w-content")

    def test_export_endpoint_returns_a_named_wiki_zip(self):
        config = self.root / "config.yml"
        server = create_server("127.0.0.1", 0, config)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        connection = HTTPConnection("127.0.0.1", server.server_address[1])
        try:
            connection.request(
                "POST", "/api/exports", body=json.dumps({"type": "wiki", "ids": []}),
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            body = response.read()
            disposition = response.getheader("Content-Disposition")
        finally:
            connection.close()
            server.shutdown(); server.server_close(); thread.join()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("Content-Type"), "application/zip")
        self.assertRegex(disposition, r'attachment; filename="knowte-wiki-.*\.zip"')
        with self._archive(body) as archive:
            self.assertIn("content.md", archive.namelist())


if __name__ == "__main__":
    unittest.main()
