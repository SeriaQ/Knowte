import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import MagicMock, patch

from knowte import usage
from knowte.server import create_server


class SourceDiscoveryApiTests(unittest.TestCase):
    def test_discovers_and_classifies_related_sources(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.yml"
            config_path.write_text(
                "ai_model_profiles: []\n",
                encoding="utf-8",
            )
            seed = {
                "id": "a" * 32,
                "title": "Seed",
                "url": "https://arxiv.org/abs/2412.15115",
                "abstract": "Seed abstract",
            }
            candidate = {
                "id": "paper-2", "title": "Related", "url": "https://paper.test",
                "abstract": "Related abstract", "source": "Semantic Scholar",
            }
            client = MagicMock()
            client.usage_snapshot.return_value = {"chat_requests": 1, "chat_tokens": 20}
            with patch.object(usage, "USAGE_DIR", root), patch.object(
                usage, "USAGE_PATH", root / "usage.json"
            ), patch("knowte.server.list_sources", return_value=[seed]), patch(
                "knowte.server.discover_related_papers",
                return_value={
                    "candidates": [candidate], "requests": 3,
                    "successful_requests": 3, "resolved_seed_count": 1,
                    "unresolved_seed_count": 0,
                },
            ), patch("knowte.server._client_from_config", return_value=client), patch(
                "knowte.server._verify_batched",
                return_value=([{
                    **candidate, "relevance_tier": "strong",
                    "verification_score": .92, "match_reason": "Direct continuation.",
                }], [], 1),
            ):
                server = create_server("127.0.0.1", 0, config_path)
                thread = threading.Thread(target=server.serve_forever)
                thread.start()
                try:
                    connection = HTTPConnection("127.0.0.1", server.server_address[1])
                    connection.request(
                        "POST", "/api/source-discovery",
                        body=json.dumps({
                            "source_ids": [seed["id"]], "focus": "long context",
                            "model_profile_id": "model-1",
                        }),
                        headers={"Content-Type": "application/json"},
                    )
                    response = connection.getresponse()
                    payload = json.loads(response.read())
                    connection.close()
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join()

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["results"][0]["relevance_tier"], "strong")
        self.assertEqual(payload["excluded_results"], [])
        self.assertEqual(payload["candidate_count"], 1)


if __name__ == "__main__":
    unittest.main()
