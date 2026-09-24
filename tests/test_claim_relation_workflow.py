import tempfile
import unittest
from pathlib import Path

from knowte.knowledge import (
    accept_claim_proposal, create_claim_proposal, create_claim_relation,
    discard_claim_proposal, get_claim, list_claim_proposals, preview_claim_audit,
)


class ClaimRelationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db = Path(self.directory.name) / "knowte.db"

    def draft(self, statement):
        return create_claim_proposal({"statement": statement, "basis": "background",
                                      "intentionally_ungrounded": True}, "test", path=self.db)

    def relation(self, left, right):
        return create_claim_proposal({"operation": "create_relation",
            "subject_claim_id": "proposal:" + left["id"], "object_claim_id": "proposal:" + right["id"],
            "relation_type": "supports", "rationale": "Concrete inference"}, "test", path=self.db)

    def test_new_endpoints_resolve_but_relation_requires_own_acceptance(self):
        left, right = self.draft("Premise"), self.draft("Conclusion")
        relation = self.relation(left, right)
        with self.assertRaisesRegex(ValueError, "both endpoint"):
            accept_claim_proposal(relation["id"], path=self.db)
        a = accept_claim_proposal(left["id"], {"statement": "Reviewed premise"}, self.db)
        with self.assertRaisesRegex(ValueError, "both endpoint"):
            accept_claim_proposal(relation["id"], path=self.db)
        b = accept_claim_proposal(right["id"], path=self.db)
        self.assertEqual(get_claim(a["id"], self.db)["relations"], [])
        pending = list_claim_proposals(self.db)[0]["payload"]
        self.assertEqual(pending["subject_statement"], "Reviewed premise")
        self.assertEqual(pending["object_claim_id"], b["id"])
        accept_claim_proposal(relation["id"], path=self.db)
        self.assertEqual(len(get_claim(a["id"], self.db)["relations"]), 1)

    def test_discarded_endpoint_retains_explicitly_blocked_relation(self):
        left, right = self.draft("Premise"), self.draft("Conclusion")
        relation = self.relation(left, right)
        discard_claim_proposal(left["id"], self.db)
        self.assertTrue(any(p["id"] == relation["id"] for p in list_claim_proposals(self.db)))
        with self.assertRaisesRegex(ValueError, "discarded"):
            accept_claim_proposal(relation["id"], path=self.db)

    def test_audit_includes_existing_links_without_lexical_similarity(self):
        a = accept_claim_proposal(self.draft("Apples")['id'], path=self.db)
        b = accept_claim_proposal(self.draft("Oranges")['id'], path=self.db)
        self.assertEqual(preview_claim_audit(path=self.db)["candidate_count"], 0)
        create_claim_relation({"subject_claim_id": a["id"], "object_claim_id": b["id"],
                               "relation_type": "related"}, self.db)
        self.assertEqual(preview_claim_audit(path=self.db)["candidate_count"], 1)

    def test_relation_replacement_removal_and_stale_guard(self):
        a = accept_claim_proposal(self.draft("Premise")['id'], path=self.db)
        b = accept_claim_proposal(self.draft("Conclusion")['id'], path=self.db)
        old = create_claim_relation({"subject_claim_id": a["id"], "object_claim_id": b["id"],
                                    "relation_type": "related", "rationale": "Old"}, self.db)
        def propose(kind):
            return create_claim_proposal({"operation": "revise_relation", "existing_relation": old,
                "subject_claim_id": b["id"], "object_claim_id": a["id"],
                "relation_type": kind, "rationale": "Reviewed"}, "test", path=self.db)
        replacement, stale = propose("supports"), propose("remove")
        accept_claim_proposal(replacement["id"], path=self.db)
        edges = get_claim(a["id"], self.db)["relations"]
        self.assertEqual([(r["subject_claim_id"], r["relation_type"]) for r in edges], [(b["id"], "supports")])
        with self.assertRaisesRegex(ValueError, "changed"):
            accept_claim_proposal(stale["id"], path=self.db)
        old = edges[0]
        removal = propose("remove")
        accept_claim_proposal(removal["id"], path=self.db)
        self.assertEqual(get_claim(a["id"], self.db)["relations"], [])
