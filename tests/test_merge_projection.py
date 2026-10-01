import unittest
import json

from tests import test_wiki_projection as fixtures
from knowte.knowledge import (accept_evidence_proposal, accept_claim_proposal,
    create_claim, create_claim_proposal, discard_claim_proposal, get_wiki,
    revise_claim, list_claim_proposals, _connect, create_claim_relation)
from knowte.proposal_dependencies import claim_input


class MergeProjectionTests(unittest.TestCase):
    claim = fixtures.WikiProjectionTests.claim

    def setUp(self):
        fixtures.WikiProjectionTests.setUp(self)
        accept_evidence_proposal(self.evidence['id'], path=self.db)
        self.a = accept_claim_proposal(self.left['id'], path=self.db)
        self.b = accept_claim_proposal(self.right['id'], path=self.db)
        self.other = create_claim({'statement': 'Third', 'basis': 'background'}, self.db)
        self.merge = self.propose(self.a['id'], self.b['id'])

    def propose(self, target, source):
        return create_claim_proposal({'operation': 'merge_claims', 'target_claim_id': target,
            'source_claim_id': source, 'merged_statement': 'Merged meaning'}, 'test', path=self.db)

    def test_unchanged_acceptance_preserves_fingerprint_and_promotes_child(self):
        ref = 'proposal:' + self.merge['id']
        with _connect(self.db) as connection:
            before = claim_input(connection, ref)
        child = create_claim_proposal({'operation': 'create_relation', 'subject_claim_id': ref,
            'object_claim_id': self.other['id'], 'relation_type': 'related'}, 'test', path=self.db)
        accept_claim_proposal(self.merge['id'], path=self.db)
        with _connect(self.db) as connection:
            after = claim_input(connection, ref)
        self.assertEqual(before['input_version'], after['input_version'])
        self.assertEqual(after['resolved_id'], self.a['id'])
        pending = next(p for p in list_claim_proposals(self.db) if p['id'] == child['id'])
        self.assertEqual(pending['derivation']['pending_count'], 0)
        self.assertEqual(pending['payload']['subject_claim_id'], self.a['id'])

    def test_changed_endpoint_excludes_projection_and_blocks_acceptance(self):
        revise_claim(self.a['id'], {'statement': 'Different meaning'}, self.db)
        self.assertIn(self.merge['id'], get_wiki(self.db, projected=True)['projection']['excluded_proposal_ids'])
        with self.assertRaisesRegex(ValueError, 'Merge input changed'):
            accept_claim_proposal(self.merge['id'], path=self.db)

    def test_overlapping_merges_deferred_until_user_resolves_conflict(self):
        other = self.propose(self.a['id'], self.other['id'])
        projected = get_wiki(self.db, projected=True)
        self.assertEqual(set(projected['projection']['deferred_proposal_ids']), {self.merge['id'], other['id']})
        self.assertEqual(len(projected['claims']), 3)
        discard_claim_proposal(other['id'], self.db)
        self.assertEqual(len(get_wiki(self.db, projected=True)['claims']), 2)

    def test_discard_restores_originals_and_invalidates_children(self):
        child = create_claim_proposal({'operation': 'create_relation', 'subject_claim_id': 'proposal:' + self.merge['id'],
            'object_claim_id': self.other['id'], 'relation_type': 'related'}, 'test', path=self.db)
        discard_claim_proposal(self.merge['id'], self.db)
        self.assertEqual(len(get_wiki(self.db, projected=True)['claims']), 3)
        pending = next(p for p in list_claim_proposals(self.db) if p['id'] == child['id'])
        self.assertEqual(pending['derivation']['status'], 'invalidated')

    def test_editing_merged_statement_on_accept_stales_children(self):
        child = create_claim_proposal({'operation': 'create_relation', 'subject_claim_id': 'proposal:' + self.merge['id'],
            'object_claim_id': self.other['id'], 'relation_type': 'related'}, 'test', path=self.db)
        accept_claim_proposal(self.merge['id'], {'merged_statement': 'Edited meaning'}, self.db)
        pending = next(p for p in list_claim_proposals(self.db) if p['id'] == child['id'])
        self.assertEqual(pending['derivation']['status'], 'stale')

    def test_remapped_edges_drop_self_links_and_deduplicate(self):
        for source in (self.a, self.b):
            create_claim_relation({'subject_claim_id': source['id'], 'object_claim_id': self.other['id'], 'relation_type': 'supports'}, self.db)
        create_claim_relation({'subject_claim_id': self.a['id'], 'object_claim_id': self.b['id'], 'relation_type': 'related'}, self.db)
        edges = get_wiki(self.db, projected=True)['graph']['edges']
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['subject_claim_id'], 'proposal:' + self.merge['id'])
        self.assertTrue(edges[0]['projection']['identity_merge'])

    def test_organized_merge_survives_unchanged_acceptance(self):
        ref = 'proposal:' + self.merge['id']
        create_claim_proposal({'operation': 'create_relation', 'subject_claim_id': ref,
            'object_claim_id': self.other['id'], 'relation_type': 'related'}, 'test', path=self.db)
        reviewed = get_wiki(self.db)
        with _connect(self.db) as connection:
            fingerprint = claim_input(connection, ref)['input_version']
            connection.execute('INSERT INTO wiki_projections VALUES (?, ?, ?, ?, ?, ?, ?)', (
                'projection', 'plan', 'run', (reviewed.get('revision') or {}).get('id'),
                json.dumps({'pages': [{'key': 'page', 'title': 'Merged', 'parent_key': '', 'summary': 'Overview', 'claim_ids': [ref]}]}),
                json.dumps({ref: fingerprint}), '2026-09-27'))
        accept_claim_proposal(self.merge['id'], path=self.db)
        wiki = get_wiki(self.db, projected=True)
        self.assertEqual(wiki['projection']['organization']['status'], 'current')
        self.assertEqual(wiki['pages'][0]['claim_ids'], [self.a['id']])

    def test_cross_page_merge_keeps_one_membership_and_remaps_summary_links(self):
        from knowte.knowledge import create_wiki_proposal, accept_wiki_proposal
        a, b, other = self.a['id'], self.b['id'], self.other['id']
        patch = create_wiki_proposal({'pages': [
            {'key': 'a', 'title': 'A', 'claim_ids': [a], 'summary': 'First'},
            {'key': 'b', 'title': 'B', 'claim_ids': [b], 'summary': 'Second'},
            {'key': 'c', 'title': 'C', 'claim_ids': [other],
             'summary': f'Compare [[claim:{b}|original]] with [[claim:{other}|third]].'},
        ]}, 'test', path=self.db)
        accept_wiki_proposal(patch['id'], self.db)
        ref = 'proposal:' + self.merge['id']
        projected = get_wiki(self.db, projected=True)
        self.assertEqual(sum(p['claim_ids'].count(ref) for p in projected['pages']), 1)
        self.assertIn(f'[[claim:{ref}|', projected['pages'][1]['summary'])
        self.assertEqual(projected['pages'][2]['summary'], '')
        accept_claim_proposal(self.merge['id'], path=self.db)
        reviewed = get_wiki(self.db)
        self.assertEqual(sum(p['claim_ids'].count(a) for p in reviewed['pages']), 1)
        self.assertIn(f'[[claim:{a}|', reviewed['pages'][1]['summary'])
        self.assertIn(f'[[claim:{a}|original]]', reviewed['pages'][2]['summary'])
        self.assertIn(f'[[claim:{other}|third]]', reviewed['pages'][2]['summary'])
        self.assertNotIn(b, str(reviewed['pages']))
        self.assertIn(a, reviewed['stale_claim_ids'])

    def test_ignore_cannot_override_merge_conflict(self):
        from knowte.knowledge import ignore_proposal_impact, ignore_proposal_descendants
        revise_claim(self.a['id'], {'statement': 'Changed'}, self.db)
        for ignore in (ignore_proposal_impact, ignore_proposal_descendants):
            with self.assertRaisesRegex(ValueError, 'only available'):
                ignore(self.merge['id'], self.db)
        self.assertIn(self.merge['id'], get_wiki(self.db, projected=True)['projection']['excluded_proposal_ids'])
