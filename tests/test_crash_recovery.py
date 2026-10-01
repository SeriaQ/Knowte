"""Abrupt child-process exits deliberately bypass rollback/finally handlers."""
import base64
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from knowte import knowledge as k
from knowte.automation import mutate
from knowte.plan_runs import queue_run, execute_run, recover_interrupted, list_runs


class CrashRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'knowte.db'
        self.config = self.db.with_name('config.yml')
        action = mutate({'operation': 'save_action', 'name': 'RL',
            'config': {'query': 'RL', 'sources': ['arxiv']}}, self.db)['saved_id']
        self.plan = mutate({'operation': 'save_plan', 'name': 'Daily',
            'action_ids': [action]}, self.db)['saved_id']

    def crash(self, code, *args):
        child = subprocess.run([sys.executable, '-c', code, str(self.db), *args],
            capture_output=True, text=True, timeout=20)
        self.assertEqual(child.returncode, 77, child.stderr)

    def test_acquisition_crash_before_and_after_commit(self):
        for point in ('before', 'after'):
            with self.subTest(point=point):
                self.crash('''
import os, sys
from pathlib import Path
from unittest.mock import patch
from knowte import plan_runs as p
db = Path(sys.argv[1])
run, _ = p.queue_run(sys.argv[2], db)
item = {'title': sys.argv[3], 'url': 'https://example.org/' + sys.argv[3]}
original = p._identity
def identity(*args):
    result = original(*args)
    os._exit(77)
def review(*args):
    os._exit(77)
with patch.object(p, '_identity', identity if sys.argv[3] == 'before' else original):
    p.execute_run(run, db, db.with_name('config.yml'), retrieve=lambda *a: [item], review=review)
''', self.plan, point)
                recover_interrupted(self.db)
                self.assertEqual(list_runs(self.db, self.plan)[0]['status'], 'failed')
                with sqlite3.connect(self.db) as connection:
                    count = connection.execute('SELECT count(*) FROM plan_action_seen').fetchone()[0]
                self.assertEqual(count, 0 if point == 'before' else 2)
                seen = []
                def review(config, candidates, *args):
                    seen.extend(candidates)
                    return {'results': candidates}
                run, _ = queue_run(self.plan, self.db)
                execute_run(run, self.db, self.config,
                    retrieve=lambda *a: [{'title': point, 'url': 'https://example.org/' + point}], review=review)
                self.assertEqual([item['title'] for item in seen], [point])
                self.assertEqual(list_runs(self.db, run_id=run)[0]['status'], 'completed')

    def test_snapshot_crash_cleanup_preserves_referenced_and_foreign_files(self):
        source, _, _ = k.save_source({'title': 'RL', 'url': 'https://example.org/rl'}, path=self.db)
        capture = k.store_capture(source['id'], {'url': source['url'], 'media_type': 'text/html',
            'sha256': 'test', 'raw_path': '', 'segments': ['RL text'], 'locators': ['Intro']}, self.db)
        segment = capture['segments'][0]['id']
        image = 'data:image/png;base64,' + base64.b64encode(b'\x89PNG\r\n\x1a\nfixture').decode()
        saved = k.create_evidence({'segment_id': segment, 'evidence_type': 'snapshot', 'image_data': image}, self.db)
        kept = k.get_snapshot_file(saved['id'], self.db.parent / 'content', self.db)
        self.crash('''
import os, sys
from pathlib import Path
from unittest.mock import patch
from knowte.knowledge import create_evidence
original = Path.write_bytes
def write(path, data):
    original(path, data)
    os._exit(77)
with patch.object(Path, 'write_bytes', write):
    create_evidence({'segment_id': sys.argv[2], 'evidence_type': 'snapshot', 'image_data': sys.argv[3]}, Path(sys.argv[1]))
''', segment, image)
        root = kept.parent
        foreign = root / 'manual.png'
        foreign.write_bytes(b'keep')
        outside = self.db.parent / 'outside.png'
        outside.write_bytes(b'keep')
        link = root / ('f' * 32 + '.png')
        try:
            link.symlink_to(outside)
        except OSError:  # Some Windows test accounts cannot create symlinks.
            link = outside
        self.assertEqual(len(k.list_evidence(self.db)), 1)
        self.assertEqual(k.cleanup_orphan_snapshots(self.db), 1)
        self.assertTrue(all(p.exists() for p in (kept, foreign, outside, link)))
        self.assertEqual(k.cleanup_orphan_snapshots(self.db), 0)

    def test_claim_acceptance_crash_rolls_back_then_retry_accepts_once(self):
        draft = k.create_claim_proposal({'statement': 'RL uses reward', 'basis': 'background'}, 'test', path=self.db)
        self.crash('''
import os, sys
from pathlib import Path
from unittest.mock import patch
from knowte import knowledge as k
original = k.proposal_dependencies.resolve
def resolve(*args, **kwargs):
    original(*args, **kwargs)
    os._exit(77)
with patch.object(k.proposal_dependencies, 'resolve', resolve):
    k.accept_claim_proposal(sys.argv[2], path=Path(sys.argv[1]))
''', draft['id'])
        self.assertEqual(k.list_claims(self.db), [])
        self.assertEqual(k.list_claim_proposals(self.db)[0]['status'], 'awaiting_review')
        k.accept_claim_proposal(draft['id'], path=self.db)
        with self.assertRaises(ValueError):
            k.accept_claim_proposal(draft['id'], path=self.db)
        self.assertEqual(len(k.list_claims(self.db)), 1)

    def test_saved_proposals_survive_exit_before_generation_receipt(self):
        from tests.automation_sandbox import Sandbox
        sandbox = Sandbox(self.db.parent)
        self.crash('''
import os, sys
from pathlib import Path
from tests.automation_sandbox import Sandbox
s = Sandbox.__new__(Sandbox)
s.db = Path(sys.argv[1]); s.root = s.db.parent; s.config = s.root / 'config.yaml'
s.plan = sys.argv[2]; s.fetches = 0; s.calls = []
original = s.evidence
def generate(*args, **kwargs):
    original(*args, **kwargs)
    os._exit(77)
s.evidence = generate
with s.mocks(): s.run()
''', sandbox.plan)
        drafts = {p['id'] for p in k.list_evidence_proposals(self.db)}
        self.assertEqual(len(drafts), 2)
        recover_interrupted(self.db)
        with sandbox.mocks():
            sandbox.run()
        self.assertNotIn('evidence', sandbox.calls)
        self.assertEqual({p['id'] for p in k.list_evidence_proposals(self.db)}, drafts)
        self.assertTrue(k.get_wiki(self.db, projected=True)['claims'])
        self.assertEqual(k.list_claims(self.db), [])
