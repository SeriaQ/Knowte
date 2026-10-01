import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from knowte.knowledge import (
    save_source, store_capture, create_evidence_proposal, create_claim_proposal,
    accept_evidence_proposal, accept_claim_proposal, discard_claim_proposal,
    list_claim_proposals, list_evidence_proposals, list_claims, list_evidence, update_evidence,
    revise_claim, delete_evidence,
)


class ProposalDependencyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / "knowte.db"
        source, _, _ = save_source({"title": "RL", "url": "https://example.org/rl"}, path=self.db)
        workspace = store_capture(source["id"], {
            "url": source["url"], "media_type": "text/html", "sha256": "test",
            "raw_path": "", "segments": ["Policy gradients estimate expected return. Value functions estimate future rewards."],
            "locators": ["Theory"],
        }, self.db)
        self.source_id = source["id"]
        self.segment_id = workspace["segments"][0]["id"]

    def evidence(self, quote="Policy gradients estimate expected return."):
        return create_evidence_proposal({"source_id": self.source_id, "segment_id": self.segment_id,
            "quote": quote}, "test", path=self.db)

    def claim(self, parents, statement="A grounded conclusion"):
        return create_claim_proposal({"statement": statement, "basis": "inference", "evidence": [
            {"evidence_id": "proposal:" + p["id"], "stance": "supports"} for p in parents]}, "test", path=self.db)

    def pending(self, proposal):
        return next(p for p in list_claim_proposals(self.db) if p["id"] == proposal["id"])

    def test_pending_stays_pending_and_acceptance_promotes_without_generation(self):
        evidence = self.evidence()
        claim = self.claim([evidence])
        self.assertEqual(list_claims(self.db), [])
        self.assertEqual(list_evidence(self.db), [])
        self.assertEqual(len(list_evidence_proposals(self.db)), 1)
        self.assertEqual(self.pending(claim)["derivation"]["pending_count"], 1)
        with self.assertRaisesRegex(ValueError, "upstream"):
            accept_claim_proposal(claim["id"], path=self.db)
        accepted = accept_evidence_proposal(evidence["id"], path=self.db)
        pending = self.pending(claim)
        self.assertEqual(pending["status"], "awaiting_review")
        self.assertEqual(pending["derivation"]["pending_count"], 0)
        self.assertEqual(pending["payload"]["evidence"][0]["evidence_id"], accepted["id"])
        accept_claim_proposal(claim["id"], path=self.db)
        with sqlite3.connect(self.db) as connection:
            outcomes = connection.execute("SELECT decision, result_id FROM proposal_outcomes").fetchall()
        self.assertEqual(len(outcomes), 2)
        self.assertTrue(all(row[0] == "accepted" and row[1] for row in outcomes))

    def test_logical_edit_stales_descendants_and_does_not_auto_accept(self):
        evidence = self.evidence()
        left = self.claim([evidence], "Left")
        right = self.claim([evidence], "Right")
        relation = create_claim_proposal({"operation": "create_relation", "relation_type": "related",
            "subject_claim_id": "proposal:" + left["id"], "object_claim_id": "proposal:" + right["id"]}, "test", path=self.db)
        accept_evidence_proposal(evidence["id"], {"quote": "Value functions estimate future rewards."}, self.db)
        for proposal in (left, right, relation):
            self.assertEqual(self.pending(proposal)["derivation"]["status"], "stale")
            self.assertEqual(self.pending(proposal)["status"], "awaiting_review")
            with self.assertRaisesRegex(ValueError, "Recompute"):
                accept_claim_proposal(proposal["id"], path=self.db)

    def test_reject_only_dependency_invalidates_but_partial_support_needs_recompute(self):
        first, second = self.evidence(), self.evidence("Value functions estimate future rewards.")
        only = self.claim([first], "Single input")
        combined = self.claim([first, second], "Combined inputs")
        discard_claim_proposal(first["id"], self.db)
        self.assertEqual(self.pending(only)["derivation"]["status"], "invalidated")
        self.assertEqual(self.pending(combined)["derivation"]["status"], "stale")
        accept_evidence_proposal(second["id"], path=self.db)
        self.assertEqual(self.pending(combined)["derivation"]["status"], "stale")
        with sqlite3.connect(self.db) as connection:
            outcome = connection.execute("SELECT payload_json, decision FROM proposal_outcomes WHERE proposal_id = ?", (first["id"],)).fetchone()
        self.assertEqual(json.loads(outcome[0])["quote"], first["payload"]["quote"])
        self.assertEqual(outcome[1], "rejected")

    def test_tag_edit_does_not_stale_logical_dependencies(self):
        evidence = self.evidence()
        claim = self.claim([evidence])
        accept_evidence_proposal(evidence["id"], {"tags": ["RL"]}, self.db)
        self.assertEqual(self.pending(claim)["derivation"]["status"], "current")
        self.assertNotIn("blocked_reason", self.pending(claim)["payload"])

    def test_resolving_ids_does_not_invalidate_next_level_version(self):
        evidence = self.evidence()
        left, right = self.claim([evidence], "Left"), self.claim([evidence], "Right")
        relation = create_claim_proposal({"operation": "create_relation", "relation_type": "supports",
            "subject_claim_id": "proposal:" + left["id"], "object_claim_id": "proposal:" + right["id"]}, "test", path=self.db)
        accept_evidence_proposal(evidence["id"], path=self.db)
        accept_claim_proposal(left["id"], path=self.db)
        accept_claim_proposal(right["id"], path=self.db)
        self.assertEqual(self.pending(relation)["derivation"]["status"], "current")
        accept_claim_proposal(relation["id"], path=self.db)

    def test_unknown_parent_rolls_back_child_creation(self):
        with self.assertRaisesRegex(ValueError, "dependency"):
            self.claim([{"id": "missing"}])
        self.assertEqual(list_claim_proposals(self.db), [])

    def test_revised_accepted_claim_stales_pending_relation(self):
        evidence = self.evidence()
        left, right = self.claim([evidence], "Left"), self.claim([evidence], "Right")
        relation = create_claim_proposal({"operation": "create_relation", "relation_type": "related",
            "subject_claim_id": "proposal:" + left["id"], "object_claim_id": "proposal:" + right["id"]}, "test", path=self.db)
        accept_evidence_proposal(evidence["id"], path=self.db)
        accepted = accept_claim_proposal(left["id"], path=self.db)
        revise_claim(accepted["id"], {"statement": "Changed meaning"}, self.db)
        self.assertEqual(self.pending(relation)["derivation"]["status"], "stale")

    def test_deleted_accepted_evidence_invalidates_pending_claim(self):
        evidence = self.evidence()
        claim = self.claim([evidence])
        accepted = accept_evidence_proposal(evidence["id"], path=self.db)
        delete_evidence(accepted["id"], self.db)
        self.assertEqual(self.pending(claim)["derivation"]["status"], "invalidated")

    def test_later_evidence_edit_propagates_and_cosmetic_waiver_preserves_state(self):
        proposal = self.evidence()
        claim = self.claim([proposal])
        evidence = accept_evidence_proposal(proposal["id"], path=self.db)
        evidence = next(item for item in list_evidence(self.db) if item["id"] == evidence["id"])
        update_evidence(evidence["id"], {"revision": evidence["revision"], "quote": "Cosmetic edit", "ignore_logical_impact": True}, self.db)
        self.assertEqual(self.pending(claim)["derivation"]["status"], "current")
        update_evidence(evidence["id"], {"revision": evidence["revision"] + 1, "quote": "Logical edit"}, self.db)
        self.assertEqual(self.pending(claim)["derivation"]["status"], "stale")
        update_evidence(evidence["id"], {"revision": evidence["revision"] + 2, "quote": "Later cosmetic edit", "ignore_logical_impact": True}, self.db)
        self.assertEqual(self.pending(claim)["derivation"]["status"], "stale")

    def test_legacy_ignored_edits_keep_existing_fingerprint(self):
        from knowte.proposal_dependencies import evidence_input
        proposal = self.evidence()
        accepted = accept_evidence_proposal(proposal["id"], path=self.db)
        evidence = list_evidence(self.db)[0]
        edited = update_evidence(accepted["id"], {"revision": evidence["revision"], "quote": "Legacy cosmetic edit", "ignore_logical_impact": True}, self.db)
        with sqlite3.connect(self.db) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute("SELECT snapshot_json FROM evidence_revisions WHERE evidence_id = ?", (accepted["id"],)).fetchone()
            snapshot = json.loads(row[0]); snapshot.pop("logical_version_preserved")
            connection.execute("UPDATE evidence_revisions SET snapshot_json = ? WHERE evidence_id = ?", (json.dumps(snapshot), accepted["id"]))
            before = evidence_input(connection, accepted["id"])
            self.assertEqual(before["logical_quote"], "Legacy cosmetic edit")
        update_evidence(accepted["id"], {"revision": edited["revision"], "quote": "New cosmetic edit", "ignore_logical_impact": True}, self.db)
        with sqlite3.connect(self.db) as connection:
            connection.row_factory = sqlite3.Row
            after = evidence_input(connection, accepted["id"])
        self.assertEqual(before["input_version"], after["input_version"])
        self.assertEqual(after["quote"], "New cosmetic edit")
