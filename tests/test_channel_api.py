import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

from knowte.config import save_config, load_config
from knowte.server import create_server


class ChannelApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'config.yml'
        save_config({'github_token': 'private-token', 'enabled_backends': 'arxiv'}, self.path)
        self.server = create_server('127.0.0.1', 0, self.path)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.addCleanup(self.close_server)

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, origin=None):
        connection = HTTPConnection('127.0.0.1', self.server.server_address[1], timeout=10)
        headers = {'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        try:
            connection.request(method, path, json.dumps(body) if body is not None else None, headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_detect_preview_save_list_and_empty_result(self):
        status, result = self.request('POST', '/api/subscriptions', {'operation': 'detect', 'url': 'reinforcement learning', 'category': 'hackernews', 'hn_mode': 'keyword'})
        self.assertEqual(status, 200)
        spec = result['choices'][0]
        with patch('knowte.channel_connectors.acquire', return_value=[]):
            status, preview = self.request('POST', '/api/subscriptions', {'operation': 'preview', 'spec': spec})
        self.assertEqual(status, 200)
        self.assertIn('does not confirm', preview['message'])
        self.assertIn('up to 100 posts and 100 comments', preview['message'])
        self.assertEqual(preview['groups'], [{'type': 'story', 'count': 0, 'items': []}, {'type': 'comment', 'count': 0, 'items': []}])
        self.assertEqual(self.request('GET', '/api/subscriptions')[1]['subscriptions'], [])
        status, saved = self.request('POST', '/api/subscriptions', {'spec': spec, 'name': 'Karpathy'})
        self.assertEqual(status, 200)
        self.assertEqual(saved['subscriptions'][0]['connector'], 'hn_keyword')
        self.assertNotIn('private-token', json.dumps(saved))

    def test_configuration_hides_preserves_and_removes_credentials(self):
        status, config = self.request('GET', '/api/config')
        self.assertEqual(status, 200)
        self.assertTrue(config['github_token_configured'])
        self.assertNotIn('private-token', json.dumps(config))
        payload = {'email': '', 'enabled_backends': ['arxiv'], 'github_token': '', 'rsshub_base_url': 'http://localhost:1200', 'rsshub_env_file': '/private/rsshub.env'}
        status, result = self.request('POST', '/api/config', payload)
        self.assertEqual(status, 200, result)
        self.assertEqual(load_config(self.path)['github_token'], 'private-token')
        self.assertEqual(result['rsshub_base_url'], 'http://localhost:1200')
        self.assertNotIn('rsshub_env_file', result)
        self.assertNotIn('rsshub_env_file', load_config(self.path))
        status, result = self.request('POST', '/api/config', {**payload, 'clear_github_token': True})
        self.assertEqual(status, 200, result)
        self.assertFalse(result['github_token_configured'])

    def test_edit_channel_roundtrip(self):
        spec = {'kind': 'hn_keyword', 'query': 'RL'}
        status, saved = self.request('POST', '/api/subscriptions', {'name':'RL', 'spec':spec})
        self.assertEqual(status, 200)
        item = saved['subscriptions'][0]
        status, changed = self.request('POST', '/api/subscriptions', {'id':item['id'], 'version':item['version'], 'name':'RL news',
            'spec':spec, 'processing':{'mode':'intelligent','query':'robotics','model_profile_id':'test-model'}})
        self.assertEqual(status, 200, changed)
        self.assertEqual(changed['subscriptions'][0]['processing']['query'], 'robotics')
        self.assertEqual(changed['subscriptions'][0]['version'], item['version'] + 1)

    def test_docker_and_external_writes_reject_other_origins(self):
        with patch('knowte.rsshub.start_operation') as run:
            status, _ = self.request('POST', '/api/rsshub', {'operation': 'setup'}, 'https://other.example')
        self.assertEqual(status, 403)
        run.assert_not_called()
        status, _ = self.request('POST', '/api/subscriptions', {'operation': 'detect', 'url': 'https://news.ycombinator.com/newest'}, 'https://other.example')
        self.assertEqual(status, 403)



if __name__ == '__main__':
    unittest.main()
