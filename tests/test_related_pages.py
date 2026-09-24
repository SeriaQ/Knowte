import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from knowte.related_pages import discover_pages, select_pages, page_url
from knowte.knowledge import (
    save_source, list_sources, create_evidence_proposal,
    accept_evidence_proposal, discard_claim_proposal,
)


class RelatedPagesTests(unittest.TestCase):
    def test_ten_pages_can_be_selected(self):
        from knowte.related_pages import MAX_PAGES
        self.assertEqual(MAX_PAGES, 10)
        client = MagicMock()
        pages = [{"id": str(i)} for i in range(10)]
        client.chat_json.return_value = {"page_ids": [p["id"] for p in pages], "summary": "All relevant"}
        selected, _ = select_pages(client, pages, "focus", 10, None)
        self.assertEqual(len(selected), 10)

    def test_directory_respects_version_and_deduplicates(self):
        source = {"id": "seed", "title": "Introduction", "url": "https://example.org/en/latest/user/intro.html"}
        html = '''<a href="../algorithms/ppo.html">PPO</a>
          <a href="../algorithms/ppo.html#one">Duplicate</a>
          <a href="/en/old/ppo.html">Old</a><a href="https://other.org/x">Other</a>'''
        with patch("knowte.related_pages._read", side_effect=[html, '<urlset><url><loc>https://example.org/en/latest/td3.html</loc></url></urlset>']):
            pages, warnings = discover_pages([source])
        self.assertEqual(len(pages), 3)
        self.assertEqual(pages[1]["title"], "PPO")
        self.assertFalse(warnings)
        self.assertEqual(page_url("https://example.org/page?id=2#section"), "https://example.org/page?id=2")

    def test_selector_is_one_call_and_rejects_invalid_ids(self):
        client = MagicMock()
        pages = [{"id": "a"}, {"id": "b"}]
        for ids, valid in [(["a"], True), ([], True), (["unknown"], False), (["a", "a"], False), ([{}], False)]:
            client.reset_mock()
            client.chat_json.return_value = {"page_ids": ids, "summary": "Selection"}
            if valid:
                result, _ = select_pages(client, pages, "focus", 2, None)
                self.assertEqual(len(result), len(ids))
            else:
                with self.assertRaises(ValueError):
                    select_pages(client, pages, "focus", 2, None)
            self.assertEqual(client.chat_json.call_count, 1)

    def test_related_source_is_created_only_on_acceptance_and_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "knowledge.db"
            parent = save_source({"title": "Intro", "url": "https://example.org/intro", "result_type": "web"}, path=path)[0]
            payload = {"source_id": "pending-page", "quote": "Original passage", "verification": "external_unverified",
                       "source_url": "https://example.org/ppo", "related_source": {
                           "title": "PPO", "url": "https://example.org/ppo", "parent_source_id": parent["id"]}}
            proposal = create_evidence_proposal(payload, "test", path=path)
            self.assertEqual(len(list_sources(path)), 1)
            discard_claim_proposal(proposal["id"], path)
            self.assertEqual(len(list_sources(path)), 1)
            for _ in range(2):
                proposal = create_evidence_proposal(payload, "test", path=path)
                evidence = accept_evidence_proposal(proposal["id"], path=path)
                self.assertNotEqual(evidence["source_id"], parent["id"])
                self.assertEqual(len(list_sources(path)), 2)
