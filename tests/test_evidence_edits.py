import tempfile
import unittest
from pathlib import Path

from knowte.knowledge import (save_source, create_evidence_proposal,
    accept_evidence_proposal, create_claim, list_claims, list_evidence,
    update_evidence, list_claim_proposals, accept_claim_proposal,
    discard_claim_proposal, set_entity_tags, revise_claim, get_source_workspace, get_wiki)
from knowte.exports import build_knowledge_export


class EvidenceEditTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "knowte.db"
        source = save_source({"title": "Original", "url": "https://example.org", "result_type": "web"}, path=self.path)[0]
        proposal = create_evidence_proposal({"source_id": source["id"], "quote": "Original excerpt", "locator": "Section 1", "verification": "external_unverified"}, "test", path=self.path)
        self.evidence = accept_evidence_proposal(proposal["id"], path=self.path)
        self.claim = create_claim({"statement": "A grounded claim", "basis": "reported", "evidence": [{"evidence_id": self.evidence["id"], "stance": "supports"}]}, self.path)

    def edit(self, revision=1, quote="Corrected excerpt"):
        return update_evidence(self.evidence["id"], {"revision": revision, "quote": quote, "locator": "Section 2"}, self.path)

    def test_history_deduplication_and_stale_review(self):
        self.assertEqual(self.edit()["affected_claims"], 1)
        old = list_claim_proposals(self.path)[0]
        self.edit(2, "Latest excerpt")
        current = list_claim_proposals(self.path)
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["id"], old["id"])
        self.assertEqual(current[0]["payload"]["changes"][0]["before_quote"], "Original excerpt")
        self.assertTrue(list_claims(self.path)[0]["needs_review"])
        evidence = list_evidence(self.path)[0]
        self.assertEqual(evidence["revision"], 3)
        self.assertEqual(len(evidence["history"]), 2)
        with self.assertRaises(ValueError):
            accept_claim_proposal(old["id"], {"change_token": old["payload"]["change_token"]}, self.path)
        accepted = accept_claim_proposal(current[0]["id"], {"change_token": current[0]["payload"]["change_token"], "statement": "Rechecked claim"}, self.path)
        self.assertEqual(accepted["id"], self.claim["id"])
        self.assertFalse(accepted["needs_review"])
        self.assertEqual(accepted["statement"], "Rechecked claim")
        self.assertEqual(len(accepted["revisions"]), 2)
        self.assertEqual(accepted["evidence"][0]["evidence_id"], self.evidence["id"])

    def test_noop_tags_stale_edit_and_withdraw(self):
        result = update_evidence(self.evidence["id"], {"revision": 1, "quote": "Original excerpt", "locator": "Section 1"}, self.path)
        self.assertEqual(result["affected_claims"], 0)
        set_entity_tags("evidence", self.evidence["id"], ["RL"], self.path)
        self.assertFalse(list_claim_proposals(self.path))
        self.edit()
        with self.assertRaises(ValueError):
            self.edit()
        pending = list_claim_proposals(self.path)[0]
        with self.assertRaises(ValueError):
            discard_claim_proposal(pending["id"], self.path)
        claim = accept_claim_proposal(pending["id"], {"change_token": pending["payload"]["change_token"], "review_state": "withdrawn"}, self.path)
        self.assertEqual(claim["lifecycle"], "withdrawn")
        self.assertEqual(len(claim["evidence"]), 1)
        self.assertFalse(list_claim_proposals(self.path))

    def test_separate_claim_revision_refreshes_review(self):
        self.edit()
        old = list_claim_proposals(self.path)[0]
        revise_claim(self.claim["id"], {"statement": "Separately revised claim"}, self.path)
        fresh = list_claim_proposals(self.path)[0]
        self.assertNotEqual(fresh["payload"]["change_token"], old["payload"]["change_token"])
        self.assertEqual(fresh["payload"]["statement"], "Separately revised claim")

    def test_pending_claim_not_exported_as_reviewed_and_reader_keeps_history(self):
        self.edit()
        with self.assertRaisesRegex(ValueError, "Evidence-changed"):
            build_knowledge_export("wiki", [], self.path, Path(self.directory.name) / "content")
        evidence = list_evidence(self.path)[0]
        workspace = get_source_workspace(evidence["source_id"], self.path)
        self.assertEqual(workspace["evidence"][0]["history"][0]["quote"], "Original excerpt")
        self.assertFalse(get_wiki(self.path)["graph"]["nodes"])
