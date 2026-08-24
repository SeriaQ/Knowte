import json
import unittest
from unittest.mock import MagicMock, patch

from knowte.ai import (
    AIConnection,
    AIError,
    OpenAICompatibleClient,
    _api_endpoint,
    _extract_json,
    cosine_similarity,
)


class OpenAICompatibleClientTests(unittest.TestCase):
    @staticmethod
    def _response(payload):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(payload).encode("utf-8")
        return response

    @staticmethod
    def _raw_response(payload):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = payload
        return response

    def test_deepseek_uses_vendor_thinking_contract_without_local_template_args(self):
        response = self._response({
            "choices": [{"message": {"content": '{"claims":[]}'}}],
            "usage": {"total_tokens": 7},
        })
        with patch("knowte.ai.urlopen", return_value=response) as urlopen:
            client = OpenAICompatibleClient(
                AIConnection("https://api.deepseek.com", "key"), "deepseek-v4-pro",
                AIConnection("", ""), "", provider="deepseek", enable_thinking=True,
            )
            result = client.chat_json("Return JSON.", "Propose claims.")
        body = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(body["thinking"], {"type": "enabled"})
        self.assertEqual(body["reasoning_effort"], "high")
        self.assertNotIn("chat_template_kwargs", body)
        self.assertEqual(result, {"claims": []})

    def test_qwen_sends_one_confirmed_pdf_block_and_enables_search(self):
        response = self._response({
            "choices": [{"message": {"content": '{"evidence":[]}'}}],
        })
        with patch("knowte.ai.urlopen", return_value=response) as urlopen:
            client = OpenAICompatibleClient(
                AIConnection("https://dashscope.aliyuncs.com/compatible-mode/v1", "key"),
                "qwen3.8-max", AIConnection("", ""), "", provider="qwen",
                enable_thinking=False,
            )
            result = client.grounded_json(
                "Return JSON.", "Inspect sources.",
                documents=[
                    {"data": b"%PDF-one", "mime_type": "application/pdf", "filename": "one.pdf"},
                ],
                urls=["https://example.test/source"],
            )
        body = json.loads(urlopen.call_args.args[0].data)
        content = body["messages"][1]["content"]
        self.assertEqual([item["type"] for item in content], ["file", "text"])
        self.assertTrue(content[0]["file_data"].startswith("data:application/pdf;base64,"))
        self.assertTrue(body["enable_search"])
        self.assertFalse(body["enable_thinking"])
        self.assertEqual(result, {"evidence": []})

    def test_qwen_rejects_unconfirmed_multi_pdf_contract_without_request(self):
        client = OpenAICompatibleClient(
            AIConnection("https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1", "key"),
            "qwen3.8-max", AIConnection("", ""), "", provider="qwen",
        )
        with patch("knowte.ai.urlopen") as urlopen, self.assertRaises(AIError) as raised:
            client.grounded_json("Return JSON.", "Inspect.", documents=[
                {"data": b"one", "mime_type": "application/pdf"},
                {"data": b"two", "mime_type": "application/pdf"},
            ])
        self.assertEqual(raised.exception.code, "recipe_missing")
        urlopen.assert_not_called()

    def test_kimi_extracts_each_document_before_chat(self):
        responses = [
            self._response({"id": "file-one"}),
            self._raw_response(b"First extracted document."),
            self._response({"deleted": True}),
            self._response({"id": "file-two"}),
            self._raw_response(b"Second extracted document."),
            self._response({"deleted": True}),
            self._response({"choices": [{"message": {"content": '{"evidence":[]}'}}]}),
        ]
        with patch("knowte.ai.urlopen", side_effect=responses) as urlopen:
            client = OpenAICompatibleClient(
                AIConnection("https://api.moonshot.cn/v1", "key"), "kimi-k2.6",
                AIConnection("", ""), "", provider="kimi",
            )
            result = client.grounded_json(
                "Return JSON.", "Inspect.", documents=[
                    {"data": b"one", "mime_type": "application/pdf", "filename": "one.pdf"},
                    {"data": b"two", "mime_type": "application/pdf", "filename": "two.pdf"},
                ],
            )
        self.assertEqual(urlopen.call_count, 7)
        chat = json.loads(urlopen.call_args_list[-1].args[0].data)
        self.assertIn("First extracted document.", chat["messages"][1]["content"])
        self.assertIn("Second extracted document.", chat["messages"][2]["content"])
        self.assertEqual(result, {"evidence": []})

    def test_kimi_completes_builtin_web_search_tool_round(self):
        first = self._response({
            "choices": [{"message": {"role": "assistant", "content": "", "tool_calls": [{
                "id": "call-1", "type": "function",
                "function": {"name": "$web_search", "arguments": '{"query":"Qwen"}'},
            }]}}], "usage": {"total_tokens": 4},
        })
        second = self._response({
            "choices": [{"message": {"content": '{"evidence":[]}'}}],
            "usage": {"total_tokens": 6},
        })
        with patch("knowte.ai.urlopen", side_effect=[first, second]) as urlopen:
            client = OpenAICompatibleClient(
                AIConnection("https://api.moonshot.cn/v1", "key"), "kimi-k2.6",
                AIConnection("", ""), "", provider="kimi", enable_thinking=True,
            )
            result = client.grounded_json(
                "Return JSON.", "Inspect the source.", urls=["https://example.test"],
            )
        first_body = json.loads(urlopen.call_args_list[0].args[0].data)
        second_body = json.loads(urlopen.call_args_list[1].args[0].data)
        self.assertEqual(first_body["thinking"], {"type": "disabled"})
        self.assertEqual(first_body["tools"][0]["function"]["name"], "$web_search")
        self.assertEqual(second_body["messages"][-1]["role"], "tool")
        self.assertEqual(client.usage_snapshot()["chat_tokens"], 10)
        self.assertEqual(result, {"evidence": []})

    def test_google_preset_matches_interactions_rest_contract(self):
        payload = {
            "steps": [{"type": "model_output", "content": [
                {"type": "text", "text": '{"evidence":[]}'},
            ]}],
            "usage": {"total_input_tokens": 10, "total_output_tokens": 4,
                      "total_tokens": 14},
        }
        with patch("knowte.ai.urlopen", return_value=self._response(payload)) as urlopen:
            client = OpenAICompatibleClient(
                AIConnection("https://generativelanguage.googleapis.com/v1beta", "gem-key"),
                "gemini-3.6-flash", AIConnection("", ""), "", provider="google",
            )
            result = client.document_json(
                "Return evidence JSON.", "Inspect this source.", b"%PDF", "application/pdf"
            )

        request = urlopen.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, "https://generativelanguage.googleapis.com/v1beta/interactions")
        self.assertEqual(request.headers["X-goog-api-key"], "gem-key")
        self.assertEqual(body["system_instruction"], "Return evidence JSON.")
        self.assertEqual(body["input"][0]["type"], "document")
        self.assertEqual(body["input"][0]["data"], "JVBERg==")
        self.assertEqual(body["input"][1], {"type": "text", "text": "Inspect this source."})
        self.assertEqual(result, {"evidence": []})
        self.assertEqual(client.usage_snapshot()["chat_tokens"], 14)

    def test_google_grounded_request_sends_multiple_documents_and_url_tool(self):
        payload = {
            "steps": [{"type": "model_output", "content": [
                {"type": "text", "text": '{"evidence":[]}'},
            ]}],
            "usage": {"total_tokens": 9},
        }
        with patch("knowte.ai.urlopen", return_value=self._response(payload)) as urlopen:
            client = OpenAICompatibleClient(
                AIConnection("https://generativelanguage.googleapis.com/v1beta", "gem-key"),
                "gemini-3.7-flash", AIConnection("", ""), "", provider="google",
            )
            result = client.grounded_json(
                "System", "Inspect the supplied sources.",
                documents=[
                    {"data": b"%PDF-one", "mime_type": "application/pdf", "filename": "one.pdf"},
                    {"data": b"%PDF-two", "mime_type": "application/pdf", "filename": "two.pdf"},
                ],
                urls=["https://example.test/source"],
            )

        body = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual([item["type"] for item in body["input"]], [
            "document", "document", "text",
        ])
        self.assertEqual(body["input"][0]["data"], "JVBERi1vbmU=")
        self.assertEqual(body["input"][1]["data"], "JVBERi10d28=")
        self.assertEqual(body["tools"], [{"type": "url_context"}])
        self.assertEqual(result, {"evidence": []})

    def test_anthropic_preset_matches_messages_pdf_contract(self):
        payload = {"content": [{"type": "text", "text": '{"evidence":[]}'}],
                   "usage": {"input_tokens": 8, "output_tokens": 3}}
        with patch("knowte.ai.urlopen", return_value=self._response(payload)) as urlopen:
            client = OpenAICompatibleClient(
                AIConnection("https://api.anthropic.com/v1", "claude-key"), "claude-opus-5",
                AIConnection("", ""), "", provider="anthropic",
            )
            result = client.document_json("System", "Inspect", b"%PDF", "application/pdf")

        request = urlopen.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(request.headers["X-api-key"], "claude-key")
        self.assertEqual(request.headers["Anthropic-version"], "2023-06-01")
        self.assertEqual(body["system"], "System")
        self.assertEqual(body["messages"][0]["content"][0]["type"], "document")
        self.assertEqual(body["messages"][0]["content"][0]["source"]["type"], "base64")
        self.assertEqual(result, {"evidence": []})

    def test_openai_preset_finds_message_after_reasoning_output(self):
        payload = {"output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "content": [
                {"type": "output_text", "text": '{"evidence":[]}'},
            ]},
        ], "usage": {"input_tokens": 12, "output_tokens": 5, "total_tokens": 17}}
        with patch("knowte.ai.urlopen", return_value=self._response(payload)) as urlopen:
            client = OpenAICompatibleClient(
                AIConnection("https://api.openai.com/v1", "openai-key"), "gpt-5",
                AIConnection("", ""), "", provider="openai",
            )
            result = client.document_json("System", "Inspect", b"%PDF", "application/pdf")

        request = urlopen.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(request.headers["Authorization"], "Bearer openai-key")
        self.assertEqual(body["instructions"], "System")
        self.assertEqual(body["input"][0]["content"][0]["type"], "input_file")
        self.assertTrue(body["input"][0]["content"][0]["file_data"].startswith(
            "data:application/pdf;base64,"
        ))
        self.assertEqual(result, {"evidence": []})

    def test_custom_recipe_maps_request_and_response_without_executing_code(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"result": {"text": '{"evidence":[]}'}}
        ).encode("utf-8")
        recipe = {"chat": {
            "url": "{{base_url}}/custom",
            "headers": {"X-Key": "{{api_key}}"},
            "body": {"model": "{{model}}", "instruction": "{{system}}", "query": "{{user}}"},
            "response_text": "$.result.text",
        }}
        with patch("knowte.ai.urlopen", return_value=response) as urlopen:
            client = OpenAICompatibleClient(
                AIConnection("https://custom.test/v1", "secret"), "custom-model",
                AIConnection("", ""), "", provider="custom", custom_recipe=recipe,
            )
            result = client.chat_json("system", "user")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://custom.test/v1/custom")
        self.assertEqual(request.headers["X-key"], "secret")
        self.assertEqual(result, {"evidence": []})

    def test_extract_json_repairs_common_local_model_deviations(self):
        self.assertEqual(
            _extract_json('{"answer":"line one\nline two",}'),
            {"answer": "line one\nline two"},
        )
        self.assertEqual(
            _extract_json("{'answer': 'usable text', 'search_actions': [],}"),
            {"answer": "usable text", "search_actions": []},
        )

    def test_chat_can_preserve_text_when_optional_structure_is_invalid(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "Assessment {not valid JSON}"}}]}
        ).encode("utf-8")
        with patch("knowte.ai.build_opener") as build_opener:
            build_opener.return_value.open.return_value = response
            client = OpenAICompatibleClient(
                AIConnection("http://192.168.1.12:8000/v1", ""),
                "local-model",
                AIConnection("http://192.168.1.12:8000/v1", ""),
                "",
            )
            result = client.chat_json(
                "system", "user", allow_text_fallback=True
            )

        self.assertEqual(result["answer"], "Assessment {not valid JSON}")
        self.assertTrue(result["_structured_output_degraded"])

    def test_chat_returns_original_text_when_required_json_is_invalid(self):
        malformed_text = '{"evidence":[{"quote":"exact"}'
        malformed = self._response({
            "choices": [{"message": {"content": malformed_text}}],
            "usage": {"total_tokens": 11},
        })
        with patch("knowte.ai.build_opener") as build_opener:
            build_opener.return_value.open.return_value = malformed
            client = OpenAICompatibleClient(
                AIConnection("http://localhost:8000/v1", ""), "local-model",
                AIConnection("", ""), "",
            )
            with self.assertRaises(AIError) as raised:
                client.chat_json("Return evidence JSON.", "Inspect this source.")

        self.assertEqual(raised.exception.code, "invalid_model_json")
        self.assertIn(malformed_text, str(raised.exception))
        self.assertEqual(build_opener.return_value.open.call_count, 1)
        self.assertEqual(client.usage_snapshot()["chat_requests"], 1)
        self.assertEqual(client.usage_snapshot()["chat_tokens"], 11)

    def test_endpoint_accepts_api_root_or_full_resource_path(self):
        self.assertEqual(
            _api_endpoint("https://provider.test/v1", "chat/completions"),
            "https://provider.test/v1/chat/completions",
        )

    def test_profile_can_force_direct_connection_for_public_provider(self):
        response = self._response({"choices": [{"message": {"content": "{}"}}]})
        with patch("knowte.ai.build_opener") as build_opener, patch("knowte.ai.urlopen") as urlopen:
            build_opener.return_value.open.return_value = response
            client = OpenAICompatibleClient(
                AIConnection("https://provider.test/v1", "", "direct"),
                "model", AIConnection("", ""), "",
            )
            client.chat_json("system", "user")
        build_opener.assert_called_once()
        urlopen.assert_not_called()

    def test_profile_can_use_explicit_proxy(self):
        response = self._response({"choices": [{"message": {"content": "{}"}}]})
        marker = object()
        with patch("knowte.ai.ProxyHandler", return_value=marker) as proxy_handler, \
             patch("knowte.ai.build_opener") as build_opener:
            build_opener.return_value.open.return_value = response
            client = OpenAICompatibleClient(
                AIConnection(
                    "https://provider.test/v1", "", "custom",
                    "http://127.0.0.1:7890",
                ),
                "model", AIConnection("", ""), "",
            )
            client.chat_json("system", "user")
        proxy_handler.assert_called_once_with({
            "http": "http://127.0.0.1:7890",
            "https": "http://127.0.0.1:7890",
        })
        build_opener.assert_called_once_with(marker)

    def test_system_proxy_mode_delegates_even_private_hosts_to_system_routing(self):
        response = self._response({"choices": [{"message": {"content": "{}"}}]})
        with patch("knowte.ai.urlopen", return_value=response) as urlopen, \
             patch("knowte.ai.build_opener") as build_opener:
            client = OpenAICompatibleClient(
                AIConnection("http://192.168.1.12:8000/v1", "", "system"),
                "model", AIConnection("", ""), "",
            )
            client.chat_json("system", "user")
        urlopen.assert_called_once()
        build_opener.assert_not_called()
        self.assertEqual(
            _api_endpoint(
                "https://provider.test/v1/chat/completions",
                "embeddings",
            ),
            "https://provider.test/v1/embeddings",
        )
        self.assertEqual(
            _api_endpoint(
                "https://generativelanguage.googleapis.com/v1beta/interactions",
                "interactions",
            ),
            "https://generativelanguage.googleapis.com/v1beta/interactions",
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

    def test_chat_accepts_multimodal_user_content(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "{}"}}]}
        ).encode("utf-8")
        with patch("knowte.ai.build_opener") as build_opener:
            build_opener.return_value.open.return_value = response
            client = OpenAICompatibleClient(
                AIConnection("http://192.168.1.12:8000/v1", ""),
                "local-vlm",
                AIConnection("http://192.168.1.12:8000/v1", ""),
                "",
            )
            content = [
                {"type": "text", "text": "Inspect this Evidence."},
                {"type": "image_url", "image_url": {
                    "url": "data:image/png;base64,iVBORw0KGgo="
                }},
            ]
            client.chat_json("system", content)

        request = build_opener.return_value.open.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload["messages"][1]["content"], content)

    def test_chat_forwards_extra_parameters_without_overriding_managed_fields(self):
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
            )
            client.chat_json(
                "system",
                "user",
                temperature=0.2,
                extra_parameters={"top_p": 0.9, "temperature": 1.5, "stream": True},
            )

        request = build_opener.return_value.open.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload["temperature"], 0.2)
        self.assertEqual(payload["top_p"], 0.9)
        self.assertNotIn("stream", payload)

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
