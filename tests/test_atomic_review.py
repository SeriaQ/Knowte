import base64
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch

from knowte import knowledge
from tests import test_proposal_dependencies as fixtures


class AtomicClaimReviewTests(unittest.TestCase):
    def setUp(self):
        fixtures.ProposalDependencyTests.setUp(self)

    def snapshot(self):
        with sqlite3.connect(self.db) as connection:
            return {
                table: connection.execute(f'SELECT * FROM {table} ORDER BY rowid').fetchall()
                for table in (
                    'claims', 'claim_revisions', 'evidence_claim_links',
                    'claim_relations', 'review_proposals', 'proposal_outcomes',
                    'artifact_dependencies', 'proposal_derivations', 'tags', 'entity_tags',
                )
            }

    def test_review_rolls_back_object_and_dependencies_then_retries_once(self):
        parent = fixtures.ProposalDependencyTests.evidence(self)
        evidence = knowledge.accept_evidence_proposal(parent['id'], path=self.db)
        left = knowledge.create_claim({'statement': 'Left', 'basis': 'background',
            'intentionally_ungrounded': True}, self.db)
        right = knowledge.create_claim({'statement': 'Right', 'basis': 'background',
            'intentionally_ungrounded': True}, self.db)
        operations = [
            {'statement': 'New conclusion', 'basis': 'inference', 'tags': ['atomic'],
             'evidence': [{'evidence_id': evidence['id'], 'stance': 'supports'}]},
            {'operation': 'create_relation', 'subject_claim_id': left['id'],
             'object_claim_id': right['id'], 'relation_type': 'supports'},
            {'operation': 'link_evidence', 'target_claim_id': left['id'],
             'evidence': [{'evidence_id': evidence['id'], 'stance': 'supports'}]},
            {'operation': 'merge_claims', 'target_claim_id': left['id'],
             'source_claim_id': right['id'], 'merged_statement': 'Merged conclusion'},
        ]
        original = knowledge.proposal_dependencies.resolve

        def fail_after_resolution(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError('interrupted after dependency resolution')

        for payload in operations:
            with self.subTest(operation=payload.get('operation', 'create_claim')):
                proposal = knowledge.create_claim_proposal(payload, 'test', path=self.db)
                if 'operation' not in payload:
                    knowledge.create_claim_proposal({
                        'operation': 'create_relation',
                        'subject_claim_id': 'proposal:' + proposal['id'],
                        'object_claim_id': left['id'], 'relation_type': 'related',
                    }, 'test', path=self.db)
                before = self.snapshot()
                with patch.object(knowledge.proposal_dependencies, 'resolve', side_effect=fail_after_resolution):
                    with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                        knowledge.accept_claim_proposal(proposal['id'], path=self.db)
                self.assertEqual(self.snapshot(), before)
                knowledge.accept_claim_proposal(proposal['id'], path=self.db)
                after = self.snapshot()
                with self.assertRaises(ValueError):
                    knowledge.accept_claim_proposal(proposal['id'], path=self.db)
                self.assertEqual(self.snapshot(), after)


class AtomicEvidenceReviewTests(unittest.TestCase):
    def setUp(self):
        fixtures.ProposalDependencyTests.setUp(self)

    def snapshot(self):
        with sqlite3.connect(self.db) as connection:
            return {
                table: connection.execute(f'SELECT * FROM {table} ORDER BY rowid').fetchall()
                for table in ('sources', 'source_captures', 'capture_segments', 'evidence',
                    'annotations', 'tags', 'entity_tags', 'review_proposals',
                    'proposal_outcomes', 'artifact_dependencies', 'proposal_derivations')
            }

    def test_acceptance_rolls_back_captures_sources_images_and_dependency_promotion(self):
        knowledge.create_evidence({'segment_id': self.segment_id,
            'evidence_type': 'snapshot', 'image_data': 'data:image/png;base64,' +
            base64.b64encode(b'\x89PNG\r\n\x1a\nexisting').decode()}, self.db)
        original = knowledge.proposal_dependencies.resolve

        def fail_after_resolution(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError('interrupted after dependency resolution')

        for mode in ('local', 'external', 'snapshot'):
            with self.subTest(mode=mode):
                payload = {'source_id': self.source_id, 'segment_id': self.segment_id,
                    'quote': 'Policy gradients estimate expected return.', 'tags': ['RL']}
                if mode != 'local':
                    payload.update(verification='external_unverified', related_source={
                        'parent_source_id': self.source_id, 'title': mode,
                        'url': 'https://example.org/rl/' + mode})
                if mode == 'snapshot':
                    payload.update(evidence_type='snapshot', image_data='data:image/png;base64,' +
                        base64.b64encode(b'\x89PNG\r\n\x1a\nexample').decode())
                proposal = knowledge.create_evidence_proposal(payload, 'test', path=self.db)
                fixtures.ProposalDependencyTests.claim(self, [proposal], 'Conclusion ' + mode)
                before = self.snapshot()
                files_before = set(self.db.parent.rglob('*.png'))
                with patch.object(knowledge.proposal_dependencies, 'resolve', side_effect=fail_after_resolution):
                    with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                        knowledge.accept_evidence_proposal(proposal['id'], path=self.db)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(set(self.db.parent.rglob('*.png')), files_before)
                knowledge.accept_evidence_proposal(proposal['id'], path=self.db)
                after = self.snapshot()
                with self.assertRaises(ValueError):
                    knowledge.accept_evidence_proposal(proposal['id'], path=self.db)
                self.assertEqual(self.snapshot(), after)
                self.assertTrue(files_before.issubset(set(self.db.parent.rglob('*.png'))))

    def test_partial_image_write_is_removed(self):
        before = self.snapshot()
        original = Path.write_bytes

        def fail_after_write(image, data):
            original(image, data[:8])
            raise OSError('interrupted image write')

        with patch.object(Path, 'write_bytes', fail_after_write):
            with self.assertRaisesRegex(OSError, 'interrupted image'):
                knowledge.create_evidence({'segment_id': self.segment_id,
                    'evidence_type': 'snapshot', 'image_data': 'data:image/png;base64,' +
                    base64.b64encode(b'\x89PNG\r\n\x1a\nexample').decode()}, self.db)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(list(self.db.parent.rglob('*.png')), [])

    def test_import_validation_failure_leaves_no_partial_capture(self):
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, '20 Tags'):
            knowledge.import_evidence(self.source_id, {'quote': 'Text',
                'tags': [str(i) for i in range(21)]}, path=self.db)
        self.assertEqual(self.snapshot(), before)

    def test_import_annotations_and_tags_share_transaction(self):
        before = self.snapshot()
        original = knowledge.create_annotation

        def fail_after_annotation(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError('interrupted annotation')

        with patch.object(knowledge, 'create_annotation', side_effect=fail_after_annotation):
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                knowledge.import_evidence(self.source_id, {'quote': 'Text', 'tags': ['RL'],
                    'annotations': [{'body': 'Note'}]}, path=self.db)
        self.assertEqual(self.snapshot(), before)
