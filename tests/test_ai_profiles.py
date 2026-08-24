import tempfile
import unittest
from pathlib import Path

from knowte.config import (
    ai_model_profiles,
    ai_profile_for_role,
    ai_role_assignments,
    load_config,
    save_config,
    set_ai_model_profiles,
)
from knowte.intelligent import _client_from_config
from knowte.server import _map_document_quote


class AIModelProfileTests(unittest.TestCase):
    def test_provider_model_and_endpoint_lock_advanced_capabilities(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yml"
            profiles = [
                {"id": "deep", "name": "DeepSeek", "provider": "deepseek",
                 "base_url": "https://api.deepseek.com", "model": "deepseek-v4-pro",
                 "capabilities": ["chat", "native_documents", "web_search"]},
                {"id": "qwen-public", "name": "Qwen public", "provider": "qwen",
                 "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                 "model": "qwen3.8-max",
                 "capabilities": ["chat", "native_documents", "web_search"]},
                {"id": "qwen-beijing", "name": "Qwen PDF", "provider": "qwen",
                 "base_url": "https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
                 "model": "qwen3.8-max",
                 "capabilities": ["chat", "native_documents", "web_search"]},
                {"id": "kimi", "name": "Kimi", "provider": "kimi",
                 "base_url": "https://api.moonshot.cn/v1", "model": "kimi-k2.5",
                 "capabilities": ["chat", "file_extraction", "web_search"]},
            ]
            set_ai_model_profiles(profiles, {"copilot": "deep"}, path)
            stored = {item["id"]: item for item in ai_model_profiles(load_config(path))}
        self.assertEqual(stored["deep"]["capabilities"], ["chat"])
        self.assertEqual(stored["qwen-public"]["capabilities"], ["chat", "web_search"])
        self.assertEqual(
            stored["qwen-beijing"]["capabilities"],
            ["chat", "native_documents", "web_search"],
        )
        self.assertEqual(stored["kimi"]["capabilities"], ["chat", "file_extraction"])

    def test_legacy_models_are_projected_and_preserve_secrets_on_first_save(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yml"
            save_config({
                "ai_provider": "google",
                "ai_base_url": "https://example.test/v1",
                "ai_api_key": "secret",
                "ai_chat_model": "gemini-test",
                "ai_embedding_model": "embed-test",
            }, path)
            config = load_config(path)
            profiles = ai_model_profiles(config)
            roles = ai_role_assignments(config)
            self.assertEqual(roles["intelligent_search"], "legacy-language")
            self.assertEqual(roles["copilot"], "legacy-language")
            self.assertIn("native_documents", profiles[0]["capabilities"])
            self.assertIn("url_fetch", profiles[0]["capabilities"])

            public = [{key: value for key, value in item.items() if key != "api_key"}
                      for item in profiles]
            set_ai_model_profiles(public, roles, path)
            stored = ai_model_profiles(load_config(path))
            self.assertEqual(stored[0]["api_key"], "secret")

    def test_roles_route_chat_and_embedding_profiles_independently(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yml"
            profiles = [
                {"id": "local", "name": "Local", "provider": "openai_compatible",
                 "base_url": "http://127.0.0.1:8000/v1", "model": "qwen",
                 "capabilities": ["chat"]},
                {"id": "docs", "name": "Docs", "provider": "google",
                 "base_url": "https://google.test/v1", "model": "gemini",
                 "capabilities": ["chat", "documents"],
                 "proxy_mode": "custom", "proxy_url": "http://127.0.0.1:7890"},
                {"id": "embed", "name": "Embed", "provider": "openai_compatible",
                 "base_url": "http://127.0.0.1:9000/v1", "model": "bge",
                 "capabilities": ["embeddings"]},
            ]
            roles = {"intelligent_search": "local", "evidence": "docs", "embedding": "embed"}
            set_ai_model_profiles(profiles, roles, path)
            config = load_config(path)
            config["ai_search_timeout_seconds"] = "30"
            config["ai_stage_timeout_seconds"] = "120"
            save_config(config, path)
            config = load_config(path)
            client = _client_from_config(config, role="evidence")
            self.assertEqual(client.chat_model, "gemini")
            self.assertEqual(client.provider, "google")
            self.assertEqual(client.connection.proxy_mode, "custom")
            self.assertEqual(client.connection.proxy_url, "http://127.0.0.1:7890")
            self.assertEqual(client.timeout, 120)
            self.assertEqual(client.embedding_model, "bge")
            self.assertEqual(ai_profile_for_role(config, "claims")["id"], "local")
            search_client = _client_from_config(config, role="intelligent_search")
            self.assertEqual(search_client.timeout, 30)

    def test_native_document_quote_maps_whitespace_back_to_captured_text(self):
        workspace = {"segments": [{
            "id": "segment-1",
            "text": "Qwen uses grouped-query\nattention for efficient inference.",
        }]}
        mapped = _map_document_quote(
            workspace,
            "Qwen uses grouped-query attention for efficient inference.",
        )
        self.assertEqual(mapped, (
            "segment-1",
            "Qwen uses grouped-query\nattention for efficient inference.",
        ))


if __name__ == "__main__":
    unittest.main()
