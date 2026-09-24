import tempfile
import unittest
from pathlib import Path
from knowte.knowledge import (
    save_source, list_sources, create_evidence_proposal, accept_evidence_proposal,
    create_claim, list_claims, list_evidence, list_claim_proposals, update_evidence,
    preview_knowledge_deletion, delete_knowledge_items, add_entity_tags_batch,
    create_wiki_proposal, accept_wiki_proposal, get_wiki, prepare_wiki_batch,
    merge_wiki_batch, revise_claim,
)


class BatchKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "knowte.db"

    def source(self, number=0):
        return save_source({"title": f"Source {number}", "url": f"https://example.org/{number}"}, path=self.path)[0]

    def test_tags_over_two_hundred(self):
        ids = [self.source(i)["id"] for i in range(205)]
        result = add_entity_tags_batch("source", ids, ["RL"], self.path)
        self.assertEqual(len(result), 205)
        self.assertTrue(all(tags[0]["name"] == "RL" for tags in result.values()))
        with self.assertRaises(ValueError):
            add_entity_tags_batch("source", ids + ["missing"], ["Must not be added"], self.path)
        self.assertTrue(all(len(item["tags"]) == 1 for item in list_sources(self.path)))

    def test_source_deletion_requires_fresh_impact_and_rechecks_claims(self):
        source = self.source()
        draft = create_evidence_proposal({"source_id": source["id"], "quote": "Evidence", "verification": "external_unverified"}, "test", path=self.path)
        evidence = accept_evidence_proposal(draft["id"], path=self.path)
        claim = create_claim({"statement": "A claim", "basis": "reported", "evidence": [{"evidence_id": evidence["id"], "stance": "supports"}]}, self.path)
        self.assertEqual(list_sources(self.path)[0]["evidence_count"], 1)
        plan = preview_knowledge_deletion("source", [source["id"]], self.path)
        self.assertEqual((plan["sources"], plan["evidence"], plan["recheck_claims"]), (1, 1, 1))
        update_evidence(evidence["id"], {"revision": 1, "quote": "Updated"}, self.path)
        with self.assertRaisesRegex(ValueError, "changed"):
            delete_knowledge_items("source", [source["id"]], plan["token"], self.path)
        plan = preview_knowledge_deletion("source", [source["id"]], self.path)
        delete_knowledge_items("source", [source["id"]], plan["token"], self.path)
        self.assertEqual(list_sources(self.path), [])
        self.assertEqual(list_evidence(self.path), [])
        kept = list_claims(self.path)[0]
        self.assertEqual(kept["id"], claim["id"])
        self.assertTrue(kept["needs_review"])
        self.assertEqual(kept["evidence"], [])
        review = list_claim_proposals(self.path)
        self.assertEqual(len(review), 1)
        self.assertTrue(review[0]["payload"]["changes"][0]["deleted"])

    def test_wiki_priority_merge_and_stale_preservation(self):
        first, second, third = [create_claim({"statement": str(i), "basis": "background", "intentionally_ungrounded": True}, self.path) for i in range(3)]
        draft = create_wiki_proposal({"pages": [{"key": "home", "title": "Home", "claim_ids": [first["id"], second["id"]]}]}, "test", path=self.path)
        accept_wiki_proposal(draft["id"], self.path)
        wiki = get_wiki(self.path)
        # Explicit versions avoid wall-clock timing in this priority test.
        import sqlite3
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE claims SET updated_at = '2099-01-01' WHERE id IN (?, ?)", (first["id"], second["id"]))
        wiki = get_wiki(self.path)
        selected, scope = prepare_wiki_batch(wiki, 1)
        self.assertIn(selected[0]["id"], {first["id"], second["id"]})
        self.assertNotEqual(selected[0]["id"], third["id"])
        merged = merge_wiki_batch({"pages": [{"key": "new", "title": "New", "claim_ids": scope["claim_ids"]}]}, wiki, scope["claim_ids"])
        draft = create_wiki_proposal(merged, "test", scope=scope, path=self.path)
        accepted = accept_wiki_proposal(draft["id"], self.path)
        self.assertEqual(sum(len(page["claim_ids"]) for page in accepted["pages"]), 2)
        self.assertEqual(accepted["unorganized_claim_ids"], [third["id"]])
        self.assertEqual(len(accepted["stale_claim_ids"]), 1)
        self.assertNotIn(selected[0]["id"], accepted["stale_claim_ids"])
        with self.assertRaisesRegex(ValueError, "every selected"):
            merge_wiki_batch({"pages": []}, accepted, [third["id"]])
        with self.assertRaisesRegex(ValueError, "structure changed"):
            draft = create_wiki_proposal(merged, "test", scope=scope, path=self.path)
            accept_wiki_proposal(draft["id"], self.path)
