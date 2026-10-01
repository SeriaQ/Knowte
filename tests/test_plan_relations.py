import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from knowte.automation import _database, mutate
from knowte.knowledge import (save_source, create_evidence_proposal, create_claim_proposal,
    accept_evidence_proposal, accept_claim_proposal, get_wiki, list_claim_proposals, revise_claim)
from knowte.plan_runs import queue_run, list_runs
from knowte.plan_relations import execute_relation_stage


class PlanRelationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / "knowte.db"
        self.config = self.db.with_name("config.yaml")
        settings = patch("knowte.plan_relations.load_config", return_value={})
        profiles = patch("knowte.plan_relations.ai_model_profiles", return_value=[{"id": "model", "capabilities": ["chat"]}])
        settings.start(); profiles.start()
        self.addCleanup(settings.stop); self.addCleanup(profiles.stop)
        stage = {"enabled": True, "focus": "RL", "model_profile_id": "model"}
        action = mutate({"operation": "save_action", "name": "RL", "config": {"query": "RL", "sources": ["arxiv"]}}, self.db)["saved_id"]
        self.plan = mutate({"operation": "save_plan", "name": "RL", "action_ids": [action], "processing": {
            "save_sources": True, "max_new_sources": 20, "evidence": stage, "claims": stage,
            "relations": {"enabled": True, "model_profile_id": "model"}}}, self.db)["saved_id"]
        self.run, _ = queue_run(self.plan, self.db)
        source, _, _ = save_source({"title": "RL", "url": "https://example.org/rl"}, path=self.db)
        self.evidence = create_evidence_proposal({"source_id": source["id"], "quote": "Policies select actions.",
            "verification": "external_unverified"}, "test", path=self.db)
        with _database(self.db) as connection:
            connection.execute("INSERT INTO plan_claim_jobs (id, plan_id, first_run_id, input_refs_json, policy_json, status) VALUES ('seed', ?, ?, '[]', '{}', 'completed')", (self.plan, self.run))
        self.claims = [create_claim_proposal({"statement": statement, "basis": "reported", "evidence": [
            {"evidence_id": "proposal:" + self.evidence["id"], "stance": "supports"}]}, "test", scope={"generation_job_id": "seed"}, path=self.db)
            for statement in ("Policies select actions", "Policies determine reward")]

    def generate(self, pairs, *args):
        return {"assessments": [{"left_claim_id": a["resolved_id"], "right_claim_id": b["resolved_id"],
            "subject_claim_id": a["resolved_id"], "object_claim_id": b["resolved_id"],
            "judgment": "supports", "rationale": "A concrete dependency."} for a, b in pairs]}, {"chat_requests": 1}

    def test_pending_chain_and_second_run_do_not_repeat_model_call(self):
        calls = []
        def generate(*args):
            calls.append(True)
            return self.generate(*args)
        self.assertTrue(execute_relation_stage(self.run, self.db, self.config, generate=generate))
        self.assertEqual(len(calls), 1)
        self.assertEqual(get_wiki(self.db)["claims"], [])
        projected = get_wiki(self.db, projected=True)
        self.assertEqual(len(projected["graph"]["edges"]), 1)
        relation = next(p for p in list_claim_proposals(self.db) if p["payload"]["operation"] == "create_relation")
        self.assertEqual(relation["derivation"]["pending_count"], 2)
        self.assertTrue(execute_relation_stage(self.run, self.db, self.config, generate=generate))
        self.assertEqual(len(calls), 1)
        job = list_runs(self.db, run_id=self.run)[0]["knowledge_jobs"][0]
        self.assertEqual(job["stage"], "relations")
        self.assertEqual(job["report"]["model_usage"]["chat_requests"], 1)

    def test_acceptance_during_call_preserves_valid_result(self):
        def generate(*args):
            result = self.generate(*args)
            accept_evidence_proposal(self.evidence["id"], path=self.db)
            for claim in self.claims:
                accept_claim_proposal(claim["id"], path=self.db)
            return result
        self.assertTrue(execute_relation_stage(self.run, self.db, self.config, generate=generate))
        relation = list_claim_proposals(self.db)[0]
        self.assertEqual(relation["derivation"]["pending_count"], 0)
        self.assertFalse(relation["payload"]["subject_claim_id"].startswith("proposal:"))

    def test_edit_during_call_rejects_entire_batch_and_retries(self):
        accept_evidence_proposal(self.evidence["id"], path=self.db)
        accepted = [accept_claim_proposal(c["id"], path=self.db) for c in self.claims]
        def generate(*args):
            result = self.generate(*args)
            revise_claim(accepted[0]["id"], {"statement": "A changed proposition"}, self.db)
            return result
        self.assertFalse(execute_relation_stage(self.run, self.db, self.config, generate=generate))
        self.assertEqual(list_claim_proposals(self.db), [])
        self.assertTrue(execute_relation_stage(self.run, self.db, self.config, generate=self.generate))
        self.assertEqual(len(list_claim_proposals(self.db)), 1)

    def test_invalid_json_is_retained_and_not_immediately_called_twice(self):
        calls = []
        def generate(*args):
            calls.append(True)
            return {"_structured_output_degraded": True, "answer": "Original answer"}, {"chat_requests": 1}
        self.assertFalse(execute_relation_stage(self.run, self.db, self.config, generate=generate))
        self.assertEqual(calls, [True])
        job = list_runs(self.db, run_id=self.run)[0]["knowledge_jobs"][0]
        self.assertEqual(job["report"]["raw_response"], "Original answer")

    def test_existing_relation_avoids_extra_model_call(self):
        create_claim_proposal({"operation": "create_relation", "relation_type": "related",
            "subject_claim_id": "proposal:" + self.claims[0]["id"],
            "object_claim_id": "proposal:" + self.claims[1]["id"]}, "test", path=self.db)
        def forbidden(*args):
            self.fail("Existing links should not be sent for new-link discovery")
        self.assertTrue(execute_relation_stage(self.run, self.db, self.config, generate=forbidden))

    def test_relation_policy_requires_upstream_stage(self):
        with self.assertRaisesRegex(ValueError, "Claim generation"):
            mutate({"operation": "save_plan", "name": "Invalid", "processing": {
                "save_sources": True, "max_new_sources": 20,
                "relations": {"enabled": True, "model_profile_id": "model"}}}, self.db)

    def test_accepted_claim_edits_stale_the_pending_relation(self):
        accept_evidence_proposal(self.evidence["id"], path=self.db)
        accepted = [accept_claim_proposal(c["id"], path=self.db) for c in self.claims]
        self.assertTrue(execute_relation_stage(self.run, self.db, self.config, generate=self.generate))
        revise_claim(accepted[1]["id"], {"statement": "Changed meaning"}, self.db)
        relation = list_claim_proposals(self.db)[0]
        self.assertEqual(relation["derivation"]["status"], "stale")
        self.assertEqual(get_wiki(self.db, projected=True)["graph"]["edges"], [])

    def test_invalid_batch_has_no_partial_writes(self):
        def generate(*args):
            result, usage = self.generate(*args)
            result["assessments"][0]["object_claim_id"] = "invented"
            return result, usage
        self.assertFalse(execute_relation_stage(self.run, self.db, self.config, generate=generate))
        self.assertFalse(any(p["payload"]["operation"] == "create_relation" for p in list_claim_proposals(self.db)))

    def test_distinct_pair_completes_without_repeated_calls(self):
        def generate(*args):
            result, usage = self.generate(*args)
            result["assessments"][0]["judgment"] = "distinct"
            return result, usage
        self.assertTrue(execute_relation_stage(self.run, self.db, self.config, generate=generate))
        self.assertTrue(execute_relation_stage(self.run, self.db, self.config, generate=lambda *a: self.fail("No paid loop")))
        job = list_runs(self.db, run_id=self.run)[0]["knowledge_jobs"][0]
        self.assertEqual(len(job["report"]["skipped"]), 1)

    def test_next_run_retry_keeps_failed_attempt_history(self):
        def fail(*args):
            raise RuntimeError("fixture timeout")
        self.assertFalse(execute_relation_stage(self.run, self.db, self.config, generate=fail))
        with _database(self.db) as connection:
            connection.execute("UPDATE plan_runs SET status = 'partial' WHERE id = ?", (self.run,))
        later, _ = queue_run(self.plan, self.db)
        self.assertTrue(execute_relation_stage(later, self.db, self.config, generate=self.generate))
        old = list_runs(self.db, run_id=self.run)[0]["knowledge_jobs"][0]
        new = list_runs(self.db, run_id=later)[0]["knowledge_jobs"][0]
        self.assertEqual(old["status"], "failed")
        self.assertEqual(new["status"], "completed")
        self.assertEqual(old["id"], new["id"])


if __name__ == "__main__":
    unittest.main()
