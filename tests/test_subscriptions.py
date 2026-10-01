import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from knowte.automation import catalog, mutate
from knowte.plan_runs import execute_run, list_runs, queue_run
from knowte.subscriptions import (delete_subscription, fetch_subscription,
    list_subscriptions, parse_feed, save_subscription)


RSS = b'''<rss version="2.0"><channel><title>Blog</title>
<item><guid>a</guid><title>RL A</title><link>https://example.org/a</link>
<description>&lt;b&gt;Hello&lt;/b&gt;</description></item></channel></rss>'''
ATOM = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>b</id>
<title>RL B</title><link href="/b"/><author><name>Alice</name></author>
<summary>Undated entry</summary></entry></feed>'''


class FeedResponse(io.BytesIO):
    headers = {"ETag": '"v1"', "Last-Modified": "Mon, 01 Jan 2024 00:00:00 GMT"}
    def geturl(self):
        return "https://example.org/feed"


class SubscriptionTests(unittest.TestCase):
    def test_saved_channel_is_directly_available_to_plans(self):
        action_id = "channel-" + self.sub
        actions = catalog(self.path)["actions"]
        self.assertEqual(len([a for a in actions if a["id"] == action_id]), 1)
        self.assertEqual(catalog(self.path)["actions"], actions)
        mutate({"operation": "save_plan", "name": "Daily", "action_ids": [action_id]}, self.path)
        self.assertEqual(list_subscriptions(self.path)[0]["used_by"], 1)
        with self.assertRaisesRegex(ValueError, "Plans"):
            delete_subscription(self.sub, self.path)

    def test_unused_channel_can_be_deleted_with_internal_adapter(self):
        delete_subscription(self.sub, self.path)
        self.assertEqual(list_subscriptions(self.path), [])
        self.assertEqual(catalog(self.path)["actions"], [])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "knowte.db"
        for name, value in (("USAGE_DIR", self.path.parent), ("USAGE_PATH", self.path.with_name("usage.json"))):
            mock = patch("knowte.usage." + name, value)
            mock.start()
            self.addCleanup(mock.stop)
        self.config = self.path.with_name("config.yml")
        self.config.write_text("{}")
        self.sub = save_subscription({"name": "AI Blog", "url": "https://example.org/feed"}, self.path)

    def test_rss_atom_and_invalid_content(self):
        rss = parse_feed(RSS, "https://example.org/feed", "Blog")
        atom = parse_feed(ATOM, "https://example.org/feed", "Blog")
        self.assertEqual(rss[0]["title"], "RL A")
        self.assertNotIn("<b>", rss[0]["abstract"])
        self.assertEqual(atom[0]["url"], "https://example.org/b")
        self.assertIsNone(atom[0]["year"])
        self.assertEqual(atom[0]["authors"], "Alice")
        for content in (b"<html/>", b'<!DOCTYPE rss [<!ENTITY x "x">]><rss/>', b"x" * (2 * 1024 * 1024 + 1)):
            with self.assertRaises(ValueError):
                parse_feed(content, "https://example.org", "Blog")

    def test_conditional_fetch_and_durable_shared_cache(self):
        with patch("knowte.subscriptions.urlopen", return_value=FeedResponse(RSS)) as request:
            first = fetch_subscription(self.sub, self.path)
            self.assertEqual(fetch_subscription(self.sub, self.path), first)
            self.assertEqual(request.call_count, 1)
        from knowte.usage import get_usage
        self.assertEqual(get_usage()["last_day_rss"], 1)
        not_modified = HTTPError("https://example.org/feed", 304, "Not modified", {}, None)
        with patch("knowte.subscriptions.urlopen", side_effect=not_modified) as request:
            self.assertEqual(fetch_subscription(self.sub, self.path, force=True), first)
            self.assertEqual(request.call_args.args[0].get_header("If-none-match"), '"v1"')
        self.assertEqual(get_usage()["last_day_rss"], 2)
        with patch("knowte.subscriptions.urlopen", return_value=FeedResponse(ATOM)):
            items = fetch_subscription(self.sub, self.path, force=True)
        self.assertEqual({item["title"] for item in items}, {"RL A", "RL B"})

    def test_fetch_failure_does_not_advance_state(self):
        with patch("knowte.subscriptions.urlopen", side_effect=OSError):
            with self.assertRaises(OSError):
                fetch_subscription(self.sub, self.path)
        self.assertIsNone(list_subscriptions(self.path)[0]["last_fetched_at"])
        with patch("knowte.subscriptions.urlopen", return_value=FeedResponse(b"<html/>")):
            with self.assertRaises(ValueError):
                fetch_subscription(self.sub, self.path)
        self.assertEqual(list_subscriptions(self.path)[0]["cached_count"], 0)

    def test_rsshub_routes_and_duplicates(self):
        item = save_subscription({"name": "Research", "connector": "rsshub", "url": "/researcher/test"}, self.path, "https://hub.example")
        self.assertEqual(save_subscription({"name": "Duplicate", "url": "https://hub.example/researcher/test"}, self.path), item)
        for value in ("//other.example/feed", "/../else", "https://other.example/feed"):
            with self.assertRaises(ValueError):
                save_subscription({"name": "bad", "connector": "rsshub", "url": value}, self.path, "https://hub.example")
        with self.assertRaises(ValueError):
            save_subscription({"name": "bad", "url": "file:///etc/passwd"}, self.path)

    def test_two_plans_consume_shared_subscription_independently(self):
        action = mutate({"operation": "save_action", "kind": "subscribe", "name": "Blogs",
            "config": {"subscription_ids": [self.sub]}}, self.path)["saved_id"]
        plans = [mutate({"operation": "save_plan", "name": name, "action_ids": [action]}, self.path)["saved_id"] for name in ("Daily", "Weekly")]
        with patch("knowte.subscriptions.urlopen", return_value=FeedResponse(RSS)) as fetch:
            counts = []
            for plan in (plans[0], plans[1], plans[0]):
                run, _ = queue_run(plan, self.path)
                execute_run(run, self.path, self.config)
                saved = list_runs(self.path, run_id=run)[0]
                self.assertEqual(saved["status"], "completed")
                self.assertEqual(saved["actions"][0]["config_snapshot"]["subscriptions"][0]["name"], "AI Blog")
                counts.append(saved["counts"]["new_count"])
            self.assertEqual(counts, [1, 1, 0])
            self.assertEqual(fetch.call_count, 1)
        with self.assertRaisesRegex(ValueError, "Actions"):
            delete_subscription(self.sub, self.path)
        self.assertEqual(catalog(self.path)["actions"][0]["kind"], "subscribe")

    def test_mixed_subscription_success_is_partial(self):
        bad = save_subscription({"name": "Bad", "url": "https://bad.example/feed"}, self.path)
        action = mutate({"operation": "save_action", "kind": "subscribe", "name": "Both", "config": {"subscription_ids": [self.sub, bad]}}, self.path)["saved_id"]
        plan = mutate({"operation": "save_plan", "name": "Plan", "action_ids": [action]}, self.path)["saved_id"]
        run, _ = queue_run(plan, self.path)
        with patch("knowte.subscriptions.urlopen", side_effect=[FeedResponse(RSS), OSError()]):
            execute_run(run, self.path, self.config)
        saved = list_runs(self.path, run_id=run)[0]
        self.assertEqual(saved["status"], "partial")
        self.assertNotIn(bad, saved["actions"][0]["checkpoint_after"]["providers"])


if __name__ == "__main__":
    unittest.main()
