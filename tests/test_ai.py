import json
import unittest
from unittest.mock import MagicMock, patch

from knowte.ai import (
    AIConnection,
    AIError,
    OpenAICompatibleClient,
    _api_endpoint,
    cosine_similarity,
)


class OpenAICompatibleClientTests(unittest.TestCase):
    def test_endpoint_accepts_api_root_or_full_resource_path(self):
        self.assertEqual(
            _api_endpoint("https://provider.test/v1", "chat/completions"),
            "https://provider.test/v1/chat/completions",
        )
        self.assertEqual(
            _api_endpoint(
                "https://provider.test/v1/chat/completions",
                "embeddings",
            ),
            "https://provider.test/v1/embeddings",
        )

    def test_chat_and_embedding_use_separate_models_and_connections(self):
        responses = [
            {
                "choices": [
                    {"message": {"content": '{"queries":["semantic retrieval"]}'}}
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 4},
            },
            {
                "data": [
                    {"index": 1, "embedding": [0.0, 1.0]},
                    {"index": 0, "embedding": [1.0, 0.0]},
                ],
                "usage": {"prompt_tokens": 6, "total_tokens": 6},
            },
        ]

        def response(payload):
            context = MagicMock()
            context.__enter__.return_value.read.return_value = json.dumps(
                payload
            ).encode("utf-8")
            return context

        with patch(
            "knowte.ai.urlopen",
            side_effect=[response(item) for item in responses],
        ) as urlopen:
            client = OpenAICompatibleClient(
                AIConnection("https://chat.test/v1", "chat-key"),
                "chat-model",
                AIConnection("https://embed.test/v1", ""),
                "embed-model",
            )
            expanded = client.chat_json("system", "user")
            vectors = client.embeddings(["one", "two"])

        self.assertEqual(expanded["queries"], ["semantic retrieval"])
        self.assertEqual(vectors, [[1.0, 0.0], [0.0, 1.0]])
        first_request = urlopen.call_args_list[0].args[0]
        second_request = urlopen.call_args_list[1].args[0]
        self.assertEqual(
            first_request.full_url,
            "https://chat.test/v1/chat/completions",
        )
        self.assertEqual(
            first_request.headers["Authorization"],
            "Bearer chat-key",
        )
        self.assertEqual(
            second_request.full_url,
            "https://embed.test/v1/embeddings",
        )
        self.assertNotIn("Authorization", second_request.headers)
        self.assertEqual(
            client.usage_snapshot(),
            {
                "chat_requests": 1,
                "chat_tokens": 14,
                "embedding_requests": 1,
                "embedding_tokens": 6,
            },
        )

    def test_private_network_ai_service_bypasses_proxy(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "{}"}}]}
        ).encode("utf-8")
        with patch("knowte.ai.build_opener") as build_opener, patch(
            "knowte.ai.urlopen"
        ) as urlopen:
            build_opener.return_value.open.return_value = response
            client = OpenAICompatibleClient(
                AIConnection("http://192.168.1.12:8000/v1", ""),
                "local-model",
                AIConnection("http://192.168.1.12:8000/v1", ""),
                "",
            )
            client.chat_json("system", "user")

        build_opener.assert_called_once()
        urlopen.assert_not_called()

    def test_reasoning_can_be_disabled_for_compatible_local_services(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "{}"}}]}
        ).encode("utf-8")
        with patch("knowte.ai.build_opener") as build_opener:
            build_opener.return_value.open.return_value = response
            client = OpenAICompatibleClient(
                AIConnection("http://192.168.1.12:8000/v1", ""),
                "local-model",
                AIConnection("http://192.168.1.12:8000/v1", ""),
                "",
                enable_thinking=False,
            )
            client.chat_json("system", "user", max_tokens=128)

        request = build_opener.return_value.open.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload["max_tokens"], 128)
        self.assertEqual(
            payload["chat_template_kwargs"],
            {"enable_thinking": False},
        )

    def test_timeout_has_a_distinct_error_code(self):
        with patch("knowte.ai.build_opener") as build_opener:
            build_opener.return_value.open.side_effect = TimeoutError()
            client = OpenAICompatibleClient(
                AIConnection("http://192.168.1.12:8000/v1", ""),
                "local-model",
                AIConnection("http://192.168.1.12:8000/v1", ""),
                "",
                timeout=45,
            )
            with self.assertRaises(AIError) as raised:
                client.chat_json("system", "user")

        self.assertEqual(raised.exception.code, "timeout")
        self.assertIn("45 seconds", str(raised.exception))

    def test_cosine_similarity(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [1, 0]), 1.0)
        self.assertAlmostEqual(cosine_similarity([1, 0], [0, 1]), 0.0)


if __name__ == "__main__":
    unittest.main()
