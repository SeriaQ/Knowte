"""Disposable manual UI acceptance fixtures; every provider/model is offline."""
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.automation_sandbox import Sandbox
from knowte.automation import mutate, catalog, _database
from knowte import knowledge as k
from knowte.plan_runs import queue_run, execute_run
from knowte.server import create_server


class Scenarios(Sandbox):
    def __init__(self, root):
        super().__init__(root)
        self.failures = 0

    def retrieve(self, config, provider, *args):
        if provider == 'openalex' and self.failures == 0:
            self.failures += 1
            raise TimeoutError('offline injected failure')
        names = ['A', 'B'] if provider == 'arxiv' else ['B', 'C']
        return [{'title': 'RL lesson ' + name, 'url': 'https://example.org/rl/' + name,
            'source': provider} for name in names]

    def seed(self):
        self.run()
        evidence = k.accept_evidence_proposal(k.list_evidence_proposals(self.db)[0]['id'], path=self.db)
        k.update_evidence(evidence['id'], {'revision': k.list_evidence(self.db)[0]['revision'],
            'quote': 'Policies can be stochastic; outcomes depend on the environment.'}, self.db)
        a = catalog(self.db)['actions'][0]['id']
        b = mutate({'operation': 'save_action', 'name': 'Related RL reports',
            'config': {'query': 'RL reports', 'sources': ['openalex']}}, self.db)['saved_id']
        partial = mutate({'operation': 'save_plan', 'name': 'Two channels — retry',
            'action_ids': [a, b], 'processing': {'save_sources': True, 'max_new_sources': 20}}, self.db)['saved_id']
        run, _ = queue_run(partial, self.db)
        execute_run(run, self.db, self.config)
        daily = mutate({'operation': 'save_plan', 'name': 'Daily — catch up once',
            'action_ids': [a], 'schedule': {'type': 'daily', 'time': '08:00', 'timezone': 'Asia/Shanghai'},
            'processing': {'save_sources': True, 'max_new_sources': 20}}, self.db)['saved_id']
        with _database(self.db) as connection:
            connection.execute('UPDATE plan_schedule_state SET next_due_at = ? WHERE plan_id = ?',
                ('2026-09-20T00:00:00+00:00', daily))
        recovery = mutate({'operation': 'save_plan', 'name': 'Interrupted — manual retry',
            'action_ids': [a], 'processing': {'save_sources': True, 'max_new_sources': 20}}, self.db)['saved_id']
        child = subprocess.run([sys.executable, '-c',
            'import os,sys; from pathlib import Path; from knowte.plan_runs import queue_run; '
            'queue_run(sys.argv[2],Path(sys.argv[1])); os._exit(77)', str(self.db), recovery])
        assert child.returncode == 77
        left = k.create_claim({'statement': 'A policy maps observations to action choices.', 'basis': 'background'}, self.db)
        right = k.create_claim({'statement': 'A policy specifies how an agent chooses actions.', 'basis': 'background'}, self.db)
        patch = k.create_wiki_proposal({'pages': [
            {'key': 'foundations', 'title': 'Foundations', 'summary': 'Policy basics', 'claim_ids': [left['id']]},
            {'key': 'agents', 'title': 'Agents', 'summary': f"See [[claim:{right['id']}|policy definition]].", 'claim_ids': [right['id']]},
        ]}, 'offline', path=self.db)
        k.accept_wiki_proposal(patch['id'], self.db)
        k.create_claim_proposal({'operation': 'merge_claims', 'target_claim_id': left['id'],
            'source_claim_id': right['id'], 'merged_statement': 'A policy maps observations to action choices.'}, 'offline', path=self.db)
        orphan = self.root / 'content' / 'evidence' / ('a' * 32 + '.png')
        orphan.parent.mkdir(parents=True, exist_ok=True)
        orphan.write_bytes(b'crash residue')
        return orphan


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='knowte-scenarios-') as directory:
        scenario = Scenarios(Path(directory))
        with scenario.mocks():
            orphan = scenario.seed()
            server = create_server('127.0.0.1', 0, scenario.config, library_name='offline-scenarios')
            assert not orphan.exists(), 'Startup must clear orphan fixture'
            print(f'QA_URL=http://127.0.0.1:{server.server_address[1]}/', flush=True)
            try:
                server.serve_forever()
            finally:
                server.server_close()
