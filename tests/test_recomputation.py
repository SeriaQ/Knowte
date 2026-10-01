import json
import unittest
from unittest.mock import patch

from tests import test_plan_relations as fixtures
from knowte.automation import _database
from knowte.knowledge import (accept_evidence_proposal, update_evidence, list_evidence,
    create_claim_proposal, list_claim_proposals, discard_claim_proposal, ignore_proposal_impact,
    ignore_proposal_descendants, create_claim)
from knowte.plan_knowledge import execute_claim_stage
from knowte.plan_runs import queue_run


class RecomputationTests(unittest.TestCase):
    def setUp(self):
        fixtures.PlanRelationTests.setUp(self)
        with _database(self.db) as connection:
            connection.execute("UPDATE plan_claim_jobs SET policy_json = ?", (json.dumps({"enabled": True, "focus": "RL", "model_profile_id": "model"}),))
        settings = patch("knowte.plan_knowledge.load_config", return_value={})
        profiles = patch("knowte.plan_knowledge.ai_model_profiles", return_value=[{"id": "model", "capabilities": ["chat"]}])
        settings.start(); profiles.start(); self.addCleanup(settings.stop); self.addCleanup(profiles.stop)
        self.calls = 0

    def generate(self, payload, config, path, *, evidence_inputs, automation_scope):
        self.calls += 1
        result = create_claim_proposal({"statement": "Recomputed conclusion", "basis": "reported", "evidence": [
            {"evidence_id": i["id"], "stance": "supports"} for i in evidence_inputs]}, "test", scope=automation_scope, path=path,
            _input_versions={i["id"]: i["input_version"] for i in evidence_inputs})
        return {"proposals": [result]}, 201

    def make_stale(self):
        return accept_evidence_proposal(self.evidence["id"], {"quote": "Policies determine how actions are selected."}, self.db)

    def test_stale_siblings_merge_and_old_drafts_stay_pending(self):
        self.make_stale()
        self.assertTrue(execute_claim_stage(self.run, self.db, self.config, generate=self.generate))
        self.assertEqual(self.calls, 1)
        drafts = list_claim_proposals(self.db)
        self.assertEqual(len(drafts), 3)  # Two old Claims and one recomputed Claim.
        for old in self.claims:
            draft = next(p for p in drafts if p["id"] == old["id"])
            self.assertEqual(draft["status"], "awaiting_review")
            self.assertEqual(len(draft["derivation"]["recomputation"]["replacement_ids"]), 1)
        execute_claim_stage(self.run, self.db, self.config, generate=self.generate)
        self.assertEqual(self.calls, 1)

    def test_subsequent_edit_recomputes_new_draft_not_all_ancestors(self):
        evidence = self.make_stale()
        execute_claim_stage(self.run, self.db, self.config, generate=self.generate)
        update_evidence(evidence["id"], {"revision": list_evidence(self.db)[0]["revision"], "quote": "New logical revision"}, self.db)
        execute_claim_stage(self.run, self.db, self.config, generate=self.generate)
        self.assertEqual(self.calls, 2)

    def test_rejected_inputs_cost_no_calls(self):
        discard_claim_proposal(self.evidence["id"], self.db)
        execute_claim_stage(self.run, self.db, self.config, generate=self.generate)
        self.assertEqual(self.calls, 0)
        with self.assertRaises(ValueError):
            ignore_proposal_impact(self.claims[0]["id"], self.db)

    def test_ignore_is_explicit_local_and_preserves_review_state(self):
        self.make_stale()
        ignore_proposal_impact(self.claims[0]["id"], self.db)
        drafts = {p["id"]: p for p in list_claim_proposals(self.db)}
        self.assertEqual(drafts[self.claims[0]["id"]]["derivation"]["status"], "current")
        self.assertEqual(drafts[self.claims[0]["id"]]["status"], "awaiting_review")
        self.assertEqual(len(drafts[self.claims[0]["id"]]["scope"]["impact_ignores"]), 1)
        self.assertEqual(drafts[self.claims[1]["id"]]["derivation"]["status"], "stale")

    def test_immediate_run_has_no_actions_or_source_capture(self):
        with _database(self.db) as connection:
            connection.execute("UPDATE plan_runs SET status = 'completed' WHERE id = ?", (self.run,))
        run_id, created = queue_run(self.plan, self.db, knowledge_only=True, trigger="recompute")
        self.assertTrue(created)
        with _database(self.db) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM action_runs WHERE run_id = ?", (run_id,)).fetchone()[0], 0)
            policy = json.loads(connection.execute("SELECT config_json FROM run_processing_policy WHERE run_id = ?", (run_id,)).fetchone()[0])
        self.assertFalse(policy["save_sources"])
        self.assertFalse(policy["evidence"]["enabled"])
        self.assertTrue(policy["knowledge_only"])
        self.assertEqual(queue_run(self.plan, self.db, knowledge_only=True)[0], run_id)

    def test_chain_ignore_rebases_descendants_but_not_siblings(self):
        other = create_claim({'statement': 'Independent', 'basis': 'background'}, self.db)
        relation = create_claim_proposal({'operation': 'create_relation', 'relation_type': 'related',
            'subject_claim_id': 'proposal:' + self.claims[0]['id'], 'object_claim_id': other['id']}, 'test', path=self.db)
        self.make_stale()
        result = ignore_proposal_descendants(self.claims[0]['id'], self.db)
        self.assertEqual(set(result['affected_proposal_ids']), {self.claims[0]['id'], relation['id']})
        drafts = {p['id']: p for p in list_claim_proposals(self.db)}
        for key in result['affected_proposal_ids']:
            self.assertEqual(drafts[key]['derivation']['status'], 'current')
            self.assertEqual(drafts[key]['status'], 'awaiting_review')
            self.assertEqual(drafts[key]['scope']['impact_ignores'][-1]['chain_root'], self.claims[0]['id'])
        self.assertEqual(drafts[self.claims[1]['id']]['derivation']['status'], 'stale')

    def test_chain_ignore_rolls_back_if_other_parent_remains_stale(self):
        create_claim_proposal({'operation': 'create_relation', 'relation_type': 'related',
            'subject_claim_id': 'proposal:' + self.claims[0]['id'],
            'object_claim_id': 'proposal:' + self.claims[1]['id']}, 'test', path=self.db)
        self.make_stale()
        before = list_claim_proposals(self.db)
        with self.assertRaises(ValueError):
            ignore_proposal_descendants(self.claims[0]['id'], self.db)
        self.assertEqual(list_claim_proposals(self.db), before)

    def test_chain_ignore_cannot_restore_deleted_input(self):
        discard_claim_proposal(self.evidence['id'], self.db)
        before = list_claim_proposals(self.db)
        with self.assertRaises(ValueError):
            ignore_proposal_descendants(self.claims[0]['id'], self.db)
        self.assertEqual(list_claim_proposals(self.db), before)

    def test_ignore_does_not_waive_wiki_organization_versions(self):
        from knowte.knowledge import _connect, get_wiki
        from knowte.proposal_dependencies import claim_input
        ref = 'proposal:' + self.claims[0]['id']
        with _connect(self.db) as connection:
            fingerprint = claim_input(connection, ref)['input_version']
            connection.execute('INSERT INTO wiki_projections VALUES (?, ?, ?, ?, ?, ?, ?)', (
                'ignore-projection', self.plan, self.run, None,
                json.dumps({'pages': [{'key': 'rl', 'title': 'RL', 'parent_key': '',
                    'summary': 'Old interpretation', 'claim_ids': [ref]}]}),
                json.dumps({ref: fingerprint}), '2026-09-27'))
        self.make_stale()
        ignore_proposal_impact(self.claims[0]['id'], self.db)
        wiki = get_wiki(self.db, projected=True)
        self.assertEqual(wiki['projection']['organization']['stale_pages'], 1)
        self.assertEqual(wiki['pages'][0]['summary'], '')
