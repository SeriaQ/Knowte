import sqlite3
import tempfile
import unittest
from pathlib import Path

from knowte.knowledge import (
    save_source, create_evidence_proposal, create_claim_proposal, get_wiki,
    accept_evidence_proposal, accept_claim_proposal, discard_claim_proposal,
    list_claims, list_claim_proposals,
)


class WikiProjectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / "knowte.db"
        source, _, _ = save_source({"title": "RL", "url": "https://example.org/rl"}, path=self.db)
        self.evidence = create_evidence_proposal({"source_id": source["id"],
            "quote": "Policies select actions.", "verification": "external_unverified"}, "test", path=self.db)
        self.left = self.claim("Policies select actions")
        self.right = self.claim("Actions affect rewards")
        self.relation = create_claim_proposal({"operation": "create_relation", "relation_type": "related",
            "subject_claim_id": "proposal:" + self.left["id"],
            "object_claim_id": "proposal:" + self.right["id"]}, "test", path=self.db)

    def claim(self, statement):
        return create_claim_proposal({"statement": statement, "basis": "reported", "evidence": [
            {"evidence_id": "proposal:" + self.evidence["id"], "stance": "supports"}]}, "test", path=self.db)

    def test_projection_does_not_accept_or_write_reviewed_knowledge(self):
        before = get_wiki(self.db)
        projected = get_wiki(self.db, projected=True)
        self.assertEqual(len(projected["claims"]), 2)
        self.assertEqual(len(projected["graph"]["edges"]), 1)
        self.assertEqual(len(projected["projection"]["pending_proposal_ids"]), 3)
        self.assertTrue(all(c["projection"]["review_status"] == "awaiting_review" for c in projected["claims"]))
        self.assertEqual(get_wiki(self.db), before)
        self.assertEqual(list_claims(self.db), [])
        self.assertEqual(len(list_claim_proposals(self.db)), 3)

    def test_acceptance_promotes_without_duplicates_or_model_calls(self):
        accept_evidence_proposal(self.evidence["id"], path=self.db)
        accepted = accept_claim_proposal(self.left["id"], path=self.db)
        projected = get_wiki(self.db, projected=True)
        self.assertEqual(len(projected["claims"]), 2)
        self.assertIn(accepted["id"], {c["id"] for c in projected["claims"]})
        self.assertEqual(projected["graph"]["edges"][0]["subject_claim_id"], accepted["id"])
        self.assertEqual(len(projected["projection"]["pending_proposal_ids"]), 2)

    def test_rejection_excludes_entire_invalid_branch(self):
        discard_claim_proposal(self.evidence["id"], self.db)
        projected = get_wiki(self.db, projected=True)
        self.assertEqual(projected["claims"], [])
        self.assertEqual(projected["graph"]["edges"], [])
        self.assertEqual(len(projected["projection"]["excluded_proposal_ids"]), 3)

    def test_changed_inputs_exclude_stale_descendants(self):
        accept_evidence_proposal(self.evidence["id"], {"quote": "Changed meaning."}, self.db)
        projected = get_wiki(self.db, projected=True)
        self.assertEqual(projected["claims"], [])
        self.assertEqual(len(projected["projection"]["excluded_proposal_ids"]), 3)

    def test_missing_endpoint_never_draws_a_dangling_edge(self):
        with sqlite3.connect(self.db) as connection:
            connection.execute("DELETE FROM review_proposals WHERE id = ?", (self.left["id"],))
        projected = get_wiki(self.db, projected=True)
        self.assertEqual(projected["graph"]["edges"], [])
        self.assertIn(self.relation["id"], projected["projection"]["excluded_proposal_ids"])

    def test_pending_links_stay_separate_from_reviewed_evidence(self):
        accept_evidence_proposal(self.evidence["id"], path=self.db)
        accepted = accept_claim_proposal(self.left["id"], path=self.db)
        proposal = create_claim_proposal({"operation": "link_evidence", "target_claim_id": accepted["id"],
            "evidence": []}, "test", path=self.db)
        original = get_wiki(self.db)
        projected = get_wiki(self.db, projected=True)
        claim = next(c for c in projected["claims"] if c["id"] == accepted["id"])
        self.assertEqual(claim["evidence"], accepted["evidence"])
        self.assertEqual(claim["pending_evidence"][0]["proposal_id"], proposal["id"])
        self.assertEqual(get_wiki(self.db), original)

    def test_merge_replaces_both_claims_only_in_projection(self):
        accept_evidence_proposal(self.evidence["id"], path=self.db)
        left = accept_claim_proposal(self.left["id"], path=self.db)
        right = accept_claim_proposal(self.right["id"], path=self.db)
        proposal = create_claim_proposal({"operation": "merge_claims", "source_claim_id": left["id"],
            "target_claim_id": right["id"], "merged_statement": "Combined"}, "test", path=self.db)
        projected = get_wiki(self.db, projected=True)
        self.assertIn(proposal["id"], projected["projection"]["pending_proposal_ids"])
        self.assertEqual(len(projected["claims"]), 1)
        self.assertEqual(projected["claims"][0]["statement"], "Combined")
        self.assertEqual(len(get_wiki(self.db)["claims"]), 2)


if __name__ == "__main__":
    unittest.main()
