import json
import os
from http.client import HTTPConnection
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from knowte import usage
from knowte import search as search_module
from knowte.models import Paper
from knowte.knowledge import (
    create_artifact,
    create_evidence,
    save_source,
    store_capture,
)
from knowte.server import create_server


class SearchApiTests(unittest.TestCase):
    def _request(self, server, method, path, body=None):
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            port = server.server_address[1]
            connection = HTTPConnection("127.0.0.1", port)
            headers = {"Content-Type": "application/json"} if body else {}
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join()

    def test_unconfigured_websearch_is_removed_without_web_usage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            usage_path = temp_path / "usage.json"
            config_path.write_text(
                "enabled_backends: arxiv,websearch\nmax_papers: 20\n",
                encoding="utf-8",
            )

            with patch.object(usage, "USAGE_DIR", temp_path), patch.object(
                usage, "USAGE_PATH", usage_path
            ), patch("knowte.server.search_papers", return_value=[]):
                server = create_server("127.0.0.1", 0, config_path)
                thread = threading.Thread(target=server.serve_forever)
                thread.start()
                try:
                    port = server.server_address[1]
                    connection = HTTPConnection("127.0.0.1", port)
                    connection.request("GET", "/api/search?q=test&limit=20")
                    response = connection.getresponse()
                    payload = json.loads(response.read())
                    connection.close()
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join()

        self.assertEqual(payload["enabled_backends"], ["arxiv"])
        self.assertEqual(payload["warnings"], ["websearch_unconfigured"])
        self.assertEqual(payload["usage"]["last_day"], 1)
        self.assertEqual(payload["usage"]["last_day_web"], 0)

    def test_companion_pair_capture_and_confirm_flow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            server = create_server("127.0.0.1", 0, config_path)
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            port = server.server_address[1]

            def request(method, path, payload=None, token=""):
                connection = HTTPConnection("127.0.0.1", port)
                headers = {}
                body = None
                if payload is not None:
                    headers["Content-Type"] = "application/json"
                    body = json.dumps(payload)
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                connection.request(method, path, body=body, headers=headers)
                response = connection.getresponse()
                data = json.loads(response.read())
                connection.close()
                return response.status, data

            try:
                info_status, info = request("GET", "/api/companion/info")
                _, pairing = request("POST", "/api/companion/pairing")
                pair_status, paired = request(
                    "POST", "/api/companion/pair",
                    {"code": pairing["code"], "nonce": pairing["nonce"]},
                )
                direct_status, direct = request(
                    "POST", "/api/companion/commit",
                    {
                        "kind": "source",
                        "source": {
                            "title": "A page saved for later",
                            "url": "https://example.test/bookmark",
                        },
                        "blocks": [{
                            "type": "paragraph",
                            "text": "A page saved without creating Evidence.",
                        }],
                        "options": {
                            "tags": ["read-later"],
                            "annotation": "Review this Source later.",
                        },
                    },
                    paired["token"],
                )
                capture_status, pending = request(
                    "POST", "/api/companion/captures",
                    {
                        "kind": "text",
                        "source": {
                            "title": "Rendered web article",
                            "url": "https://example.test/rendered",
                        },
                        "quote": "The browser rendered this precise statement.",
                        "blocks": [{
                            "type": "heading", "text": "Rendered article",
                            "metadata": {"level": 1},
                        }, {
                            "type": "paragraph",
                            "text": "The browser rendered this precise statement.",
                        }],
                    },
                    paired["token"],
                )
                confirm_status, confirmed = request(
                    "POST",
                    f"/api/companion/inbox/{pending['id']}/confirm",
                    {},
                )
                _, inbox = request("GET", "/api/companion/inbox")
                _, workspace = request(
                    "GET",
                    f"/api/library/sources/{confirmed['source']['id']}/workspace",
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

        self.assertEqual(info_status, 200)
        manifest_path = Path(info["path"]) / "manifest.json"
        self.assertTrue(manifest_path.is_file())
        self.assertEqual(
            info["version"],
            json.loads(manifest_path.read_text(encoding="utf-8"))["version"],
        )
        self.assertEqual(pair_status, 200)
        self.assertEqual(direct_status, 201)
        self.assertIsNone(direct["evidence"])
        self.assertEqual(capture_status, 201)
        self.assertEqual(confirm_status, 201)
        self.assertEqual(inbox["items"], [])
        self.assertEqual(confirmed["evidence"]["evidence_type"], "text")
        self.assertEqual(workspace["segments"][0]["block_type"], "heading")

    def test_artifact_and_library_api_complete_first_collection_step(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            artifact_server = create_server("127.0.0.1", 0, config_path)
            artifact_status, artifact = self._request(
                artifact_server,
                "POST",
                "/api/artifacts",
                json.dumps(
                    {
                        "title": "Open LLM frontier",
                        "purpose": "Understand current open model technology.",
                    }
                ),
            )
            source_server = create_server("127.0.0.1", 0, config_path)
            source_status, saved = self._request(
                source_server,
                "POST",
                "/api/library/sources",
                json.dumps(
                    {
                        "artifact_id": artifact["id"],
                        "source": {
                            "id": "paper-1",
                            "title": "A frontier model report",
                            "authors": "Researcher",
                            "year": 2026,
                            "abstract": "Model details.",
                            "url": "https://example.test/model",
                            "source": "Web",
                            "result_type": "web",
                        },
                    }
                ),
            )
            library_server = create_server("127.0.0.1", 0, config_path)
            library_status, library = self._request(
                library_server,
                "GET",
                "/api/library/sources",
            )
            list_server = create_server("127.0.0.1", 0, config_path)
            list_status, artifact_list = self._request(
                list_server,
                "GET",
                "/api/artifacts",
            )

        self.assertEqual(artifact_status, 201)
        self.assertEqual(source_status, 201)
        self.assertTrue(saved["source_created"])
        self.assertTrue(saved["artifact_link_created"])
        self.assertEqual(library_status, 200)
        self.assertEqual(len(library["sources"]), 1)
        self.assertEqual(
            library["sources"][0]["artifacts"][0]["id"],
            artifact["id"],
        )
        self.assertEqual(list_status, 200)
        self.assertEqual(artifact_list["artifacts"][0]["source_count"], 1)

    def test_source_workspace_capture_evidence_and_annotation_api(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            source, _, _ = save_source(
                {
                    "title": "Qwen report",
                    "url": "https://example.test/qwen",
                    "source": "Web",
                    "result_type": "web",
                },
                path=Path(temp_dir) / "knowte.db",
            )
            captured_file = Path(temp_dir) / "content" / "capture.html"
            captured_file.parent.mkdir(parents=True)
            captured_file.write_text("<p>Qwen systems.</p>", encoding="utf-8")
            captured = {
                "url": "https://example.test/qwen",
                "media_type": "text/html",
                "sha256": "capture-hash",
                "raw_path": str(captured_file),
                "segments": ["Qwen combines model and systems improvements."],
                "locators": ["Section 1"],
            }
            with patch("knowte.server.capture_source_content", return_value=captured):
                capture_server = create_server("127.0.0.1", 0, config_path)
                capture_status, workspace = self._request(
                    capture_server,
                    "POST",
                    f"/api/library/sources/{source['id']}/capture",
                )
            text = workspace["segments"][0]["text"]
            quote = "systems improvements"
            start = text.index(quote)
            evidence_server = create_server("127.0.0.1", 0, config_path)
            evidence_status, evidence = self._request(
                evidence_server,
                "POST",
                "/api/evidence",
                json.dumps(
                    {
                        "segment_id": workspace["segments"][0]["id"],
                        "quote": quote,
                        "start_offset": start,
                        "end_offset": start + len(quote),
                    }
                ),
            )
            annotation_server = create_server("127.0.0.1", 0, config_path)
            annotation_status, _ = self._request(
                annotation_server,
                "POST",
                "/api/annotations",
                json.dumps(
                    {
                        "target_type": "evidence",
                        "target_id": evidence["id"],
                        "body": "Review this support.",
                    }
                ),
            )
            workspace_server = create_server("127.0.0.1", 0, config_path)
            workspace_status, loaded = self._request(
                workspace_server,
                "GET",
                f"/api/library/sources/{source['id']}/workspace",
            )
            content_server = create_server("127.0.0.1", 0, config_path)
            thread = threading.Thread(target=content_server.serve_forever)
            thread.start()
            try:
                connection = HTTPConnection(
                    "127.0.0.1", content_server.server_address[1]
                )
                connection.request(
                    "GET", f"/api/library/sources/{source['id']}/content"
                )
                content_response = connection.getresponse()
                content_status = content_response.status
                content_type = content_response.getheader("Content-Type")
                content_body = content_response.read()
                connection.close()
            finally:
                content_server.shutdown()
                content_server.server_close()
                thread.join()

        self.assertEqual(capture_status, 201)
        self.assertEqual(evidence_status, 201)
        self.assertEqual(annotation_status, 201)
        self.assertEqual(workspace_status, 200)
        self.assertEqual(content_status, 200)
        self.assertEqual(content_type, "text/html")
        self.assertEqual(content_body, b"<p>Qwen systems.</p>")
        self.assertEqual(loaded["segments"][0]["locator"], "Section 1")
        self.assertEqual(loaded["evidence"][0]["annotations"][0]["body"], "Review this support.")

    def test_batch_collection_adds_sources_and_links_them_to_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            database_path = temp_path / "knowte.db"
            artifact = create_artifact(
                {"title": "Batch target", "purpose": "Review selected Sources."},
                database_path,
            )
            server = create_server(
                "127.0.0.1",
                0,
                config_path,
            )
            status, payload = self._request(
                server,
                "POST",
                "/api/library/sources/batch",
                json.dumps(
                    {
                        "artifact_id": artifact["id"],
                        "sources": [
                            {
                                "id": "source-1",
                                "title": "First Source",
                                "url": "https://example.test/1",
                            },
                            {
                                "id": "source-2",
                                "title": "Second Source",
                                "url": "https://example.test/2",
                            },
                        ],
                    }
                ),
            )

        self.assertEqual(status, 201)
        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["sources_created"], 2)
        self.assertEqual(payload["artifact_links_created"], 2)

    def test_review_chat_returns_advice_without_writing_sources(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            database_path = temp_path / "knowte.db"
            usage_path = temp_path / "usage.json"
            client = MagicMock()
            client.chat_json.return_value = {
                "answer": "Keep the technical report.",
                "recommendations": [
                    {"source_index": 1, "decision": "add", "reason": "Primary source."}
                ],
            }
            client.usage_snapshot.return_value = {
                "chat_requests": 1,
                "chat_tokens": 42,
                "embedding_requests": 0,
                "embedding_tokens": 0,
            }
            with patch("knowte.server._client_from_config", return_value=client), patch.object(
                usage, "USAGE_DIR", temp_path
            ), patch.object(usage, "USAGE_PATH", usage_path):
                server = create_server(
                    "127.0.0.1",
                    0,
                    config_path,
                )
                status, payload = self._request(
                    server,
                    "POST",
                    "/api/review/chat",
                    json.dumps(
                        {
                            "question": "Should this be collected?",
                            "sources": [{"title": "Qwen report", "abstract": "Technical details."}],
                            "evidence": [{
                                "id": "evidence-1",
                                "evidence_type": "text",
                                "source_title": "Qwen report",
                                "locator": "Page 4",
                                "quote": "The model uses grouped-query attention.",
                            }],
                        }
                    ),
                )

        self.assertEqual(status, 200)
        self.assertEqual(payload["answer"], "Keep the technical report.")
        self.assertEqual(payload["recommendations"][0]["decision"], "add")
        self.assertEqual(payload["usage"]["last_day_ai_chat"], 1)
        self.assertIn("selected_evidence", client.chat_json.call_args.args[1])
        self.assertIn("grouped-query attention", client.chat_json.call_args.args[1])
        self.assertIn("local-first system", client.chat_json.call_args.args[0])
        self.assertEqual(client.chat_json.call_args.kwargs["temperature"], 0.2)
        self.assertEqual(client.chat_json.call_args.kwargs["extra_parameters"], {"top_p": 0.9})

    def test_claim_proposal_survives_restart_until_accept(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            database_path = temp_path / "knowte.db"
            usage_path = temp_path / "usage.json"
            source, _, _ = save_source(
                {
                    "title": "Qwen report",
                    "url": "https://example.test/qwen",
                    "source": "Web",
                },
                path=database_path,
            )
            workspace = store_capture(
                source["id"],
                {
                    "url": "https://example.test/qwen",
                    "media_type": "text/html",
                    "sha256": "claim-proposal-source",
                    "raw_path": str(temp_path / "source.html"),
                    "segments": [
                        "Qwen uses grouped-query attention for efficient inference."
                    ],
                    "locators": ["Architecture"],
                },
                database_path,
            )
            evidence = create_evidence(
                {
                    "segment_id": workspace["segments"][0]["id"],
                    "quote": "Qwen uses grouped-query attention",
                    "start_offset": 0,
                    "end_offset": len("Qwen uses grouped-query attention"),
                },
                database_path,
            )
            client = MagicMock()
            client.chat_json.return_value = {
                "claims": [{
                    "statement": "Qwen uses grouped-query attention.",
                    "basis": "reported",
                    "evidence": [{
                        "evidence_id": evidence["id"],
                        "stance": "supports",
                        "rationale": "The report states this directly.",
                    }],
                    "tags": ["Qwen"],
                    "rationale": "Atomic statement grounded in the report.",
                    "caveats": [],
                }],
                "summary": "One grounded Claim proposed.",
            }
            client.usage_snapshot.return_value = {
                "chat_requests": 1,
                "chat_tokens": 64,
                "embedding_requests": 0,
                "embedding_tokens": 0,
            }
            with patch("knowte.server._client_from_config", return_value=client), patch.object(
                usage, "USAGE_DIR", temp_path
            ), patch.object(usage, "USAGE_PATH", usage_path):
                generate_server = create_server("127.0.0.1", 0, config_path)
                generated_status, generated = self._request(
                    generate_server,
                    "POST",
                    "/api/claim-proposals/generate",
                    json.dumps({"evidence_ids": [evidence["id"]]}),
                )

                # A new server instance models a page reload or Knowte restart.
                reload_server = create_server("127.0.0.1", 0, config_path)
                reload_status, reloaded = self._request(
                    reload_server, "GET", "/api/claim-proposals"
                )

                proposal_id = generated["proposals"][0]["id"]
                accept_server = create_server("127.0.0.1", 0, config_path)
                accept_status, accepted = self._request(
                    accept_server,
                    "POST",
                    f"/api/claim-proposals/{proposal_id}/accept",
                    json.dumps({"review_state": "disputed"}),
                )

                final_server = create_server("127.0.0.1", 0, config_path)
                final_status, final = self._request(
                    final_server, "GET", "/api/claim-proposals"
                )

        self.assertEqual(generated_status, 201)
        self.assertEqual(reload_status, 200)
        self.assertEqual(len(reloaded["proposals"]), 1)
        self.assertEqual(reloaded["proposals"][0]["status"], "awaiting_review")
        self.assertEqual(accept_status, 201)
        self.assertEqual(accepted["created_via"], "ai_assisted")
        self.assertEqual(accepted["review_state"], "disputed")
        self.assertEqual(accepted["evidence"][0]["evidence_id"], evidence["id"])
        self.assertEqual(final_status, 200)
        self.assertEqual(final["proposals"], [])

    def test_cached_find_more_does_not_increment_paper_usage(self):
        def papers(prefix, source):
            return [
                Paper(
                    id=f"{prefix}-{index}",
                    title=f"Alpha {prefix} {index}",
                    authors="Author",
                    year=2020,
                    abstract="alpha",
                    url=f"https://example.test/{prefix}/{index}",
                    keywords=[],
                    source=source,
                )
                for index in range(60)
            ]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            usage_path = temp_path / "usage.json"
            config_path.write_text(
                "enabled_backends: arxiv,openalex,semanticscholar\n"
                "max_papers: 60\n",
                encoding="utf-8",
            )
            search_module._ACADEMIC_CACHE.clear()
            with patch.object(usage, "USAGE_DIR", temp_path), patch.object(
                usage, "USAGE_PATH", usage_path
            ), patch(
                "knowte.search.search_arxiv", return_value=papers("a", "arXiv")
            ) as arxiv, patch(
                "knowte.search.search_openalex",
                return_value=papers("o", "OpenAlex"),
            ) as openalex, patch(
                "knowte.search.search_semanticscholar",
                return_value=papers("s", "Semantic Scholar"),
            ) as semanticscholar:
                first_server = create_server("127.0.0.1", 0, config_path)
                first_status, first = self._request(
                    first_server, "GET", "/api/search?q=alpha&limit=60"
                )
                second_server = create_server("127.0.0.1", 0, config_path)
                second_status, second = self._request(
                    second_server, "GET", "/api/search?q=alpha&limit=120"
                )

        self.assertEqual(first_status, 200)
        self.assertEqual(second_status, 200)
        self.assertEqual(first["usage"]["last_day"], 1)
        self.assertEqual(second["usage"]["last_day"], 1)
        self.assertTrue(second["search_diagnostics"]["academic"]["cache_hit"])
        self.assertFalse(
            second["search_diagnostics"]["academic"]["external_request"]
        )
        arxiv.assert_called_once()
        openalex.assert_called_once()
        semanticscholar.assert_called_once()

    def test_new_config_uses_academic_sources_and_one_hundred_as_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            server = create_server("127.0.0.1", 0, config_path)
            status, payload = self._request(server, "GET", "/api/config")

        self.assertEqual(status, 200)
        self.assertEqual(
            payload["enabled_backends"],
            ["arxiv", "openalex", "semanticscholar"],
        )
        self.assertNotIn("websearch", payload["enabled_backends"])
        self.assertEqual(payload["max_papers"], 100)
        self.assertEqual(payload["intelligent_max_results"], 20)
        self.assertEqual(payload["default_search_mode"], "keyword")
        self.assertFalse(payload["ai_enable_thinking"])

    def test_default_search_mode_is_saved_independently(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            server = create_server("127.0.0.1", 0, config_path)
            status, saved = self._request(
                server,
                "POST",
                "/api/config/default-search-mode",
                json.dumps({"mode": "intelligent"}),
            )
            server = create_server("127.0.0.1", 0, config_path)
            get_status, fetched = self._request(server, "GET", "/api/config")
            config_text = config_path.read_text(encoding="utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(saved["default_search_mode"], "intelligent")
        self.assertEqual(get_status, 200)
        self.assertEqual(fetched["default_search_mode"], "intelligent")
        self.assertIn("default_search_mode: intelligent", config_text)

    def test_debug_replay_uses_saved_artifact_sources_without_search_or_ai(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            database_path = temp_path / "knowte.db"
            usage_path = temp_path / "usage.json"
            artifact = create_artifact(
                {
                    "title": "Qwen baseline",
                    "purpose": "Exercise the knowledge pipeline without retrieval.",
                },
                database_path,
            )
            save_source(
                {
                    "id": "https://arxiv.org/abs/2401.00001",
                    "title": "Qwen baseline report",
                    "authors": "Qwen Team",
                    "year": 2024,
                    "source": "arXiv",
                    "result_type": "paper",
                    "paper_url": "https://arxiv.org/abs/2401.00001",
                    "abstract": "A saved and previously verified baseline.",
                    "match_reason": "Previously verified.",
                    "verification_score": 0.95,
                    "discovery_path": "Academic recall → LLM verify",
                },
                artifact["id"],
                database_path,
            )
            save_source(
                {
                    "id": "https://example.test/qwen",
                    "title": "Qwen Web baseline",
                    "source": "Web",
                    "result_type": "web",
                    "url": "https://example.test/qwen",
                    "abstract": "A saved Web source without verification metadata.",
                },
                artifact["id"],
                database_path,
            )
            replay_environment = {
                "KNOWTE_DEBUG_REPLAY_QUERY": "qwen",
                "KNOWTE_DEBUG_REPLAY_ARTIFACT": "Qwen baseline",
            }
            with patch.dict(os.environ, replay_environment), patch.object(
                usage, "USAGE_DIR", temp_path
            ), patch.object(
                usage, "USAGE_PATH", usage_path
            ), patch(
                "knowte.server.search_papers"
            ) as keyword_search, patch(
                "knowte.server.intelligent_search"
            ) as intelligent_pipeline:
                keyword_server = create_server("127.0.0.1", 0, config_path)
                keyword_status, keyword = self._request(
                    keyword_server,
                    "GET",
                    "/api/search?q=qwen&year_from=2026",
                )
                intelligent_server = create_server("127.0.0.1", 0, config_path)
                intelligent_status, intelligent = self._request(
                    intelligent_server,
                    "GET",
                    "/api/intelligent-search?q=qwen&year_from=2026",
                )

        self.assertEqual(keyword_status, 200)
        self.assertEqual(intelligent_status, 200)
        self.assertEqual(keyword["count"], 2)
        self.assertEqual(intelligent["count"], 2)
        self.assertTrue(keyword["debug_replay"]["enabled"])
        self.assertFalse(keyword["debug_replay"]["filters_applied"])
        self.assertEqual(keyword["debug_replay"]["verified_count"], 1)
        self.assertEqual(keyword["debug_replay"]["unverified_count"], 1)
        self.assertEqual(intelligent["candidate_counts"]["verified"], 1)
        self.assertEqual(intelligent["candidate_counts"]["web"], 1)
        self.assertEqual(intelligent["request_budget"]["chat"], 0)
        self.assertEqual(
            intelligent["results"][0]["match_reason"],
            "Previously verified.",
        )
        self.assertIn(
            "Debug replay",
            intelligent["results"][0]["discovery_path"],
        )
        keyword_search.assert_not_called()
        intelligent_pipeline.assert_not_called()

    def test_server_can_restart_immediately_on_same_port(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            first = create_server("127.0.0.1", 0, config_path)
            port = first.server_address[1]
            thread = threading.Thread(target=first.serve_forever)
            thread.start()
            try:
                connection = HTTPConnection("127.0.0.1", port)
                connection.request("GET", "/api/health")
                response = connection.getresponse()
                response.read()
                connection.close()
            finally:
                first.shutdown()
                first.server_close()
                thread.join()

            second = create_server("127.0.0.1", port, config_path)
            second.server_close()

        self.assertEqual(response.status, 200)

    def test_managed_searxng_setup_updates_app_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            config_path.write_text(
                "enabled_backends: arxiv\nmax_papers: 100\n", encoding="utf-8"
            )
            managed_status = {
                "state": "running",
                "installed": True,
                "running": True,
                "healthy": True,
                "managed": True,
                "url": "http://127.0.0.1:8889/search",
                "message": "Local Web Search is running.",
            }
            def start_job(action, on_complete=None):
                on_complete(managed_status)
                return {
                    "job_id": "setup-job",
                    "action": action,
                    "status": "running",
                    "phase": "queued",
                    "output": [],
                }

            with patch(
                "knowte.server.start_searxng_job", side_effect=start_job
            ) as start:
                server = create_server("127.0.0.1", 0, config_path)
                status, payload = self._request(
                    server,
                    "POST",
                    "/api/searxng",
                    json.dumps({"action": "setup"}),
                )

            self.assertEqual(status, 202)
            self.assertEqual(payload["job_id"], "setup-job")
            start.assert_called_once()
            config = config_path.read_text(encoding="utf-8")
            self.assertIn(
                "searxng_url: http://127.0.0.1:8889/search", config
            )
            self.assertIn("enabled_backends: arxiv,websearch", config)

    def test_managed_searxng_remove_forwards_image_cache_choice(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            removed = {
                "state": "not_installed",
                "installed": False,
                "removed_url": "http://127.0.0.1:8888/search",
                "image_cache_requested": True,
                "image_cache_removed": True,
            }
            with patch(
                "knowte.server.manage_searxng", return_value=removed
            ) as manage:
                server = create_server("127.0.0.1", 0, config_path)
                status, payload = self._request(
                    server,
                    "POST",
                    "/api/searxng",
                    json.dumps({"action": "remove", "remove_image": True}),
                )

        self.assertEqual(status, 200)
        self.assertTrue(payload["image_cache_removed"])
        manage.assert_called_once_with("remove", remove_image=True)

    def test_search_reports_source_counts_and_strict_web_year_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            usage_path = temp_path / "usage.json"
            config_path.write_text(
                "enabled_backends: arxiv,websearch\n"
                "searxng_url: http://127.0.0.1:8888/search\n",
                encoding="utf-8",
            )
            results = [
                {"source": "arXiv", "title": "One"},
                {"source": "arXiv", "title": "Two"},
                {"source": "Google", "title": "Three"},
            ]

            with patch.object(usage, "USAGE_DIR", temp_path), patch.object(
                usage, "USAGE_PATH", usage_path
            ), patch("knowte.server.search_papers", return_value=results):
                server = create_server("127.0.0.1", 0, config_path)
                status, payload = self._request(
                    server, "GET", "/api/search?q=alpha&year_from=2015&year_to=2018"
                )

        self.assertEqual(status, 200)
        self.assertEqual(payload["source_counts"], {"arXiv": 2, "Google": 1})
        self.assertIn("websearch_strict_year_filter", payload["warnings"])

    def test_search_reports_unavailable_web_backend(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            usage_path = temp_path / "usage.json"
            config_path.write_text(
                "enabled_backends: websearch\n"
                "searxng_url: http://127.0.0.1:8888/search\n",
                encoding="utf-8",
            )

            def unavailable_search(*args, **kwargs):
                kwargs["diagnostics"]["websearch"] = {
                    "attempted": True,
                    "fetched": 0,
                    "accepted": 0,
                    "error": "unavailable",
                }
                return []

            with patch.object(usage, "USAGE_DIR", temp_path), patch.object(
                usage, "USAGE_PATH", usage_path
            ), patch("knowte.server.search_papers", side_effect=unavailable_search):
                server = create_server("127.0.0.1", 0, config_path)
                status, payload = self._request(server, "GET", "/api/search?q=alpha")

        self.assertEqual(status, 200)
        self.assertIn("websearch_unavailable", payload["warnings"])

    def test_search_passes_web_page_count_and_reports_more_from_actual_page(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            usage_path = temp_path / "usage.json"
            config_path.write_text(
                "enabled_backends: websearch\n"
                "searxng_url: http://127.0.0.1:8888/search\n"
                "web_ignore_year_filter: true\n",
                encoding="utf-8",
            )

            def paged_search(*args, **kwargs):
                kwargs["diagnostics"]["websearch"] = {
                    "attempted": True,
                    "fetched": 13,
                    "accepted": 13,
                    "pages": [
                        {"page": 1, "returned": 7},
                        {"page": 2, "returned": 6},
                    ],
                    "has_more": True,
                }
                return [{"source": "brave", "title": "Alpha"}]

            with patch.object(usage, "USAGE_DIR", temp_path), patch.object(
                usage, "USAGE_PATH", usage_path
            ), patch(
                "knowte.server.search_papers", side_effect=paged_search
            ) as search:
                server = create_server("127.0.0.1", 0, config_path)
                status, payload = self._request(
                    server,
                    "GET",
                    "/api/search?q=alpha&limit=100&web_pages=2",
                )

        self.assertEqual(status, 200)
        self.assertEqual(search.call_args.kwargs["web_pages"], 2)
        self.assertEqual(payload["web_pages"], 2)
        self.assertTrue(payload["can_find_more"])
        self.assertEqual(
            [page["returned"] for page in payload["search_diagnostics"]["websearch"]["pages"]],
            [7, 6],
        )

    def test_empty_query_is_rejected_without_recording_usage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            usage_path = temp_path / "usage.json"
            config_path.write_text("enabled_backends: arxiv\n", encoding="utf-8")

            with patch.object(usage, "USAGE_DIR", temp_path), patch.object(
                usage, "USAGE_PATH", usage_path
            ), patch("knowte.server.search_papers") as search:
                server = create_server("127.0.0.1", 0, config_path)
                status, payload = self._request(server, "GET", "/api/search?q=%20%20")

        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "empty_query")
        self.assertEqual(payload["usage"]["last_day"], 0)
        search.assert_not_called()

    def test_config_does_not_return_api_key_and_blank_update_preserves_it(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            config_path.write_text(
                "semanticscholar_api_key: secret-value\nemail: old@example.com\n",
                encoding="utf-8",
            )

            server = create_server("127.0.0.1", 0, config_path)
            status, payload = self._request(server, "GET", "/api/config")
            self.assertEqual(status, 200)
            self.assertEqual(payload["semanticscholar_api_key"], "")
            self.assertTrue(payload["semanticscholar_api_key_configured"])

            server = create_server("127.0.0.1", 0, config_path)
            status, payload = self._request(
                server,
                "POST",
                "/api/config",
                json.dumps({"email": "new@example.com", "enabled_backends": ["arxiv"]}),
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["semanticscholar_api_key_configured"])
            self.assertIn(
                "semanticscholar_api_key: secret-value",
                config_path.read_text(encoding="utf-8"),
            )

            server = create_server("127.0.0.1", 0, config_path)
            status, payload = self._request(
                server,
                "POST",
                "/api/config",
                json.dumps({"semanticscholar_api_key": ""}),
            )
            self.assertEqual(status, 200)
            self.assertFalse(payload["semanticscholar_api_key_configured"])
            self.assertNotIn(
                "semanticscholar_api_key:", config_path.read_text(encoding="utf-8")
            )

    def test_config_rejects_empty_backend_selection_without_overwriting_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            original = "enabled_backends: arxiv\nmax_papers: 100\n"
            config_path.write_text(original, encoding="utf-8")

            server = create_server("127.0.0.1", 0, config_path)
            status, payload = self._request(
                server,
                "POST",
                "/api/config",
                json.dumps({"enabled_backends": []}),
            )

            self.assertEqual(status, 400)
            self.assertEqual(payload["error"], "no_search_backends")
            self.assertEqual(config_path.read_text(encoding="utf-8"), original)

    def test_config_persists_web_year_filter_exemption(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            server = create_server("127.0.0.1", 0, config_path)
            status, payload = self._request(
                server,
                "POST",
                "/api/config",
                json.dumps(
                    {
                        "enabled_backends": ["websearch"],
                        "searxng_url": "http://127.0.0.1:8888/search",
                        "web_ignore_year_filter": True,
                    }
                ),
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["web_ignore_year_filter"])
            self.assertIn(
                "web_ignore_year_filter: true",
                config_path.read_text(encoding="utf-8"),
            )

    def test_search_request_can_override_configured_sources_for_a_plan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            usage_path = temp_path / "usage.json"
            config_path.write_text(
                "enabled_backends: arxiv,openalex,semanticscholar\nmax_papers: 20\n",
                encoding="utf-8",
            )
            with patch.object(usage, "USAGE_DIR", temp_path), patch.object(
                usage, "USAGE_PATH", usage_path
            ), patch("knowte.server.search_papers", return_value=[]) as search:
                server = create_server("127.0.0.1", 0, config_path)
                status, payload = self._request(
                    server,
                    "GET",
                    "/api/search?q=alpha&limit=20&backends=openalex",
                )

            self.assertEqual(status, 200)
            self.assertEqual(payload["enabled_backends"], ["openalex"])
            self.assertEqual(search.call_args.kwargs["backends"], ["openalex"])

    def test_plan_api_saves_behavior_without_config_secrets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            config_path.write_text(
                "semanticscholar_api_key: secret\n"
                "searxng_url: http://127.0.0.1:8888/search\n",
                encoding="utf-8",
            )
            server = create_server("127.0.0.1", 0, config_path)
            status, created = self._request(
                server,
                "POST",
                "/api/plans",
                json.dumps(
                    {
                        "query": "find conceptual successors to AlphaGo",
                        "mode": "intelligent",
                        "sources": ["openalex", "websearch"],
                        "semanticscholar_api_key": "do-not-copy",
                    }
                ),
            )
            server = create_server("127.0.0.1", 0, config_path)
            list_status, listing = self._request(server, "GET", "/api/plans")

            self.assertEqual(status, 201)
            self.assertEqual(list_status, 200)
            self.assertEqual(listing["plans"][0]["id"], created["id"])
            self.assertNotIn("semanticscholar_api_key", listing["plans"][0])
            self.assertNotIn("searxng_url", listing["plans"][0])

    def test_ai_config_is_write_only_and_supports_separate_embedding_connection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            server = create_server("127.0.0.1", 0, config_path)
            status, saved = self._request(
                server,
                "POST",
                "/api/config",
                json.dumps(
                    {
                        "enabled_backends": ["openalex"],
                        "ai_base_url": "https://chat.test/v1",
                        "ai_api_key": "chat-secret",
                        "ai_chat_model": "chat-model",
                        "ai_embedding_model": "embed-model",
                        "ai_embedding_separate_connection": True,
                        "ai_enable_thinking": False,
                        "ai_embedding_base_url": "http://127.0.0.1:11434/v1",
                        "ai_embedding_api_key": "embed-secret",
                        "intelligent_max_results": 25,
                        "ai_verify_batch_size": 4,
                        "ai_verify_concurrency": 2,
                        "ai_timeout_seconds": 600,
                    }
                ),
            )
            server = create_server("127.0.0.1", 0, config_path)
            get_status, fetched = self._request(server, "GET", "/api/config")

            self.assertEqual(status, 200)
            self.assertEqual(get_status, 200)
            self.assertTrue(saved["ai_configured"])
            self.assertTrue(fetched["ai_api_key_configured"])
            self.assertTrue(fetched["ai_embedding_api_key_configured"])
            self.assertEqual(fetched["ai_api_key"], "")
            self.assertEqual(fetched["ai_embedding_api_key"], "")
            self.assertEqual(fetched["intelligent_max_results"], 25)
            self.assertEqual(fetched["ai_verify_batch_size"], 4)
            self.assertEqual(fetched["ai_verify_concurrency"], 2)
            self.assertEqual(fetched["ai_timeout_seconds"], 600)
            self.assertFalse(fetched["ai_enable_thinking"])
            config_text = config_path.read_text(encoding="utf-8")
            self.assertIn("ai_api_key: chat-secret", config_text)
            self.assertIn("ai_embedding_api_key: embed-secret", config_text)

    def test_intelligent_search_endpoint_reports_and_records_retrieval_rounds(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            usage_path = temp_path / "usage.json"
            config_path.write_text(
                "enabled_backends: openalex,websearch\n"
                "searxng_url: http://127.0.0.1:8888/search\n"
                "ai_base_url: https://ai.test/v1\n"
                "ai_chat_model: chat\n"
                "ai_embedding_model: embed\n",
                encoding="utf-8",
            )
            intelligent_payload = {
                "query": "alpha planning",
                "results": [],
                "count": 0,
                "warnings": [],
                "stages": {},
                "request_budget": {
                    "retrieval": 3,
                    "academic_retrieval": 2,
                    "web_retrieval": 1,
                    "chat": 2,
                    "embedding": 1,
                },
                "_ai_usage": {
                    "chat_requests": 2,
                    "chat_tokens": 150,
                    "embedding_requests": 1,
                    "embedding_tokens": 80,
                },
            }
            with patch.object(usage, "USAGE_DIR", temp_path), patch.object(
                usage, "USAGE_PATH", usage_path
            ), patch(
                "knowte.server.intelligent_search",
                return_value=intelligent_payload,
            ) as search:
                server = create_server("127.0.0.1", 0, config_path)
                status, payload = self._request(
                    server,
                    "GET",
                    "/api/intelligent-search?q=alpha%20planning"
                    "&areas=ai.rl&year_from=2015&limit=100"
                    "&backends=openalex,websearch",
                )

            self.assertEqual(status, 200)
            self.assertEqual(payload["usage"]["last_day"], 2)
            self.assertEqual(payload["usage"]["last_day_web"], 1)
            self.assertEqual(payload["usage"]["last_day_ai_chat"], 2)
            self.assertEqual(payload["usage"]["last_day_ai_chat_tokens"], 150)
            self.assertEqual(payload["usage"]["last_day_ai_embedding"], 1)
            self.assertEqual(payload["usage"]["last_day_ai_embedding_tokens"], 80)
            self.assertEqual(search.call_args.args[4], ["ai.rl"])
            self.assertEqual(search.call_args.args[5], 2015)


if __name__ == "__main__":
    unittest.main()
