"""Offline, disposable automation demo: python -m tests.automation_sandbox."""
import json
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from knowte import usage
from knowte.automation import mutate
from knowte.config import save_config
from knowte.knowledge import create_evidence_proposal, create_claim_proposal
from knowte.plan_runs import queue_run, execute_run
from knowte.server import create_server


class Sandbox:
    def __init__(self, root):
        self.root = root
        self.db = root / 'knowte.db'
        self.config = root / 'config.yaml'
        self.fetches = 0
        self.calls = []
        save_config({'ai_model_profiles': json.dumps([{'id': 'offline', 'name': 'Offline QA',
            'provider': 'openai_compatible', 'base_url': 'http://127.0.0.1:1/v1',
            'model': 'offline-qa', 'capabilities': ['chat']}])}, self.config)
        action = mutate({'operation': 'save_action', 'name': 'RL reading', 'config': {
            'query': 'reinforcement learning', 'sources': ['arxiv']}}, self.db)['saved_id']
        stage = {'enabled': True, 'focus': 'Understand RL policies', 'model_profile_id': 'offline'}
        self.plan = mutate({'operation': 'save_plan', 'name': 'Offline acceptance journey',
            'action_ids': [action], 'processing': {'save_sources': True, 'max_new_sources': 20,
                'evidence': stage, 'claims': stage,
                'relations': {'enabled': True, 'model_profile_id': 'offline'},
                'wiki': {'enabled': True, 'model_profile_id': 'offline'}}}, self.db)['saved_id']

    def retrieve(self, config, *args):
        if config.get('_page', 0):
            return []
        self.fetches += 1
        names = ['A', 'B'] if self.fetches == 1 else ['B', 'C']
        return [{'title': 'RL lesson ' + name, 'url': 'https://example.org/rl/' + name,
            'source': 'arxiv'} for name in names]  # Deliberately no publication dates.

    def evidence(self, payload, config, path, content, *, automation_scope):
        self.calls.append('evidence')
        return {'proposals': [create_evidence_proposal({'source_id': sid,
            'quote': 'Policies select actions; rewards evaluate outcomes.',
            'verification': 'external_unverified'}, 'offline-qa', scope=automation_scope, path=path)
            for sid in payload['source_ids']]}, 201

    def claims(self, payload, config, path, *, evidence_inputs, automation_scope):
        self.calls.append('claims')
        return {'proposals': [create_claim_proposal({'statement': text + ' (' + evidence_inputs[0]['source_id'][:6] + ')',
            'basis': 'reported', 'evidence': [{'evidence_id': item['id'], 'stance': 'supports'} for item in evidence_inputs]},
            'offline-qa', scope=automation_scope, path=path,
            _input_versions={item['id']: item['input_version'] for item in evidence_inputs})
            for text in ['Policies select actions', 'Rewards evaluate policies']]}, 201

    def relations(self, pairs, *args):
        self.calls.append('relations')
        return {'assessments': [{'left_claim_id': a['resolved_id'], 'right_claim_id': b['resolved_id'],
            'judgment': 'related', 'rationale': 'Policy and reward context'} for a, b in pairs]}, {'chat_requests': 1}

    def wiki(self, wiki, selected, *args):
        self.calls.append('wiki')
        return {'pages': [{'key': 'rl', 'title': 'Reinforcement learning', 'parent_key': '',
            'summary': 'Policies select actions; rewards guide learning.', 'claim_ids': [c['id'] for c in selected]}]}, {'chat_requests': 1}

    def recheck(self, draft, *args):
        self.calls.append('recheck')
        return {'claims': [{'statement': draft['statement'] + ' — revised', 'rationale': 'Reflect updated Evidence.'}]}, {'chat_requests': 1}

    def mocks(self):
        stack = ExitStack()
        for target, replacement in [
            ('knowte.plan_runs._retrieve', self.retrieve),
            ('knowte.plan_runs._review', lambda config, candidates, *args: {'results': candidates}),
            ('knowte.server.generate_evidence_proposals', self.evidence),
            ('knowte.server.generate_claim_proposals', self.claims),
            ('knowte.plan_relations._generate', self.relations),
            ('knowte.plan_wiki._generate', self.wiki),
            ('knowte.plan_rechecks._generate', self.recheck),
        ]:
            stack.enter_context(patch(target, side_effect=replacement))
        stack.enter_context(patch.object(usage, 'USAGE_DIR', self.root))
        stack.enter_context(patch.object(usage, 'USAGE_PATH', self.root / 'usage.json'))
        return stack

    def run(self, **kwargs):
        run, _ = queue_run(self.plan, self.db, **kwargs)
        execute_run(run, self.db, self.config)
        return run


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='knowte-acceptance-') as directory:
        sandbox = Sandbox(Path(directory))
        with sandbox.mocks():
            sandbox.run()
            server = create_server('127.0.0.1', 0, sandbox.config, library_name='offline-acceptance')
            print(f'QA_URL=http://127.0.0.1:{server.server_address[1]}/', flush=True)
            try:
                server.serve_forever()
            finally:
                server.server_close()
