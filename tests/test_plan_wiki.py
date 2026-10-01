import tempfile
import json
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from knowte.automation import mutate, _database
from knowte.knowledge import (create_claim_proposal, accept_claim_proposal, discard_claim_proposal,
    get_wiki, revise_claim, reset_wiki_structure, create_evidence_proposal, list_claims, list_evidence,
    review_wiki_projection, accept_wiki_proposal, discard_wiki_proposal, update_wiki_proposal,
    list_evidence_proposals, accept_evidence_proposal, list_claim_proposals, update_evidence)
from knowte.plan_runs import queue_run, list_runs, execute_run
from knowte.plan_wiki import execute_wiki_stage, _generate


class PlanWikiTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / "knowte.db"; self.config = self.db.with_name("config.yaml")
        settings = patch("knowte.plan_wiki.load_config", return_value={})
        self.settings = settings.start(); self.addCleanup(settings.stop)
        profiles = patch("knowte.plan_wiki.ai_model_profiles", return_value=[{"id": "m", "capabilities": ["chat"]}])
        profiles.start(); self.addCleanup(profiles.stop)
        action = mutate({"operation": "save_action", "name": "RL", "config": {"query": "RL", "sources": ["arxiv"]}}, self.db)["saved_id"]
        stage = {"enabled": True, "focus": "RL", "model_profile_id": "m"}
        self.plan = mutate({"operation": "save_plan", "name": "RL", "action_ids": [action], "processing": {
            "save_sources": True, "max_new_sources": 20, "evidence": stage, "claims": stage,
            "wiki": {"enabled": True, "model_profile_id": "m"}}}, self.db)["saved_id"]
        self.run, _ = queue_run(self.plan, self.db)
        self.claims = [create_claim_proposal({"statement": text, "basis": "background", "intentionally_ungrounded": True}, "test", path=self.db)
            for text in ("RL studies sequential decision making", "Rewards express objectives")]

    def generate(self, wiki, selected, *args):
        return {"pages": [{"key": c["id"], "title": "Concept " + str(i), "parent_key": "", "summary": c["statement"],
                           "claim_ids": [c["id"]]} for i, c in enumerate(selected)]}, {"chat_requests": 1}

    def test_durable_projection_leaves_reviewed_wiki_unchanged_and_skips_repeat(self):
        before = get_wiki(self.db)
        self.assertTrue(execute_wiki_stage(self.run, self.db, self.config, generate=self.generate))
        projected = get_wiki(self.db, projected=True)
        self.assertEqual(len(projected["pages"]), 2)
        self.assertEqual(projected["projection"]["organization"]["status"], "current")
        self.assertEqual(get_wiki(self.db), before)
        self.assertTrue(execute_wiki_stage(self.run, self.db, self.config, generate=lambda *a: self.fail("No duplicate call")))
        job = list_runs(self.db, run_id=self.run)[0]["knowledge_jobs"][0]
        self.assertEqual(job["stage"], "wiki")
        self.assertEqual(job["report"]["pages"], 2)

    def test_unchanged_acceptance_preserves_pages_without_call(self):
        self.assertTrue(execute_wiki_stage(self.run, self.db, self.config, generate=self.generate))
        accepted = accept_claim_proposal(self.claims[0]["id"], path=self.db)
        wiki = get_wiki(self.db, projected=True)
        self.assertEqual(wiki["projection"]["organization"]["status"], "current")
        self.assertIn(accepted["id"], [cid for p in wiki["pages"] for cid in p["claim_ids"]])

    def test_accept_during_call_resolves_without_regeneration(self):
        def generate(*args):
            result = self.generate(*args)
            accept_claim_proposal(self.claims[0]["id"], path=self.db)
            return result
        self.assertTrue(execute_wiki_stage(self.run, self.db, self.config, generate=generate))
        self.assertEqual(len(get_wiki(self.db, projected=True)["pages"]), 2)

    def test_rejection_hides_affected_summary_not_other_pages(self):
        execute_wiki_stage(self.run, self.db, self.config, generate=self.generate)
        discard_claim_proposal(self.claims[0]["id"], self.db)
        wiki = get_wiki(self.db, projected=True)
        self.assertEqual(wiki["projection"]["organization"]["stale_pages"], 1)
        self.assertEqual(sum(bool(p["summary"]) for p in wiki["pages"]), 1)

    def test_edit_during_call_rejects_output_and_next_run_retries(self):
        def generate(*args):
            result = self.generate(*args)
            accepted = accept_claim_proposal(self.claims[0]["id"], path=self.db)
            revise_claim(accepted["id"], {"statement": "New meaning"}, self.db)
            return result
        self.assertFalse(execute_wiki_stage(self.run, self.db, self.config, generate=generate))
        self.assertEqual(get_wiki(self.db, projected=True)["pages"], [])
        with _database(self.db) as connection:
            connection.execute("UPDATE plan_runs SET status = 'partial' WHERE id = ?", (self.run,))
        later, _ = queue_run(self.plan, self.db)
        self.assertTrue(execute_wiki_stage(later, self.db, self.config, generate=self.generate))
        self.assertEqual(list_runs(self.db, run_id=self.run)[0]["knowledge_jobs"][0]["status"], "failed")

    def test_reset_during_call_cannot_be_overwritten(self):
        def generate(*args):
            result = self.generate(*args); reset_wiki_structure(self.db); return result
        self.assertFalse(execute_wiki_stage(self.run, self.db, self.config, generate=generate))
        self.assertEqual(get_wiki(self.db)["pages"], [])

    def test_batch_limit_preserves_prior_pages(self):
        self.settings.return_value = {"ai_wiki_claim_limit": 1}
        self.assertTrue(execute_wiki_stage(self.run, self.db, self.config, generate=self.generate))
        self.assertEqual(len(get_wiki(self.db, projected=True)["unorganized_claim_ids"]), 1)
        self.assertTrue(execute_wiki_stage(self.run, self.db, self.config, generate=lambda *a: self.fail("One batch per Run")))
        with _database(self.db) as connection:
            connection.execute("UPDATE plan_runs SET status = 'completed' WHERE id = ?", (self.run,))
        later, _ = queue_run(self.plan, self.db)
        self.assertTrue(execute_wiki_stage(later, self.db, self.config, generate=self.generate))
        wiki = get_wiki(self.db, projected=True)
        self.assertEqual(len(wiki["pages"]), 2)
        self.assertEqual(wiki["unorganized_claim_ids"], [])

    def test_raw_json_failure_has_no_page_writes(self):
        self.assertFalse(execute_wiki_stage(self.run, self.db, self.config, generate=lambda *a: (
            {"_structured_output_degraded": True, "answer": "raw"}, {"chat_requests": 1})))
        self.assertEqual(get_wiki(self.db, projected=True)["pages"], [])
        self.assertEqual(list_runs(self.db, run_id=self.run)[0]["knowledge_jobs"][0]["report"]["raw_response"], "raw")

    def test_large_batch_selects_reference_pages_before_organizing(self):
        self.settings.return_value = {"ai_wiki_claim_limit": 1}
        execute_wiki_stage(self.run, self.db, self.config, generate=self.generate)
        wiki = get_wiki(self.db, projected=True)
        selected = [c for c in wiki["claims"] if c["id"] in wiki["unorganized_claim_ids"]]
        client = Mock()
        client.chat_json.side_effect = [{"page_ids": [wiki["pages"][0]["id"]]}, self.generate(wiki, selected)[0]]
        client.usage_snapshot.return_value = {"chat_requests": 2, "chat_tokens": 20}
        with patch("knowte.server._client_from_config", return_value=client), patch("knowte.usage.record_ai_usage") as usage:
            result, stats = _generate(wiki, selected, True, {}, self.config, "m")
        self.assertEqual(client.chat_json.call_count, 2)
        request = json.loads(client.chat_json.call_args_list[1].args[1])
        self.assertTrue(request["projection_mode"])
        self.assertEqual(len(request["reference_pages"]), 1)
        self.assertEqual(stats["chat_requests"], 2)
        usage.assert_called_once()

    def test_structure_review_blocks_pending_claims_then_creates_one_editable_draft(self):
        execute_wiki_stage(self.run, self.db, self.config, generate=self.generate)
        organization = get_wiki(self.db, projected=True)["projection"]["organization"]
        with self.assertRaisesRegex(ValueError, "pending Claim"):
            review_wiki_projection(organization["id"], self.db)
        for claim in self.claims:
            accept_claim_proposal(claim["id"], path=self.db)
        draft = review_wiki_projection(organization["id"], self.db)
        self.assertEqual(review_wiki_projection(organization["id"], self.db)["id"], draft["id"])
        self.assertEqual(get_wiki(self.db)["pages"], [])
        edited = draft["payload"]
        edited["pages"][0]["title"] = "Edited title"
        update_wiki_proposal(draft["id"], edited, self.db)
        reviewed = accept_wiki_proposal(draft["id"], self.db)
        self.assertEqual(reviewed["pages"][0]["title"], "Edited title")
        projected = get_wiki(self.db, projected=True)
        self.assertEqual(projected["projection"]["organization"]["status"], "reviewed")
        self.assertEqual(projected["pages"], reviewed["pages"])

    def test_discard_structure_draft_keeps_projection(self):
        execute_wiki_stage(self.run, self.db, self.config, generate=self.generate)
        for claim in self.claims:
            accept_claim_proposal(claim["id"], path=self.db)
        before = get_wiki(self.db, projected=True)
        draft = review_wiki_projection(before["projection"]["organization"]["id"], self.db)
        discard_wiki_proposal(draft["id"], self.db)
        self.assertEqual(get_wiki(self.db, projected=True), before)

    def test_edit_after_structure_review_started_blocks_apply(self):
        execute_wiki_stage(self.run, self.db, self.config, generate=self.generate)
        accepted = [accept_claim_proposal(c["id"], path=self.db) for c in self.claims]
        organization = get_wiki(self.db, projected=True)["projection"]["organization"]
        draft = review_wiki_projection(organization["id"], self.db)
        revise_claim(accepted[0]["id"], {"statement": "Changed meaning"}, self.db)
        with self.assertRaisesRegex(ValueError, "needs upstream review"):
            accept_wiki_proposal(draft["id"], self.db)
        self.assertEqual(get_wiki(self.db)["pages"], [])

    def test_end_to_end_run_reaches_projection_without_accepting_knowledge(self):
        # This fixture starts from acquisition, not pre-existing proposal outputs.
        for claim in self.claims:
            discard_claim_proposal(claim["id"], self.db)
        with _database(self.db) as connection:
            row = connection.execute("SELECT config_json FROM run_processing_policy WHERE run_id = ?", (self.run,)).fetchone()
            policy = json.loads(row[0]); policy["relations"] = {"enabled": True, "model_profile_id": "m"}
            connection.execute("UPDATE run_processing_policy SET config_json = ? WHERE run_id = ?", (json.dumps(policy), self.run))
        def evidence(payload, config, path, content, *, automation_scope):
            item = create_evidence_proposal({"source_id": payload["source_ids"][0], "quote": "Policies select actions and rewards measure outcomes.", "verification": "external_unverified"}, "test", scope=automation_scope, path=path)
            return {"proposals": [item]}, 201
        def claims(payload, config, path, *, evidence_inputs, automation_scope):
            return {"proposals": [create_claim_proposal({"statement": statement, "basis": "reported", "evidence": [
                {"evidence_id": evidence_inputs[0]["id"], "stance": "supports"}]}, "test", scope=automation_scope, path=path)
                for statement in ("Policies select actions", "Rewards evaluate policies")]}, 201
        def relations(pairs, *args):
            return {"assessments": [{"left_claim_id": a["resolved_id"], "right_claim_id": b["resolved_id"],
                "judgment": "related", "rationale": "Policy evaluation connects rewards and actions."} for a, b in pairs]}, {"chat_requests": 1}
        with patch("knowte.plan_knowledge.load_config", return_value={}), patch("knowte.plan_relations.load_config", return_value={}), \
             patch("knowte.plan_knowledge.ai_model_profiles", return_value=[{"id": "m", "capabilities": ["chat"]}]), \
             patch("knowte.plan_relations.ai_model_profiles", return_value=[{"id": "m", "capabilities": ["chat"]}]), \
             patch("knowte.server.generate_evidence_proposals", side_effect=evidence), \
             patch("knowte.server.generate_claim_proposals", side_effect=claims), \
             patch("knowte.plan_relations._generate", side_effect=relations), patch("knowte.plan_wiki._generate", side_effect=self.generate):
            execute_run(self.run, self.db, self.config, retrieve=lambda *a: [{"title": "RL", "url": "https://example.org/rl"}],
                        review=lambda config, candidates, *a: {"results": candidates})
        run = list_runs(self.db, run_id=self.run)[0]
        self.assertEqual(run["status"], "completed")
        self.assertEqual({j["stage"] for j in run["knowledge_jobs"]}, {"evidence", "claims", "relations", "wiki"})
        self.assertEqual(list_claims(self.db), [])
        self.assertEqual(list_evidence(self.db), [])
        self.assertEqual(len(get_wiki(self.db, projected=True)["pages"]), 2)
        self.assertEqual(len(get_wiki(self.db, projected=True)["graph"]["edges"]), 1)
        evidence = accept_evidence_proposal(list_evidence_proposals(self.db)[0]["id"], path=self.db)
        for claim in list_claim_proposals(self.db):
            if claim["payload"]["operation"] == "create_claim":
                accept_claim_proposal(claim["id"], path=self.db)
        edited = update_evidence(evidence["id"], {"revision": list_evidence(self.db)[0]["revision"],
            "quote": evidence["quote"] + " ", "locator": "Typo corrected", "ignore_logical_impact": True}, self.db)
        self.assertEqual(get_wiki(self.db, projected=True)["projection"]["organization"]["status"], "current")
        edited = update_evidence(evidence["id"], {"revision": edited["revision"], "quote": "Different meaning."}, self.db)
        self.assertEqual(get_wiki(self.db, projected=True)["projection"]["organization"]["status"], "stale")
        update_evidence(evidence["id"], {"revision": edited["revision"], "quote": "Different meaning!", "ignore_logical_impact": True}, self.db)
        self.assertEqual(get_wiki(self.db, projected=True)["projection"]["organization"]["status"], "stale")


if __name__ == "__main__":
    unittest.main()
