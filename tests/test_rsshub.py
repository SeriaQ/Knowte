import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from knowte import rsshub
from knowte.config import save_config


class InlineThread:
    def __init__(self, target, **kwargs):
        self.target = target
    def start(self):
        self.target()


class RSSHubManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'config.yml'
        self.key, self.name = rsshub.identity(self.path)
        self.addCleanup(lambda: rsshub._JOBS.pop(self.key, None))

    def run_operation(self, operation, existing=None, host='unix:///var/run/docker.sock', fail=None):
        calls = []
        def docker(args, **kwargs):
            calls.append(args)
            if args == fail:
                raise ValueError('simulated failure')
            if args[:2] == ['context', 'inspect']:
                return json.dumps([{'Endpoints': {'docker': {'Host': host}}}])
            if args[0] == 'ps':
                return self.name if existing is not None else ''
            if args[0] == 'inspect':
                return json.dumps([existing])
            return ''
        with patch.object(rsshub, '_docker', side_effect=docker), patch.object(rsshub.threading, 'Thread', InlineThread), patch.dict('os.environ', {'DOCKER_HOST': '', 'DOCKER_CONTEXT': ''}):
            rsshub.start_operation(self.path, operation)
        return calls, rsshub._JOBS[self.key]

    def test_setup_uses_owned_local_binding_without_login_credentials(self):
        save_config({'rsshub_twitter_auth_token': 'private-cookie'}, self.path)
        calls, job = self.run_operation('setup')
        self.assertFalse(job['error'])
        self.assertIn(['pull', rsshub.IMAGE], calls)
        run = next(c for c in calls if c[0] == 'run')
        self.assertIn('127.0.0.1:1200:1200', run)
        self.assertIn(rsshub.LABEL + '=' + self.key, run)
        self.assertNotIn('private-cookie', ' '.join(run))
        env = self.path.parent / 'rsshub' / 'service.env'
        self.assertFalse(env.exists())
        self.assertNotIn('--env-file', run)

    def test_private_token_storage_and_docker_arguments(self):
        rsshub.save_credentials(self.path, {'content': 'TWITTER_AUTH_TOKEN=private-cookie'})
        path = rsshub.credential_path(self.path)
        self.assertEqual(path.read_text(), 'TWITTER_AUTH_TOKEN=private-cookie\n')
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(rsshub.public_credentials(self.path), {'rsshub_managed_env_configured': True})
        self.assertFalse(self.path.exists())
        rsshub.save_credentials(self.path, {'content': ''})
        self.assertTrue(path.exists())
        calls, job = self.run_operation('setup')
        self.assertFalse(job['error'])
        run = next(c for c in calls if c[0] == 'run')
        self.assertEqual(run[run.index('--env-file') + 1], str(path))
        self.assertNotIn('private-cookie', json.dumps(calls) + json.dumps(job))
        rsshub.save_credentials(self.path, {'operation': 'env_clear'})
        self.assertFalse(path.exists())

    def test_invalid_token_cannot_inject_env_variables(self):
        with self.assertRaises(ValueError):
            rsshub.save_credentials(self.path, {'content': 'invalid line'})
        self.assertFalse(rsshub.credential_path(self.path).exists())

    def test_never_modifies_unowned_container(self):
        calls, job = self.run_operation('remove', {'Config': {'Labels': {}}})
        self.assertTrue(job['error'])
        self.assertFalse(any(c[0] in {'rm', 'stop', 'run', 'pull'} for c in calls))

    def test_reboot_uses_env_file_and_existing_image_without_exposing_contents(self):
        env = rsshub.credential_path(self.path)
        rsshub.save_credentials(self.path, {'content': 'TWITTER_AUTH_TOKEN=private-cookie'})
        info = {'Config': {'Labels': {rsshub.LABEL: self.key}}, 'Image': 'sha256:existing', 'State': {'Running': True}}
        calls, job = self.run_operation('reboot', info)
        self.assertFalse(job['error'])
        create = next(c for c in calls if c[0] == 'create')
        self.assertEqual(create[-1], 'sha256:existing')
        self.assertEqual(create[create.index('--env-file') + 1], str(env))
        self.assertNotIn('private-cookie', json.dumps(calls) + json.dumps(job))
        self.assertLess(calls.index(create), calls.index(['stop', self.name]))
        self.assertIn(['rename', self.name + '-replacement', self.name], calls)
        self.assertFalse(any(c[0] == 'pull' for c in calls))
        self.assertTrue(env.exists())

    def test_reboot_invalid_path_leaves_service_untouched(self):
        save_config({'rsshub_env_file': str(self.path.parent / 'missing')}, self.path)
        calls, job = self.run_operation('reboot', {'Config': {'Labels': {rsshub.LABEL: self.key}}})
        self.assertTrue(job['error'])
        self.assertFalse(any(c[0] in {'stop', 'rm', 'create'} for c in calls))

    def test_reinstall_preserves_stopped_state(self):
        info = {'Config': {'Labels': {rsshub.LABEL: self.key}}, 'Image': 'sha256:existing', 'State': {'Running': False}}
        calls, job = self.run_operation('reboot', info)
        self.assertFalse(job['error'])
        self.assertFalse(any(c[0] in {'start', 'stop'} for c in calls))
        self.assertIn(['rename', self.name + '-replacement', self.name], calls)

    def test_reboot_start_failure_restores_previous_container(self):
        info = {'Config': {'Labels': {rsshub.LABEL: self.key}}, 'Image': 'sha256:existing', 'State': {'Running': True}}
        calls, job = self.run_operation('reboot', info, fail=['start', self.name + '-replacement'])
        self.assertTrue(job['error'])
        self.assertIn(['start', self.name], calls)
        self.assertIn(['rm', '-f', self.name + '-replacement'], calls)
        self.assertNotIn(['rm', self.name], calls)

    def test_reboot_create_failure_does_not_stop_old_service(self):
        info = {'Config': {'Labels': {rsshub.LABEL: self.key}}, 'Image': 'sha256:existing', 'State': {'Running': True}}
        calls, _ = self.run_operation('reboot', info)
        create = next(c for c in calls if c[0] == 'create')
        calls, job = self.run_operation('reboot', info, fail=create)
        self.assertTrue(job['error'])
        self.assertNotIn(['stop', self.name], calls)

    def test_removes_only_owned_container_and_keeps_settings(self):
        save_config({'rsshub_base_url': 'http://localhost:1200'}, self.path)
        calls, job = self.run_operation('remove', {'Config': {'Labels': {rsshub.LABEL: self.key}}})
        self.assertFalse(job['error'])
        self.assertIn(['rm', '-f', self.name], calls)
        self.assertTrue(self.path.exists())

    def test_remote_context_refused_before_mutation(self):
        calls, job = self.run_operation('setup', host='ssh://someone@remote')
        self.assertTrue(job['error'])
        self.assertEqual(len(calls), 1)

    def test_no_setup_on_status_and_no_parallel_operations(self):
        with patch.object(rsshub, '_owned', return_value=None):
            self.assertEqual(rsshub.status(self.path)['state'], 'not installed')
        rsshub._JOBS[self.key] = {'running': True}
        with self.assertRaisesRegex(ValueError, 'already running'):
            rsshub.start_operation(self.path, 'setup')

    def test_errors_do_not_expose_docker_output(self):
        class Result:
            returncode = 1
            stdout = ''
            stderr = 'private-credential'
        with patch.object(rsshub, '_docker_process_context', return_value=('docker', {})), patch.object(rsshub.subprocess, 'run', return_value=Result()):
            with self.assertRaises(ValueError) as raised:
                rsshub._docker(['pull', rsshub.IMAGE])
        self.assertNotIn('private-credential', str(raised.exception))


if __name__ == '__main__':
    unittest.main()
