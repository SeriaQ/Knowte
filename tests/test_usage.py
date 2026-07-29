import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from knowte import usage


class UsageLimitTests(unittest.TestCase):
    def test_concurrent_requests_do_not_lose_counts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            usage_path = Path(temp_dir) / "usage.json"
            with patch.object(usage, "USAGE_DIR", usage_path.parent), patch.object(
                usage, "USAGE_PATH", usage_path
            ):
                threads = [
                    threading.Thread(
                        target=usage.record_request,
                        args=(["arxiv", "websearch"], 1_700_000_000 + index),
                    )
                    for index in range(40)
                ]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
                result = usage.get_usage(now=1_700_000_100)

        self.assertEqual(result["last_day"], 40)
        self.assertEqual(result["last_day_web"], 40)

    def test_web_only_request_ignores_exhausted_paper_limit(self):
        current = {
            "last_5_min": usage.PAPER_5MIN_LIMIT,
            "last_day": usage.PAPER_DAY_LIMIT,
            "last_5_min_web": 0,
            "last_day_web": 0,
        }

        with patch.object(usage, "get_usage", return_value=current):
            result = usage.can_request(backends=["websearch"])

        self.assertTrue(result["allowed"])
        self.assertTrue(result["allowed_web"])

    def test_paper_only_request_ignores_exhausted_web_limit(self):
        current = {
            "last_5_min": 0,
            "last_day": 0,
            "last_5_min_web": usage.WEB_5MIN_LIMIT,
            "last_day_web": usage.WEB_DAY_LIMIT,
        }

        with patch.object(usage, "get_usage", return_value=current):
            result = usage.can_request(backends=["arxiv"])

        self.assertTrue(result["allowed"])
        self.assertTrue(result["allowed_web"])

    def test_record_request_counts_paper_and_web_independently(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            usage_path = Path(temp_dir) / "usage.json"
            with patch.object(usage, "USAGE_DIR", usage_path.parent), patch.object(
                usage, "USAGE_PATH", usage_path
            ):
                paper = usage.record_request(["arxiv"], now=1_700_000_000)
                both = usage.record_request(
                    ["arxiv", "websearch"], now=1_700_000_001
                )

        self.assertEqual(paper["last_day"], 1)
        self.assertEqual(paper["last_day_web"], 0)
        self.assertEqual(both["last_day"], 2)
        self.assertEqual(both["last_day_web"], 1)

    def test_ai_usage_tracks_requests_and_tokens(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            usage_path = Path(temp_dir) / "usage.json"
            with patch.object(usage, "USAGE_DIR", usage_path.parent), patch.object(
                usage, "USAGE_PATH", usage_path
            ):
                result = usage.record_ai_usage(
                    chat_requests=2,
                    chat_tokens=150,
                    embedding_requests=1,
                    embedding_tokens=80,
                    now=1_700_000_000,
                )

        self.assertEqual(result["last_day_ai_chat"], 2)
        self.assertEqual(result["last_day_ai_chat_tokens"], 150)
        self.assertEqual(result["last_day_ai_embedding"], 1)
        self.assertEqual(result["last_day_ai_embedding_tokens"], 80)


if __name__ == "__main__":
    unittest.main()
