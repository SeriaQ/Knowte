import tempfile
import unittest
import json
import subprocess
import sys
from pathlib import Path

from tests.automation_sandbox import Sandbox
from knowte.knowledge import (list_sources, list_evidence_proposals, list_evidence,
    list_claim_proposals, list_claims, accept_evidence_proposal, accept_claim_proposal,
    update_evidence, get_wiki, review_wiki_projection, accept_wiki_proposal)
from knowte.plan_runs import list_runs


class AutomationJourneyTests(unittest.TestCase):
    def test_two_incremental_runs_review_edit_recompute_and_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = Sandbox(Path(directory))
            with sandbox.mocks():
                first = sandbox.run()
                second = sandbox.run()
                self.assertEqual(list_runs(sandbox.db, run_id=first)[0]['status'], 'completed')
                report = list_runs(sandbox.db, run_id=second)[0]
                self.assertEqual(report['counts']['new_count'], 1)
                self.assertEqual(report['counts']['duplicate_count'], 1)
                self.assertEqual(len(list_sources(sandbox.db)), 3)
                self.assertEqual(len(list_evidence_proposals(sandbox.db)), 3)
                self.assertEqual(list_claims(sandbox.db), [])
                calls = list(sandbox.calls)
                sandbox.run()
                self.assertEqual(sandbox.calls, calls)
                for draft in list_evidence_proposals(sandbox.db):
                    accept_evidence_proposal(draft['id'], path=sandbox.db)
                for draft in list_claim_proposals(sandbox.db):
                    if draft['payload']['operation'] == 'create_claim':
                        accept_claim_proposal(draft['id'], path=sandbox.db)
                for draft in list_claim_proposals(sandbox.db):
                    accept_claim_proposal(draft['id'], path=sandbox.db)
                projection = get_wiki(sandbox.db, projected=True)['projection']['organization']
                patch = review_wiki_projection(projection['id'], sandbox.db)
                accept_wiki_proposal(patch['id'], sandbox.db)
                self.assertEqual(len(get_wiki(sandbox.db)['pages']), 1)
                evidence = list_evidence(sandbox.db)[0]
                update_evidence(evidence['id'], {'revision': evidence['revision'],
                    'quote': 'Policy behavior depends on state and the learning objective.'}, sandbox.db)
                fetches = sandbox.fetches
                run = sandbox.run(knowledge_only=True, trigger='recompute')
                self.assertEqual(sandbox.fetches, fetches)
                self.assertEqual(list_runs(sandbox.db, run_id=run)[0]['status'], 'completed')
                changed = [p for p in list_claim_proposals(sandbox.db) if p['payload']['operation'] == 'review_evidence_change']
                self.assertTrue(changed)
                self.assertTrue(all(p['payload'].get('ai_recheck') for p in changed))
                projected = get_wiki(sandbox.db, projected=True)
                self.assertTrue(any(c['id'].startswith('proposal:') for c in projected['claims']))
                self.assertFalse(any('— revised' in c['statement'] for c in list_claims(sandbox.db)))
                # Reopen through fresh connections: pending work and projection survive.
                self.assertEqual(get_wiki(Path(directory) / 'knowte.db', projected=True), projected)
                reopened = subprocess.check_output([sys.executable, '-c',
                    'import json, sys; from pathlib import Path; '
                    'from knowte.knowledge import get_wiki; '
                    'print(json.dumps(get_wiki(Path(sys.argv[1]), projected=True)))',
                    str(sandbox.db)], text=True)
                self.assertEqual(json.loads(reopened), projected)
