import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from knowte import channel_connectors as cc
from knowte.automation import mutate
from knowte.config import export_config, save_config
from knowte.plan_runs import execute_run, queue_run, list_runs
from knowte.subscriptions import save_subscription, fetch_subscription, list_subscriptions, delete_subscription

RSS = b'<rss><channel><item><guid>a</guid><title>A</title><link>https://example.org/a</link></item></channel></rss>'


class ChannelConnectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'knowte.db'
        for name, value in (("USAGE_DIR", self.db.parent), ("USAGE_PATH", self.db.with_name("usage.json"))):
            mock = patch("knowte.usage." + name, value)
            mock.start()
            self.addCleanup(mock.stop)
        self.config_path = self.db.with_name('config.yml')

    def test_site_discovers_only_valid_declared_same_site_feeds(self):
        page = b'''<html><link rel="alternate" type="application/rss+xml" href="/bad"><link rel="alternate" type="application/atom+xml" href="https://other.org/feed"><link rel="alternate" type="application/rss+xml" href="/feed" title="Blog"></html>'''
        with patch.object(cc, '_read', side_effect=[page, b'not XML', RSS]) as read:
            result = cc.detect('https://example.org', {})
        self.assertEqual(len(result['choices']), 1)
        self.assertEqual(result['choices'][0]['source_url'], 'https://example.org/feed')
        self.assertEqual(read.call_count, 3)

    def test_json_requests_use_api_counter(self):
        with patch.object(cc, '_read', return_value=b'{}') as read:
            cc._json('https://api.github.com/users/example')
        self.assertEqual(read.call_args.kwargs['request_kind'], 'subscription_api')

    def test_public_channel_types_and_removed_logins(self):
        self.assertEqual(cc.recognize('https://github.com/SeriaQ')['kind'], 'github')
        self.assertEqual(cc.recognize('https://github.com/SeriaQ/Knowte/releases')['account'], 'seriaq/knowte')
        spec = cc.detect('reinforcement learning', {}, 'hackernews')['choices'][0]
        self.assertEqual(spec['query'], 'reinforcement learning')
        with patch.object(cc, '_json', return_value={'id': 'pg'}):
            spec = cc.detect('https://news.ycombinator.com/user?id=pg', {}, 'hackernews', 'user')['choices'][0]
        self.assertEqual(spec['account'], 'pg')
        for url in ['https://github.com/trending', 'https://news.ycombinator.com/newest']:
            with self.assertRaises(ValueError):
                cc.recognize(url)
        with self.assertRaisesRegex(ValueError, 'no longer supported'):
            cc.clean_spec({'kind': 'hackernews'})
        for url in ['https://x.com/karpathy', 'https://mp.weixin.qq.com/s/article']:
            with self.assertRaisesRegex(ValueError, 'not managed'):
                cc.detect(url, {})
        with self.assertRaisesRegex(ValueError, 'does not match'):
            cc.detect('https://github.com/seriaq', {}, 'others')
        with self.assertRaises(ValueError):
            cc.recognize('https://news.ycombinator.com/item?id=1')
        with self.assertRaisesRegex(ValueError, 'Replace old'):
            cc.acquire({'kind': 'wechat'}, {}, 'Old channel')

    def test_repository_releases_exclude_drafts_and_deduplicate_channel(self):
        with patch.object(cc, '_json', return_value={'id': 1, 'full_name': 'SeriaQ/Knowte'}):
            spec = cc.detect('https://github.com/SeriaQ/Knowte', {}, 'github')['choices'][0]
        self.assertEqual(spec['scopes'], [])
        with self.assertRaisesRegex(ValueError, 'at least one'):
            cc.clean_spec(spec)
        spec['scopes'] = ['releases']
        items = [{'id': 1, 'name': 'v1', 'html_url': 'https://github.com/SeriaQ/Knowte/releases/tag/v1', 'body': 'notes'},
                 {'id': 2, 'draft': True}, {'id': 3, 'html_url': 'https://evil.example/release'}]
        with patch.object(cc, '_json', return_value=items) as api:
            self.assertEqual(len(cc.acquire(spec, {}, 'Releases')), 1)
            self.assertIn('/repos/seriaq/knowte/releases?', api.call_args.args[0])
        saved = save_subscription({'name': 'Releases', 'spec': spec}, self.db)
        self.assertEqual(save_subscription({'name': 'Again', 'spec': {**spec, 'source_url': spec['source_url'] + '/releases'}}, self.db), saved)

    def test_hackernews_story_mapping_and_partial_failure(self):
        spec = cc.hn_spec('keyword', 'reinforcement learning')
        def api(url):
            params = parse_qs(urlsplit(url).query)
            self.assertEqual(params['query'], ['reinforcement learning'])
            comment = params['tags'] == ['comment']
            self.assertEqual(params['restrictSearchableAttributes'], ['comment_text' if comment else 'title,story_text,url'])
            return {'hits': [{'objectID': '2' if comment else '1', 'title': 'Article',
                    'story_id': 1, 'url': 'https://example.org/article', 'created_at': '2026-09-29T00:00:00Z',
                    'comment_text': '<p>Learning &amp; planning</p>'}], 'nbPages': 1}
        with patch.object(cc, '_json', side_effect=api):
            items = cc.acquire(spec, {}, 'HN')
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['url'], 'https://example.org/article')
        self.assertEqual(items[1]['url'], 'https://news.ycombinator.com/item?id=2')
        self.assertEqual(items[1]['abstract'], 'Learning & planning')
        self.assertEqual([i['channel_item_type'] for i in items], ['story', 'comment'])
        self.assertEqual(items[0]['abstract'], '')
        with patch.object(cc, '_json', side_effect=[{'hits': []}, ValueError('network failed')]):
            with self.assertRaisesRegex(ValueError, 'network failed'):
                cc.acquire(spec, {}, 'HN')

    def test_release_small_pages_and_explicit_scope(self):
        spec = {**cc.recognize('https://github.com/astral-sh/uv'), 'scopes': ['releases']}
        item = {'id': 1, 'html_url': 'https://github.com/astral-sh/uv/releases/tag/1'}
        with patch.object(cc, '_json', side_effect=[[item] * 20, [item]]) as api:
            self.assertEqual(len(cc.acquire(spec, {}, 'uv')), 21)
        self.assertTrue(api.call_args_list[0].args[0].endswith('per_page=20&page=1'))
        self.assertTrue(api.call_args_list[1].args[0].endswith('per_page=20&page=2'))
        with patch.object(cc, '_json', return_value=[item] * 20) as api:
            self.assertEqual(len(cc.acquire(spec, {}, 'uv')), 300)
        self.assertEqual(api.call_count, 15)
        self.assertIn('not a full archive', cc.fetch_scope('github_releases'))

    def test_oversize_later_page_does_not_commit_and_run_shows_reason(self):
        spec = {**cc.recognize('https://github.com/astral-sh/uv'), 'scopes': ['releases']}
        channel = save_subscription({'name': 'uv', 'spec': spec}, self.db)
        item = {'id': 1, 'html_url': 'https://github.com/astral-sh/uv/releases/tag/1'}
        with patch.object(cc, '_json', side_effect=[[item] * 20, cc.ChannelResponseTooLarge('oversize')]):
            with self.assertRaisesRegex(cc.ChannelResponseTooLarge, 'page 2.*2 MiB'):
                fetch_subscription(channel, self.db, force=True)
        self.assertEqual(list_subscriptions(self.db)[0]['cached_count'], 0)
        self.assertFalse(list_subscriptions(self.db)[0]['last_fetched_at'])
        plan = mutate({'operation': 'save_plan', 'name': 'uv', 'action_ids': ['channel-' + channel]}, self.db)['saved_id']
        save_config({}, self.config_path)
        run, _ = queue_run(plan, self.db)
        with patch.object(cc, '_json', side_effect=cc.ChannelResponseTooLarge('Fetch stopped: 2 MiB safety limit.')):
            execute_run(run, self.db, self.config_path)
        detail = list_runs(self.db, run_id=run)[0]['actions'][0]
        self.assertIn('exceeded 2 MiB', detail['report']['providers'][channel]['error'])
        self.assertEqual(detail['checkpoint_after'], {})

    def test_removed_credentials_are_cleared_on_save(self):
        old = {key: 'private' for key in ('werss_mode', 'werss_base_url', 'werss_token', 'rsshub_twitter_auth_token')}
        self.assertEqual(cc.update_settings(old, {}), {})

    def test_edit_channel_keeps_identity_and_versions_action(self):
        from knowte.automation import _database
        spec = {**cc.recognize('https://github.com/pytest-dev/pytest'), 'scopes': ['releases']}
        channel = save_subscription({'name': 'pytest', 'spec': spec}, self.db)
        before = list_subscriptions(self.db)[0]
        changed = {**before['spec'], 'scopes': ['commits']}
        save_subscription({'id': channel, 'version': before['version'], 'name': 'pytest updates', 'spec': changed,
            'processing': {'mode': 'intelligent', 'query': 'testing APIs', 'model_profile_id': 'm'}}, self.db)
        after = list_subscriptions(self.db)[0]
        self.assertEqual(after['id'], channel)
        self.assertEqual(after['version'], before['version'] + 1)
        self.assertEqual(after['processing']['query'], 'testing APIs')
        self.assertEqual(after['processing']['mode'], 'intelligent')
        with self.assertRaisesRegex(ValueError, 'changed'):
            save_subscription({'id': channel, 'version': before['version'], 'name': 'stale', 'spec': changed}, self.db)
        with _database(self.db) as c:
            self.assertEqual(c.execute('select name from actions where id=?', ('channel-' + channel,)).fetchone()[0], 'pytest updates')

    def test_focus_edit_does_not_reconsume_previous_items(self):
        spec = cc.hn_spec('keyword', 'RL')
        channel = save_subscription({'name': 'HN', 'spec': spec}, self.db)
        plan = mutate({'operation':'save_plan', 'name':'Daily', 'action_ids':['channel-' + channel],
                       'processing': {'save_sources': False, 'max_new_sources': 20}}, self.db)['saved_id']
        save_config({}, self.config_path)
        article = {'id':'123', 'title':'RL', 'url':'https://news.ycombinator.com/item?id=123', 'paper_url':'https://news.ycombinator.com/item?id=123', 'result_type':'web'}
        with patch.object(cc, 'acquire', return_value=[article]):
            run, _ = queue_run(plan, self.db)
            execute_run(run, self.db, self.config_path)
        save_subscription({'id':channel, 'version':1, 'name':'HN', 'spec':spec,
            'processing': {'mode':'intelligent','query':'Robotics','model_profile_id':'m'}}, self.db)
        with patch.object(cc, 'acquire', return_value=[article]), patch('knowte.plan_runs._review') as review:
            run, _ = queue_run(plan, self.db)
            execute_run(run, self.db, self.config_path)
        review.assert_not_called()

    def test_edit_blocked_during_run_and_snapshots_preserved(self):
        from knowte.automation import _database
        spec = cc.hn_spec('keyword', 'robotics')
        channel = save_subscription({'name': 'HN', 'spec': spec}, self.db)
        plan = mutate({'operation': 'save_plan', 'name': 'Daily', 'action_ids': ['channel-' + channel]}, self.db)['saved_id']
        run, _ = queue_run(plan, self.db)
        with self.assertRaisesRegex(ValueError, 'active Plans'):
            save_subscription({'id': channel, 'version': 1, 'name': 'New', 'spec': cc.hn_spec('keyword', 'RL')}, self.db)
        with _database(self.db) as c:
            c.execute("UPDATE plan_runs SET status='completed' WHERE id=?", (run,))
        save_subscription({'id': channel, 'version': 1, 'name': 'New', 'spec': cc.hn_spec('keyword', 'RL')}, self.db)
        with _database(self.db) as c:
            old = json.loads(c.execute('select config_snapshot from action_runs where run_id=?', (run,)).fetchone()[0])
        self.assertEqual(old['subscriptions'][0]['connector']['query'], 'robotics')

    def test_channel_verify_uses_shared_tiers_and_subscription_role(self):
        from unittest.mock import Mock
        from knowte.plan_runs import _review
        client = Mock()
        client.usage_snapshot.return_value = {'chat_requests': 1, 'chat_tokens': 100}
        config = {'kind': 'subscribe', 'mode': 'intelligent', 'query': 'RL', 'model_profile_id': 'm'}
        assessed = [{'id': '1', 'relevance_tier': 'strong'}, {'id': '2', 'relevance_tier': 'possible'}, {'id': '3', 'relevance_tier': 'excluded'}]
        with patch('knowte.plan_runs.ai_model_profiles', return_value=[{'id': 'm', 'capabilities': ['chat']}]), \
             patch('knowte.intelligent._client_from_config', return_value=client) as make_client, \
             patch('knowte.intelligent._verify_batched', return_value=(assessed, [], 1)) as verify, \
             patch('knowte.usage.record_ai_usage'):
            result = _review(config, [{'title': 'post'}], {}, self.config_path)
        self.assertEqual(make_client.call_args.kwargs['role'], 'subscription_verify')
        self.assertFalse(make_client.call_args.kwargs['require_embedding'])
        self.assertEqual(len(result['results']), 2)
        self.assertEqual(result['excluded_results'][0]['id'], '3')
        self.assertIn('not an assumed full article', verify.call_args.args[-1])

    def test_repository_scopes_branch_and_issue_pr_separation(self):
        spec = {**cc.recognize('https://github.com/pytest-dev/pytest/'),
                'scopes': ['commits', 'issues', 'pulls'], 'branch': 'feature/test'}
        def api(url, **kwargs):
            params = parse_qs(urlsplit(url).query)
            scope = urlsplit(url).path.split('/')[-1]
            self.assertEqual(params['per_page'], ['20'])
            if scope == 'commits':
                self.assertEqual(params['sha'], ['feature/test'])
                return [{'sha': 'abc', 'html_url': 'https://github.com/pytest-dev/pytest/commit/abc',
                         'commit': {'message': 'Fix\n\nDescription', 'committer': {'date': '2026-09-29'}}}]
            self.assertEqual(params['state'], ['all'])
            item = {'id': 1, 'html_url': 'https://github.com/pytest-dev/pytest/' + scope + '/1', 'title': scope}
            return [item, {**item, 'pull_request': {}}] if scope == 'issues' else [item]
        with patch.object(cc, '_json', side_effect=api):
            items = cc.acquire(spec, {}, 'pytest')
        self.assertEqual([item['channel_item_type'] for item in items], ['commits', 'issues', 'pulls'])
        self.assertEqual(len({item['id'] for item in items}), 3)
        self.assertEqual(items[0]['abstract'], 'Fix\n\nDescription')

    def test_hn_user_pagination_and_atomic_cache(self):
        spec = cc.hn_spec('user', 'pg')
        item = {'objectID': '2', 'comment_text': 'hello', 'author': 'pg'}
        with patch.object(cc, '_json', return_value={'hits': [item] * 20, 'nbPages': 100}) as api:
            items = cc.acquire(spec, {}, 'pg')
        self.assertEqual(api.call_count, 10)
        self.assertEqual(len(items), 200)
        self.assertEqual(parse_qs(urlsplit(api.call_args_list[0].args[0]).query)['tags'], ['story,author_pg'])
        self.assertEqual(parse_qs(urlsplit(api.call_args_list[5].args[0]).query)['tags'], ['comment,author_pg'])
        channel = save_subscription({'name': 'pg', 'spec': spec}, self.db)
        with patch.object(cc, '_json', side_effect=[{'hits': [item]}, ValueError('comment request failed')]):
            with self.assertRaisesRegex(ValueError, 'comment request failed'):
                fetch_subscription(channel, self.db, force=True)
        self.assertEqual(list_subscriptions(self.db)[0]['cached_count'], 0)
        self.assertFalse(list_subscriptions(self.db)[0]['last_fetched_at'])

    def test_legacy_releases_not_silently_reinterpreted(self):
        spec = {'kind': 'github_releases', 'source_url': 'https://github.com/pytest-dev/pytest'}
        saved = save_subscription({'name': 'Old releases', 'spec': spec}, self.db)
        self.assertEqual(cc.clean_spec(spec)['kind'], 'github_releases')
        with self.assertRaisesRegex(ValueError, 'another scope'):
            save_subscription({'name': 'Commits', 'spec': {**spec, 'kind': 'github_repo', 'scopes': ['commits']}}, self.db)
        self.assertEqual(list_subscriptions(self.db)[0]['id'], saved)

    def test_account_has_no_default_scope_and_hn_user_validation(self):
        with patch.object(cc, '_json', return_value={'id': 1, 'login': 'seriaq'}):
            spec = cc.detect('https://github.com/seriaq', {}, 'github')['choices'][0]
        self.assertEqual(spec['event_types'], [])
        with self.assertRaises(ValueError):
            cc.clean_spec(spec)
        with patch.object(cc, '_json', return_value=None), self.assertRaisesRegex(ValueError, 'not found'):
            cc.detect('nonexistent', {}, 'hackernews', 'user')

    def test_github_uses_bounded_official_api_and_configured_scope(self):
        events = [
            {'id': '1', 'type': 'ReleaseEvent', 'repo': {'name': 'me/repo'}, 'payload': {'release': {'name': 'v1', 'html_url': 'https://github.com/me/repo/releases/tag/v1'}}},
            {'id': '2', 'type': 'WatchEvent', 'repo': {'name': 'me/other'}, 'payload': {}},
            {'id': '3', 'type': 'PushEvent', 'repo': {'name': 'me/repo'}, 'payload': {'head': 'a' * 40}},
        ]
        spec = cc.clean_spec({'kind': 'github', 'source_url': 'https://github.com/SeriaQ', 'event_types': ['ReleaseEvent', 'PushEvent']})
        with patch.object(cc, '_json', return_value=events) as api:
            items = cc.acquire(spec, {'github_token': 'secret'}, 'Me')
        self.assertEqual(len(items), 2)
        self.assertTrue(items[1]['url'].endswith('/commit/' + 'a' * 40))
        self.assertTrue(api.call_args.args[0].startswith('https://api.github.com/users/seriaq/events/public'))
        self.assertEqual(api.call_args.kwargs['token'], 'secret')
        with patch.object(cc, '_json', return_value=[events[0]] * 100) as api:
            cc.acquire(spec, {}, 'Me')
        self.assertEqual(api.call_count, 3)

    def test_shared_cache_preserves_independent_plan_consumption(self):
        spec = {'kind': 'github', 'source_url': 'https://github.com/seriaq', 'event_types': ['ReleaseEvent']}
        channel = save_subscription({'name': 'X', 'spec': spec}, self.db)
        save_config({}, self.config_path)
        plans = [mutate({'operation': 'save_plan', 'name': n, 'action_ids': ['channel-' + channel]}, self.db)['saved_id'] for n in ('A', 'B')]
        with patch.object(cc, 'acquire', return_value=[{'id': '1', 'title': 'Release', 'url': 'https://github.com/a/b/releases/tag/1', 'paper_url': 'https://github.com/a/b/releases/tag/1', 'source': 'GitHub', 'result_type': 'web'}]) as read:
            for plan in plans:
                run, _ = queue_run(plan, self.db)
                execute_run(run, self.db, self.config_path)
            self.assertEqual(read.call_count, 1)
        for plan in plans:
            self.assertEqual(list_runs(self.db, plan)[0]['counts']['new_count'], 1)
        self.assertEqual(list_subscriptions(self.db)[0]['connector'], 'github')

    def test_duplicate_channel_never_silently_changes_scope(self):
        spec = {'kind': 'github', 'source_url': 'https://github.com/seriaq', 'event_types': ['ReleaseEvent']}
        saved = save_subscription({'name': 'X', 'spec': spec}, self.db)
        self.assertEqual(save_subscription({'name': 'X again', 'spec': spec}, self.db), saved)
        with self.assertRaisesRegex(ValueError, 'different scope'):
            save_subscription({'name': 'X', 'spec': {**spec, 'event_types': ['PushEvent']}}, self.db)

    def test_credentials_are_preserved_redacted_and_never_returned(self):
        config = {'github_token': 'secret-value', 'rsshub_twitter_auth_token': 'key-value'}
        updated = cc.update_settings(config, {'github_token': '', 'rsshub_base_url': 'http://localhost:1200/'})
        self.assertEqual(updated['github_token'], 'secret-value')
        self.assertTrue(cc.public_settings(updated)['github_token_configured'])
        self.assertNotIn('secret-value', json.dumps(cc.public_settings(updated)))
        save_config(updated, self.config_path)
        exported = export_config(self.config_path).decode()
        self.assertNotIn('secret-value', exported)
        self.assertNotIn('key-value', exported)
        self.assertNotIn('github_token', cc.update_settings(updated, {'clear_github_token': True}))

    def test_auth_does_not_follow_cross_origin_redirect(self):
        def opener(handler):
            class Fake:
                def open(self, request, timeout):
                    return handler.redirect_request(request, None, 302, '', {}, 'https://evil.example/')
            return Fake()
        with patch.object(cc, 'build_opener', side_effect=opener), self.assertRaisesRegex(ValueError, 'Cross-origin'):
            cc._read('https://api.github.com/users/me', token='secret')


if __name__ == '__main__':
    unittest.main()
