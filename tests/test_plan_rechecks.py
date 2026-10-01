import json
import unittest
from unittest.mock import patch

from tests import test_recomputation as fixtures
from knowte.automation import _database
from knowte.knowledge import (accept_evidence_proposal, accept_claim_proposal,
    update_evidence, get_claim, list_claim_proposals, get_wiki, create_claim,
    create_claim_proposal, ignore_evidence_change_review)
from knowte.plan_rechecks import execute_rechecks
from knowte.proposal_dependencies import claim_input
from knowte.plan_wiki import execute_wiki_stage
from knowte.plan_relations import execute_relation_stage


class PlanRecheckTests(unittest.TestCase):
    def setUp(self):
        fixtures.RecomputationTests.setUp(self)
        self.accepted_evidence = accept_evidence_proposal(self.evidence['id'], path=self.db)
        self.claim = accept_claim_proposal(self.claims[0]['id'], path=self.db)
        update_evidence(self.accepted_evidence['id'], {'revision': 1, 'quote': 'Revised policy evidence'}, self.db)
        self.calls = 0

    def generate(self, draft, inputs, policy, *args):
        self.calls += 1
        self.assertEqual(policy['model_profile_id'], 'model')
        return {'claims': [{'statement': 'Revised conclusion', 'rationale': 'New Evidence scope'}]}, {'chat_requests': 1}

    def review(self):
        return next(p for p in list_claim_proposals(self.db) if p['payload'].get('operation') == 'review_evidence_change')

    def test_revision_stays_pending_until_review_and_repeat_is_free(self):
        self.assertTrue(execute_rechecks(self.run, self.db, self.config, {}, generate=self.generate))
        review = self.review()
        self.assertEqual(review['payload']['statement'], 'Revised conclusion')
        self.assertEqual(get_claim(self.claim['id'], self.db)['statement'], self.claim['statement'])
        execute_rechecks(self.run, self.db, self.config, {}, generate=self.generate)
        self.assertEqual(self.calls, 1)
        accept_claim_proposal(review['id'], {'change_token': review['payload']['change_token']}, self.db)
        self.assertEqual(get_claim(self.claim['id'], self.db)['statement'], 'Revised conclusion')

    def test_edit_during_call_does_not_overwrite_latest_review(self):
        def race(*args):
            update_evidence(self.accepted_evidence['id'], {'revision': 2, 'quote': 'Changed again'}, self.db)
            return self.generate(*args)
        self.assertFalse(execute_rechecks(self.run, self.db, self.config, {}, generate=race))
        self.assertNotIn('ai_recheck', self.review()['payload'])
        self.assertTrue(execute_rechecks(self.run, self.db, self.config, {}, generate=self.generate))
        self.assertEqual(self.calls, 2)

    def test_invalid_response_retained_without_immediate_retry(self):
        def invalid(*args):
            self.calls += 1
            return {'raw_text': 'not JSON'}, {'chat_requests': 1}
        self.assertFalse(execute_rechecks(self.run, self.db, self.config, {}, generate=invalid))
        self.assertEqual(self.calls, 1)
        with _database(self.db) as connection:
            report = json.loads(connection.execute("SELECT report_json FROM plan_claim_jobs WHERE status = 'failed'").fetchone()[0])
        self.assertEqual(report['raw_response'], {'raw_text': 'not JSON'})
        self.assertNotIn('ai_recheck', self.review()['payload'])

    def test_no_supported_revision_keeps_manual_review(self):
        self.assertTrue(execute_rechecks(self.run, self.db, self.config, {},
            generate=lambda *args: ({'claims': [], 'summary': 'Insufficient support'}, {})))
        self.assertNotIn('ai_recheck', self.review()['payload'])
        execute_rechecks(self.run, self.db, self.config, {}, generate=self.generate)
        self.assertEqual(self.calls, 0)

    def test_later_evidence_edit_clears_old_suggestion_and_requeues(self):
        execute_rechecks(self.run, self.db, self.config, {}, generate=self.generate)
        update_evidence(self.accepted_evidence['id'], {'revision': 2, 'quote': 'New scope'}, self.db)
        self.assertNotIn('ai_recheck', self.review()['payload'])
        execute_rechecks(self.run, self.db, self.config, {}, generate=self.generate)
        self.assertEqual(self.calls, 2)

    def projected_revision(self):
        execute_rechecks(self.run, self.db, self.config, {}, generate=self.generate)
        review = self.review()
        ref = 'proposal:' + review['id']
        other = create_claim({'statement': 'Independent conclusion', 'basis': 'background'}, self.db)
        with _database(self.db) as connection:
            versions = {key: claim_input(connection, key)['input_version'] for key in (ref, other['id'])}
        relation = create_claim_proposal({'operation': 'create_relation', 'relation_type': 'related',
            'subject_claim_id': ref, 'object_claim_id': other['id']}, 'test', path=self.db,
            _claim_versions=versions)
        return review, ref, relation, versions[ref]

    def test_projected_revision_promotes_without_duplicate_or_version_change(self):
        review, ref, relation, version = self.projected_revision()
        projected = get_wiki(self.db, projected=True)
        ids = {c['id'] for c in projected['claims']}
        self.assertIn(ref, ids)
        self.assertNotIn(self.claim['id'], ids)
        self.assertEqual(get_claim(self.claim['id'], self.db)['statement'], self.claim['statement'])
        accept_claim_proposal(review['id'], {'change_token': review['payload']['change_token']}, self.db)
        with _database(self.db) as connection:
            resolved = claim_input(connection, ref)
        self.assertEqual(resolved['resolved_id'], self.claim['id'])
        self.assertEqual(resolved['input_version'], version)
        pending = next(p for p in list_claim_proposals(self.db) if p['id'] == relation['id'])
        self.assertEqual(pending['derivation']['pending_count'], 0)
        self.assertEqual(pending['payload']['subject_claim_id'], self.claim['id'])

    def test_edit_and_ignore_remove_revision_from_projection(self):
        review, ref, relation, _ = self.projected_revision()
        update_evidence(self.accepted_evidence['id'], {'revision': 2, 'quote': 'Another meaning'}, self.db)
        self.assertNotIn(ref, {c['id'] for c in get_wiki(self.db, projected=True)['claims']})
        pending = next(p for p in list_claim_proposals(self.db) if p['id'] == relation['id'])
        self.assertEqual(pending['derivation']['status'], 'stale')
        current = self.review()
        ignore_evidence_change_review(current['id'], current['payload']['change_token'], self.db)
        self.assertIn(self.claim['id'], {c['id'] for c in get_wiki(self.db, projected=True)['claims']})

    def test_withdraw_invalidates_revision_dependencies(self):
        review, ref, relation, _ = self.projected_revision()
        accept_claim_proposal(review['id'], {'change_token': review['payload']['change_token'], 'review_state': 'withdrawn'}, self.db)
        self.assertNotIn(ref, {c['id'] for c in get_wiki(self.db, projected=True)['claims']})
        pending = next(p for p in list_claim_proposals(self.db) if p['id'] == relation['id'])
        self.assertEqual(pending['derivation']['status'], 'invalidated')

    def test_revision_is_seed_for_automatic_relation_discovery(self):
        execute_rechecks(self.run, self.db, self.config, {}, generate=self.generate)
        ref = 'proposal:' + self.review()['id']
        create_claim({'statement': 'Other grounded conclusion', 'basis': 'reported',
            'evidence': [{'evidence_id': self.accepted_evidence['id'], 'stance': 'supports'}]}, self.db)
        seen = []
        def generate(pairs, *args):
            seen.extend(pairs)
            return {'assessments': [{'left_claim_id': a['resolved_id'], 'right_claim_id': b['resolved_id'],
                'subject_claim_id': a['resolved_id'], 'object_claim_id': b['resolved_id'],
                'judgment': 'related', 'rationale': 'Shared grounding'} for a, b in pairs]}, {}
        self.assertTrue(execute_relation_stage(self.run, self.db, self.config, generate=generate))
        self.assertTrue(any(ref in (a['id'], b['id']) for a, b in seen))

    def test_wiki_organizes_revision_and_unchanged_acceptance_preserves_projection(self):
        review, ref, _, _ = self.projected_revision()
        with _database(self.db) as connection:
            row = connection.execute('SELECT config_json FROM run_processing_policy WHERE run_id = ?', (self.run,)).fetchone()
            policy = json.loads(row[0]); policy['wiki'] = {'enabled': True, 'model_profile_id': 'model'}
            connection.execute('UPDATE run_processing_policy SET config_json = ? WHERE run_id = ?', (json.dumps(policy), self.run))
        def organize(wiki, selected, *args):
            return {'pages': [{'key': 'page', 'title': 'RL', 'parent_key': '', 'summary': 'Revised knowledge',
                'claim_ids': [c['id'] for c in selected]}]}, {}
        with patch('knowte.plan_wiki.load_config', return_value={}), patch('knowte.plan_wiki.ai_model_profiles', return_value=[{'id': 'model', 'capabilities': ['chat']}]):
            self.assertTrue(execute_wiki_stage(self.run, self.db, self.config, generate=organize))
        self.assertIn(ref, get_wiki(self.db, projected=True)['pages'][0]['claim_ids'])
        accept_claim_proposal(review['id'], {'change_token': review['payload']['change_token']}, self.db)
        wiki = get_wiki(self.db, projected=True)
        self.assertEqual(wiki['projection']['organization']['status'], 'current')
        self.assertIn(self.claim['id'], wiki['pages'][0]['claim_ids'])
