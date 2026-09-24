import json
import os
import socket
from contextlib import ExitStack
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
    accept_wiki_proposal,
    create_artifact,
    create_claim,
    create_evidence,
    create_wiki_proposal,
    link_project_knowledge,
    save_source,
    store_capture,
)
from knowte.server import KnowteTCPServer, _import_candidates, create_server


class SearchApiTests(unittest.TestCase):
    def test_new_claim_relations_resolve_from_one_model_call(self):
        from knowte.knowledge import accept_claim_proposal, list_claim_proposals
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "knowte.db"
            source, _, _ = save_source({"title": "RL", "url": "https://example.test/rl"}, path=db)
            workspace = store_capture(source["id"], {"url": source["url"], "media_type": "text/html",
                "sha256": "relations", "raw_path": str(root / "page.html"),
                "segments": ["RL policies select actions and thereby affect returns."]}, db)
            segment = workspace["segments"][0]
            evidence = create_evidence({"segment_id": segment["id"], "quote": segment["text"],
                "start_offset": 0, "end_offset": len(segment["text"])}, db)
            old = create_claim({"statement": "RL policies affect returns", "basis": "reported",
                "evidence": [{"evidence_id": evidence["id"], "stance": "supports"}]}, db)
            client = MagicMock()
            client.chat_json.return_value = {"claims": [
                {"temp_id": "new:1", "statement": "Policies select actions", "basis": "reported",
                 "evidence": [{"evidence_id": evidence["id"], "stance": "supports"}]},
                {"temp_id": "new:2", "statement": "Actions affect returns", "basis": "reported",
                 "evidence": [{"evidence_id": evidence["id"], "stance": "supports"}]},
            ], "claim_relations": [
                {"subject_claim_id": "new:1", "object_claim_id": "new:2", "relation_type": "related", "rationale": "Action mechanism"},
                {"subject_claim_id": "new:2", "object_claim_id": old["id"], "relation_type": "supports", "rationale": "Effect on return"},
                {"subject_claim_id": "invented", "object_claim_id": "new:1", "relation_type": "supports"},
            ]}
            client.usage_snapshot.return_value = {"chat_requests": 1, "chat_tokens": 100}
            with patch("knowte.server._client_from_config", return_value=client), patch.object(usage, "USAGE_DIR", root), patch.object(usage, "USAGE_PATH", root / "usage.json"):
                status, body = self._request(create_server("127.0.0.1", 0, root / "config.yml"), "POST",
                    "/api/claim-proposals/generate", json.dumps({"evidence_ids": [evidence["id"]]}))
            self.assertEqual(status, 201, body)
            self.assertEqual(client.chat_json.call_count, 1)
            self.assertEqual(len(body["proposals"]), 4)
            for proposal in body["proposals"][:2]:
                accept_claim_proposal(proposal["id"], path=db)
            for proposal in list_claim_proposals(db):
                self.assertFalse(proposal["payload"]["subject_claim_id"].startswith("proposal:"))
                accept_claim_proposal(proposal["id"], path=db)

    def test_audit_discovers_support_and_reviews_existing_relation(self):
        from knowte.knowledge import create_claim_relation, create_claim_audit, accept_claim_proposal, get_claim
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "knowte.db"
            a = create_claim({"statement": "Policy selects actions", "basis": "background", "intentionally_ungrounded": True, "tags": ["RL"]}, db)
            b = create_claim({"statement": "Behavior determines return", "basis": "background", "intentionally_ungrounded": True, "tags": ["RL"]}, db)
            client = MagicMock()
            assessment = {"left_claim_id": a["id"], "right_claim_id": b["id"],
                "judgment": "supports", "subject_claim_id": b["id"], "object_claim_id": a["id"], "rationale": "Directional reason"}
            client.chat_json.return_value = {"assessments": [assessment]}
            client.usage_snapshot.return_value = {"chat_requests": 1, "chat_tokens": 100}
            with patch("knowte.server._client_from_config", return_value=client), patch.object(usage, "USAGE_DIR", root), patch.object(usage, "USAGE_PATH", root / "usage.json"):
                audit = create_claim_audit(path=db)
                status, body = self._request(create_server("127.0.0.1", 0, root / "config.yml"), "POST", f"/api/claim-audits/{audit['id']}/run", "{}")
                self.assertEqual(status, 200, body)
                proposal = body["proposals"][0]
                self.assertEqual(proposal["payload"]["subject_claim_id"], b["id"])
                accept_claim_proposal(proposal["id"], path=db)
                old = get_claim(a["id"], db)["relations"][0]
                assessment.update({"judgment": "distinct", "relation_reviews": [{**old, "action": "remove", "rationale": "Not justified"}]})
                audit = create_claim_audit(path=db)
                status, body = self._request(create_server("127.0.0.1", 0, root / "config.yml"), "POST", f"/api/claim-audits/{audit['id']}/run", "{}")
                self.assertEqual(status, 200, body)
                sent = json.loads(client.chat_json.call_args.args[1])
                self.assertEqual(len(sent["pairs"][0]["existing_relations"]), 1)
                self.assertEqual(body["proposals"][0]["payload"]["operation"], "revise_relation")
                self.assertEqual(len(get_claim(a["id"], db)["relations"]), 1)
                accept_claim_proposal(body["proposals"][0]["id"], path=db)
                self.assertEqual(get_claim(a["id"], db)["relations"], [])

    def test_wiki_reset_requires_confirmation_and_returns_unorganized_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.yml"
            database = config.with_name("knowte.db")
            claim = create_claim({"statement": "Keep this Claim", "basis": "background",
                                  "intentionally_ungrounded": True}, database)
            draft = create_wiki_proposal({"pages": [{"key": "root", "title": "Root",
                                                    "claim_ids": [claim["id"]]}]}, "test", path=database)
            accept_wiki_proposal(draft["id"], database)
            status, _ = self._request(create_server("127.0.0.1", 0, config), "POST", "/api/wiki/reset", "{}")
            self.assertEqual(status, 400)
            from knowte.knowledge import get_wiki
            self.assertEqual(len(get_wiki(database)["pages"]), 1)
            status, result = self._request(create_server("127.0.0.1", 0, config), "POST", "/api/wiki/reset", '{"confirmed":true}')
            self.assertEqual(status, 200)
            self.assertEqual(result["pages"], [])
            self.assertEqual(result["unorganized_claim_ids"], [claim["id"]])

    def test_startup_connection_burst_fits_listen_queue(self):
        # Deliberately do not accept yet: startup connections must fit in the
        # kernel queue, not depend on the serving thread winning a race.
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            server = create_server("127.0.0.1", 0, Path(directory) / "config.yml")
            stack.callback(server.server_close)
            for _ in range(20):
                stack.enter_context(socket.create_connection(server.server_address, timeout=1))

    def test_article_claim_limit_is_one_hundred(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            claims = [{"id": f"claim-{i}", "statement": f"Fact {i}", "lifecycle": "active"} for i in range(100)]
            project = {"title": "Test", "purpose": "Test", "claims": claims}
            client = MagicMock()
            client.usage_snapshot.return_value = {}
            client.chat_json.side_effect = [
                {"claim_ids": [claim["id"] for claim in claims]},
                {"title": "Test", "introduction": "Test", "sections": [{"heading": "Test", "paragraphs": [{"text": "Fact", "claim_ids": [claims[-1]["id"]]}]}]},
            ]
            with patch("knowte.server.get_project", return_value=project), patch("knowte.server._client_from_config", return_value=client):
                status, response = self._request(create_server("127.0.0.1", 0, config_path), "POST", "/api/project-articles/generate", json.dumps({"project_id": "test", "goal": "Test"}))
                self.assertEqual(status, 200, response)
                self.assertEqual(len(json.loads(client.chat_json.call_args_list[1].args[1])["claims"]), 100)
                claims.append({"id": "extra", "statement": "Extra", "lifecycle": "active"})
                client.reset_mock()
                status, response = self._request(create_server("127.0.0.1", 0, config_path), "POST", "/api/project-articles/generate", json.dumps({"project_id": "test", "goal": "Test"}))
                self.assertEqual(status, 400, response)
                client.chat_json.assert_not_called()

    def test_wiki_model_receives_only_configured_batch(self):
        from knowte.knowledge import get_wiki, prepare_wiki_batch
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            config_path.write_text("ai_wiki_claim_limit: 1\n", encoding="utf-8")
            database = Path(directory) / "knowte.db"
            for i in range(3):
                create_claim({"statement": f"Fact {i}", "basis": "background", "intentionally_ungrounded": True}, database)
            selected, _ = prepare_wiki_batch(get_wiki(database), 1)
            client = MagicMock()
            client.chat_json.return_value = {"pages": [{"key": "new", "title": "First batch", "claim_ids": [selected[0]["id"]]}]}
            client.usage_snapshot.return_value = {}
            with patch("knowte.server._client_from_config", return_value=client), patch("knowte.server._model_name_from_config", return_value="test"):
                status, response = self._request(create_server("127.0.0.1", 0, config_path), "POST", "/api/wiki/proposals/generate", "{}")
            self.assertEqual(status, 201, response)
            sent = json.loads(client.chat_json.call_args.args[1])
            self.assertEqual(len(sent["claims"]), 1)
            self.assertTrue(sent["batch_mode"])
            accepted = accept_wiki_proposal(response["proposal"]["id"], database)
            self.assertEqual(len(accepted["unorganized_claim_ids"]), 2)
            page_id = accepted["pages"][0]["id"]
            original_id = selected[0]["id"]
            next_batch, _ = prepare_wiki_batch(accepted, 1)
            client.reset_mock()
            client.chat_json.side_effect = [
                {"page_ids": [page_id]},
                {"pages": [{"key": page_id, "title": "First batch", "summary": "Combined context",
                            "claim_ids": [next_batch[0]["id"]]}]},
            ]
            with patch("knowte.server._client_from_config", return_value=client), patch("knowte.server._model_name_from_config", return_value="test"):
                status, response = self._request(create_server("127.0.0.1", 0, config_path), "POST", "/api/wiki/proposals/generate", "{}")
            self.assertEqual(status, 201, response)
            self.assertEqual(client.chat_json.call_count, 2)
            selection_input = json.loads(client.chat_json.call_args_list[0].args[1])
            self.assertNotIn("claim_ids", selection_input["directory"][0])
            self.assertEqual(len(selection_input["claims"]), 1)
            organization_input = json.loads(client.chat_json.call_args_list[1].args[1])
            self.assertEqual(organization_input["reference_pages"][0]["claims"][0]["id"], original_id)
            self.assertEqual(len(organization_input["claims"]), 1)
            accepted = accept_wiki_proposal(response["proposal"]["id"], database)
            self.assertIn(original_id, accepted["pages"][0]["claim_ids"])
            self.assertEqual(len(accepted["unorganized_claim_ids"]), 1)
            client.reset_mock()
            client.chat_json.side_effect = [{"page_ids": ["invented-page"]}]
            with patch("knowte.server._client_from_config", return_value=client):
                status, response = self._request(create_server("127.0.0.1", 0, config_path), "POST", "/api/wiki/proposals/generate", "{}")
            self.assertEqual(status, 400, response)
            self.assertEqual(client.chat_json.call_count, 1)

    def test_batch_deletion_preview_and_confirmation_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            database = Path(directory) / "knowte.db"
            source = save_source({"title": "Temporary", "url": "https://example.org/delete"}, path=database)[0]
            payload = {"entity_type": "source", "entity_ids": [source["id"]]}
            status, plan = self._request(create_server("127.0.0.1", 0, config_path), "POST", "/api/knowledge/delete-preview", json.dumps(payload))
            self.assertEqual(status, 200, plan)
            self.assertEqual(plan["sources"], 1)
            status, result = self._request(create_server("127.0.0.1", 0, config_path), "POST", "/api/knowledge/delete", json.dumps({**payload, "token": plan["token"]}))
            self.assertEqual(status, 200, result)

    def test_configured_selection_limits_reject_instead_of_truncating(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            config_path.write_text("ai_evidence_source_limit: 2\nai_claim_evidence_limit: 3\nai_copilot_context_limit: 2\n", encoding="utf-8")
            cases = [
                ("/api/evidence-proposals/generate", {"source_ids": ["a", "b", "c"], "focus": "test"}),
                ("/api/claim-proposals/generate", {"evidence_ids": ["a", "b", "c", "d"]}),
                ("/api/review/chat", {"question": "test", "sources": [{}], "evidence": [{}], "claims": [{}]}),
            ]
            for route, payload in cases:
                server = create_server("127.0.0.1", 0, config_path)
                status, result = self._request(server, "POST", route, json.dumps(payload))
                self.assertEqual(status, 400, result)
                self.assertIn("message", result)

    def setUp(self):
        self.image_directory = patch("knowte.server.discover_source_images", return_value=[]).start()
        self.addCleanup(patch.stopall)

    def test_web_image_candidates_preserve_caption_and_reject_invented_url(self):
        import base64
        import io
        from PIL import Image
        raw = io.BytesIO()
        Image.new("RGB", (2, 2)).save(raw, "PNG")
        png = "data:image/png;base64," + base64.b64encode(raw.getvalue()).decode()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server = create_server("127.0.0.1", 0, root / "config.yml")
            source = save_source({"title": "Intro", "url": "https://example.org/intro", "result_type": "web"}, path=root / "knowte.db")[0]
            self.image_directory.return_value = [{"image_url": "https://example.org/figure.jpg", "caption": "Original caption", "alt": "Diagram", "title": ""}]
            client = MagicMock()
            client.usage_snapshot.return_value = {}
            client.grounded_json.return_value = {"evidence": [
                {"source_id": source["id"], "evidence_type": "snapshot", "image_url": url, "quote": "Invented caption"}
                for url in ["https://example.org/figure.jpg", "https://example.org/fake.png"]]}
            with patch("knowte.server.load_config", return_value={}), patch("knowte.server.ai_model_profiles", return_value=[]), patch("knowte.server.ai_profile_for_role", return_value={"capabilities": ["url_fetch"]}), patch("knowte.server._client_from_config", return_value=client), patch("knowte.server._model_name_from_config", return_value="dummy"), patch("knowte.server.record_ai_usage", return_value={}), patch("knowte.server.capture_evidence_image", return_value=png) as download:
                status, result = self._request(server, "POST", "/api/evidence-proposals/generate", json.dumps({"source_ids": [source["id"]], "focus": "concepts"}))
            self.assertEqual(status, 201)
            self.assertEqual(len(result["proposals"]), 1, result)
            self.assertEqual(result["proposals"][0]["payload"]["quote"], "Original caption")
            self.assertEqual(download.call_count, 1)
            self.assertIn("not in this page", " ".join(result["warnings"]))
            manifest = json.loads(client.grounded_json.call_args.args[1])
            self.assertEqual(manifest["sources"][0]["images"][0]["caption"], "Original caption")

    def test_related_pages_call_counts_and_deferred_sources(self):
        from knowte.knowledge import list_sources
        for mode, extraction_calls in [("combined", 1), ("individual", 2)]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                server = create_server("127.0.0.1", 0, root / "config.yml")
                source = save_source({"title": "Intro", "url": "https://example.org/intro", "result_type": "web"}, path=root / "knowte.db")[0]
                pages = [{"id": str(n), "title": f"Chapter {n}", "url": f"https://example.org/{n}", "parent_source_id": source["id"]} for n in range(2)]
                client = MagicMock()
                client.usage_snapshot.return_value = {}
                client.chat_json.return_value = {"page_ids": ["0", "1"], "summary": "Both relevant"}
                def extraction(prompt, request, **kwargs):
                    items = json.loads(request)["sources"]
                    self.assertTrue(all(not item["segments"] for item in items))
                    return {"evidence": [{"source_id": item["source_id"], "quote": "Original passage"} for item in items]}
                client.grounded_json.side_effect = extraction
                with patch("knowte.server.load_config", return_value={"ai_evidence_request_mode": mode}), patch("knowte.server.ai_model_profiles", return_value=[]), patch("knowte.server.ai_profile_for_role", return_value={"capabilities": ["url_fetch"]}), patch("knowte.server._client_from_config", return_value=client), patch("knowte.server._model_name_from_config", return_value="dummy"), patch("knowte.server.discover_pages", return_value=(pages, [])), patch("knowte.server.record_ai_usage", return_value={}):
                    status, selected = self._request(server, "POST", "/api/evidence-pages/select", json.dumps({"source_ids": [source["id"]], "focus": "learn"}))
                    self.assertEqual(status, 200)
                    server = create_server("127.0.0.1", 0, root / "config.yml")
                    status, result = self._request(server, "POST", "/api/evidence-proposals/generate", json.dumps({"source_ids": [source["id"]], "focus": "learn", "related_pages": selected["pages"], "related_request_mode": selected["request_mode"]}))
                self.assertEqual(status, 201)
                self.assertEqual(len(result["proposals"]), 2, result)
                self.assertEqual(client.chat_json.call_count, 1)
                self.assertEqual(client.grounded_json.call_count, extraction_calls)
                self.assertEqual(len(list_sources(root / "knowte.db")), 1)

    def test_evidence_request_mode_config_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            server = create_server("127.0.0.1", 0, Path(directory) / "config.yml")
            status, data = self._request(server, "GET", "/api/config")
            self.assertEqual(data["ai_evidence_request_mode"], "combined")
            server = create_server("127.0.0.1", 0, Path(directory) / "config.yml")
            status, data = self._request(server, "POST", "/api/config", json.dumps({"ai_evidence_request_mode": "individual"}))
            self.assertEqual(status, 200)
            self.assertEqual(data["ai_evidence_request_mode"], "individual")
            server = create_server("127.0.0.1", 0, Path(directory) / "config.yml")
            status, data = self._request(server, "GET", "/api/config")
            self.assertEqual(data["ai_evidence_request_mode"], "individual")

    def test_evidence_url_requests_and_partial_failures(self):
        from knowte.ai import AIError
        for mode, expected_calls in [("combined", 1), ("individual", 2)]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                server = create_server("127.0.0.1", 0, root / "config.yml")
                sources = [save_source({"title": f"Web {n}", "url": f"https://example.org/{n}"}, path=root / "knowte.db")[0] for n in range(2)]
                client = MagicMock()
                client.usage_snapshot.return_value = {}
                def result(prompt, request, **kwargs):
                    items = json.loads(request)["sources"]
                    self.assertTrue(all(not item["segments"] for item in items))
                    if mode == "individual" and items[0]["source_id"] == sources[1]["id"]:
                        raise AIError("timeout", "Timed out")
                    return {"evidence": [{"source_id": items[0]["source_id"], "quote": "An exact externally read passage.", "locator": "Section 1"}]}
                client.grounded_json.side_effect = result
                with patch("knowte.server.load_config", return_value={"ai_evidence_request_mode": mode}), patch("knowte.server.ai_model_profiles", return_value=[]), patch("knowte.server.ai_profile_for_role", return_value={"capabilities": ["url_fetch"]}), patch("knowte.server._client_from_config", return_value=client), patch("knowte.server._model_name_from_config", return_value="test"), patch("knowte.server.capture_source_content") as capture, patch("knowte.server.record_ai_usage", return_value={}):
                    status, data = self._request(server, "POST", "/api/evidence-proposals/generate", json.dumps({"source_ids": [s["id"] for s in sources], "focus": "learn"}))
                self.assertEqual(status, 201)
                self.assertEqual(client.grounded_json.call_count, expected_calls)
                client.chat_json.assert_not_called()
                capture.assert_not_called()
                self.assertEqual(len(data["proposals"]), 1)
                self.assertEqual(data["proposals"][0]["payload"]["verification"], "external_unverified")
                if mode == "individual":
                    self.assertIn("Timed out", " ".join(data["warnings"]))

    def test_discovery_empty_focus_and_retrieval_outcomes(self):
        seed = {"id": "seed", "title": "Seed", "url": "https://arxiv.org/abs/2309.16609"}
        for success, candidates, expected_status, reason in [
            (0, [], 502, None),
            (3, [], 200, "no_candidates"),
            (3, [seed], 200, "already_saved"),
        ]:
            with self.subTest(success=success, reason=reason), tempfile.TemporaryDirectory() as directory:
                server = create_server("127.0.0.1", 0, Path(directory) / "config.yml")
                with patch("knowte.server.list_sources", return_value=[seed]), \
                     patch("knowte.server.can_request", return_value={"allowed_paper": True}), \
                     patch("knowte.server.get_usage", return_value={}), \
                     patch("knowte.server.record_request", return_value={}) as record, \
                     patch("knowte.server._client_from_config") as client, \
                     patch("knowte.server.discover_related_papers", return_value={
                         "candidates": candidates, "requests": 3,
                         "successful_requests": success,
                         "retrieval_failures": [] if success else [{"code": "rate_limited", "status": 429}],
                     }):
                    status, payload = self._request(server, "POST", "/api/source-discovery",
                                                    json.dumps({"source_ids": ["seed"], "focus": ""}))
                self.assertEqual(status, expected_status)
                self.assertEqual(record.call_count, 3)
                client.assert_not_called()
                if reason:
                    self.assertEqual(payload["empty_reason"], reason)
                else:
                    self.assertEqual(payload["error"], "discovery_retrieval_failed")
                    self.assertIn("429", payload["message"])

    def test_client_disconnect_does_not_print_a_server_traceback(self):
        server = object.__new__(KnowteTCPServer)
        with patch("socketserver.ThreadingTCPServer.handle_error") as parent:
            try:
                raise ConnectionAbortedError("browser closed the local request")
            except ConnectionAbortedError:
                server.handle_error(None, ("127.0.0.1", 12345))
        parent.assert_not_called()

    def test_wiki_organization_reads_global_reviewed_claims(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            server = create_server("127.0.0.1", 0, config_path)
            status, payload = self._request(
                server,
                "POST",
                "/api/wiki/proposals/generate",
                json.dumps({}),
            )

        self.assertEqual(status, 400)
        self.assertEqual(
            payload["message"],
            "The Wiki needs at least one reviewed active Claim to organize",
        )

    def test_article_generation_selects_from_the_project_claims(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            database_path = temp_path / "knowte.db"
            usage_path = temp_path / "usage.json"
            first = create_claim(
                {"statement": "Qwen uses grouped-query attention.", "basis": "background", "intentionally_ungrounded": True},
                database_path,
            )
            second = create_claim(
                {"statement": "Qwen uses RMSNorm.", "basis": "background", "intentionally_ungrounded": True},
                database_path,
            )
            project = create_artifact({
                "title": "Qwen architecture",
                "purpose": "Explain how Qwen architecture evolved.",
            }, database_path)
            link_project_knowledge(project["id"], "claim", first["id"], database_path)
            link_project_knowledge(project["id"], "claim", second["id"], database_path)
            client = MagicMock()
            article_result = {
                "title": "Qwen architecture",
                "introduction": "A focused explanation.",
                "sections": [{"heading": "Design", "paragraphs": [{
                    "text": "Qwen combines two architectural choices.",
                    "claim_ids": [first["id"], second["id"]],
                }]}],
                "gaps": [],
            }
            client.chat_json.side_effect = [
                {
                    "claim_ids": [first["id"], second["id"]],
                    "outline": [{
                        "heading": "Design",
                        "claim_ids": [first["id"], second["id"]],
                    }],
                    "rationale": "Both Claims address the requested architecture.",
                },
                article_result,
            ]
            client.usage_snapshot.return_value = {
                "chat_requests": 1, "chat_tokens": 64,
                "embedding_requests": 0, "embedding_tokens": 0,
            }
            with patch("knowte.server._client_from_config", return_value=client), patch.object(
                usage, "USAGE_DIR", temp_path
            ), patch.object(usage, "USAGE_PATH", usage_path):
                server = create_server("127.0.0.1", 0, config_path)
                status, payload = self._request(
                    server, "POST", "/api/project-articles/generate",
                    json.dumps({
                        "goal": "Explain Qwen architecture.",
                        "project_id": project["id"],
                    }),
                )

        self.assertEqual(status, 200)
        self.assertEqual(payload["article"]["capability_version"], "wiki-article-v1")
        selection_input = client.chat_json.call_args_list[0].args[1]
        article_input = client.chat_json.call_args_list[1].args[1]
        self.assertIn(project["title"], selection_input)
        self.assertIn(project["purpose"], selection_input)
        self.assertIn(first["statement"], selection_input)
        self.assertIn(second["statement"], selection_input)
        self.assertIn(first["id"], article_input)
        self.assertIn(second["id"], article_input)

    def test_import_parser_accepts_human_links_and_structured_llm_output(self):
        urls = _import_candidates("https://arxiv.org/abs/1706.03762\nhttps://arxiv.org/pdf/1706.03762.pdf\nhttps://doi.org/10.1000/example")
        self.assertEqual(len(urls), 2)
        self.assertEqual(urls[0]["result_type"], "paper")
        self.assertEqual(urls[0]["title"], "arXiv 1706.03762")
        self.assertEqual(urls[0]["pdf_url"], "https://arxiv.org/pdf/1706.03762")
        self.assertEqual(urls[1]["doi_url"], "https://doi.org/10.1000/example")
        human = _import_candidates(
            "https://example.test/article\narXiv: 2412.15115\ndoi: 10.1000/example"
        )
        self.assertEqual(len(human), 3)
        self.assertTrue(all(item["import_status"] == "partial" for item in human))
        structured = _import_candidates(json.dumps({"sources": [{
            "title": "Qwen2.5 Technical Report",
            "source_type": "report",
            "url": "https://arxiv.org/abs/2412.15115",
            "year": 2024,
            "why_relevant": "Primary report.",
        }]}))
        self.assertEqual(structured[0]["title"], "Qwen2.5 Technical Report")
        self.assertEqual(structured[0]["match_reason"], "Primary report.")
        self.assertNotEqual(structured[0]["abstract"], "Primary report.")

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

    def test_legacy_websearch_setting_is_ignored_without_web_usage(self):
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
        self.assertEqual(payload["warnings"], [])
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
        self.assertEqual(artifact_list["artifacts"][0]["source_count"], 0)

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
                            "context": "library",
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
        self.assertIn("local-first knowledge workspace", client.chat_json.call_args.args[0])
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
                    json.dumps({
                        "evidence_ids": [evidence["id"]],
                        "focus": "Qwen inference architecture",
                    }),
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
        proposal_input = json.loads(client.chat_json.call_args.args[1])
        self.assertEqual(proposal_input["focus"], "Qwen inference architecture")
        self.assertIn("existing_claims", proposal_input)
        self.assertEqual(generated["comparison_claim_count"], 0)
        self.assertEqual(reload_status, 200)
        self.assertEqual(len(reloaded["proposals"]), 1)
        self.assertEqual(reloaded["proposals"][0]["status"], "awaiting_review")
        self.assertEqual(accept_status, 201)
        self.assertEqual(accepted["created_via"], "ai_assisted")
        self.assertEqual(accepted["review_state"], "disputed")
        self.assertEqual(accepted["evidence"][0]["evidence_id"], evidence["id"])
        self.assertEqual(final_status, 200)
        self.assertEqual(final["proposals"], [])

    def test_claim_proposal_can_attach_new_evidence_to_related_existing_claim(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            database_path = temp_path / "knowte.db"
            usage_path = temp_path / "usage.json"
            source, _, _ = save_source({
                "title": "Qwen evaluation", "url": "https://example.test/qwen-eval",
            }, path=database_path)
            workspace = store_capture(source["id"], {
                "url": source["url"], "media_type": "text/html",
                "sha256": "claim-update-source",
                "raw_path": str(temp_path / "source.html"),
                "segments": [
                    "Qwen uses grouped-query attention.",
                    "The evaluation confirms Qwen grouped-query attention.",
                ],
            }, database_path)
            evidence = [create_evidence({
                "segment_id": segment["id"], "quote": segment["text"],
                "start_offset": 0, "end_offset": len(segment["text"]),
            }, database_path) for segment in workspace["segments"]]
            existing = create_claim({
                "statement": "Qwen uses grouped-query attention.",
                "basis": "reported",
                "evidence": [{"evidence_id": evidence[0]["id"], "stance": "supports"}],
                "tags": ["Qwen"],
            }, database_path)
            client = MagicMock()
            client.chat_json.return_value = {
                "summary": "The selected Evidence reinforces an existing Claim.",
                "claims": [],
                "existing_claim_updates": [{
                    "claim_id": existing["id"],
                    "evidence": [{
                        "evidence_id": evidence[1]["id"], "stance": "supports",
                        "rationale": "The evaluation confirms the mechanism.",
                    }],
                    "rationale": "Avoid a duplicate Claim.", "caveats": [],
                }],
                "claim_relations": [], "skipped": [],
            }
            client.usage_snapshot.return_value = {
                "chat_requests": 1, "chat_tokens": 80,
                "embedding_requests": 0, "embedding_tokens": 0,
            }
            with patch("knowte.server._client_from_config", return_value=client), patch.object(
                usage, "USAGE_DIR", temp_path
            ), patch.object(usage, "USAGE_PATH", usage_path):
                generate_server = create_server("127.0.0.1", 0, config_path)
                status, generated = self._request(
                    generate_server, "POST", "/api/claim-proposals/generate",
                    json.dumps({"evidence_ids": [evidence[1]["id"]]}),
                )
                proposal = generated["proposals"][0]
                accept_server = create_server("127.0.0.1", 0, config_path)
                accept_status, accepted = self._request(
                    accept_server, "POST",
                    f"/api/claim-proposals/{proposal['id']}/accept", "{}",
                )

        self.assertEqual(status, 201)
        self.assertEqual(proposal["payload"]["operation"], "link_evidence")
        self.assertEqual(generated["comparison_claim_count"], 1)
        self.assertEqual(generated["comparison_scope"]["limit"], 100)
        self.assertEqual(generated["comparison_scope"]["covered_evidence_count"], 1)
        self.assertFalse(generated["comparison_scope"]["truncated"])
        self.assertEqual(client.chat_json.call_count, 1)
        self.assertEqual(accept_status, 201)
        self.assertEqual(accepted["id"], existing["id"])
        self.assertEqual(len(accepted["evidence"]), 2)

    def test_claim_audit_previews_scope_and_persists_review_proposals(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            database_path = temp_path / "knowte.db"
            usage_path = temp_path / "usage.json"
            first = create_claim({
                "statement": "Qwen uses grouped-query attention.",
                "basis": "background", "intentionally_ungrounded": True,
                "tags": ["Qwen"],
            }, database_path)
            second = create_claim({
                "statement": "Qwen models use grouped query attention.",
                "basis": "background", "intentionally_ungrounded": True,
                "tags": ["Qwen"],
            }, database_path)
            client = MagicMock()
            client.chat_json.return_value = {"assessments": [{
                "left_claim_id": first["id"],
                "right_claim_id": second["id"],
                "judgment": "same",
                "target_claim_id": first["id"],
                "source_claim_id": second["id"],
                "merged_statement": "Qwen models use grouped-query attention.",
                "rationale": "The statements express the same proposition.",
                "caveats": [],
            }]}
            client.usage_snapshot.return_value = {
                "chat_requests": 1, "chat_tokens": 90,
                "embedding_requests": 0, "embedding_tokens": 0,
            }
            with patch("knowte.server._client_from_config", return_value=client), patch.object(
                usage, "USAGE_DIR", temp_path
            ), patch.object(usage, "USAGE_PATH", usage_path):
                preview_server = create_server("127.0.0.1", 0, config_path)
                preview_status, preview = self._request(
                    preview_server, "POST", "/api/claim-audits/preview",
                    json.dumps({"scope": {"all_tags": ["Qwen"]}}),
                )
                create_audit_server = create_server("127.0.0.1", 0, config_path)
                create_status, audit = self._request(
                    create_audit_server, "POST", "/api/claim-audits",
                    json.dumps({
                        "scope": {"all_tags": ["Qwen"]},
                        "model_profile_id": "claims-model",
                    }),
                )
                run_server = create_server("127.0.0.1", 0, config_path)
                run_status, run = self._request(
                    run_server, "POST", f"/api/claim-audits/{audit['id']}/run", "{}",
                )
                queue_server = create_server("127.0.0.1", 0, config_path)
                queue_status, queue = self._request(
                    queue_server, "GET", "/api/claim-proposals",
                )

        self.assertEqual(preview_status, 200)
        self.assertEqual(preview["claim_count"], 2)
        self.assertEqual(preview["candidate_count"], 1)
        self.assertEqual(create_status, 201)
        self.assertEqual(run_status, 200)
        self.assertEqual(run["audit"]["status"], "completed")
        self.assertEqual(run["proposals"][0]["payload"]["operation"], "merge_claims")
        self.assertEqual(queue_status, 200)
        self.assertEqual(queue["proposals"][0]["scope"]["audit_id"], audit["id"])

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
        self.assertEqual(payload["ai_wiki_claim_limit"], 100)
        self.assertEqual(payload["ai_claim_comparison_limit"], 100)
        self.assertEqual(payload["intelligent_max_results"], 20)
        self.assertEqual(payload["default_search_mode"], "keyword")
        self.assertTrue(payload["web_ignore_year_filter"])
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

    def test_import_can_be_saved_as_default_search_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            server = create_server("127.0.0.1", 0, config_path)
            status, saved = self._request(
                server,
                "POST",
                "/api/config/default-search-mode",
                json.dumps({"mode": "import"}),
            )
            server = create_server("127.0.0.1", 0, config_path)
            _, fetched = self._request(server, "GET", "/api/config")

        self.assertEqual(status, 200)
        self.assertEqual(saved["default_search_mode"], "import")
        self.assertEqual(fetched["default_search_mode"], "import")

    def test_legacy_search_defaults_and_independent_ai_review(self):
        with tempfile.TemporaryDirectory() as folder:
            config_path = Path(folder) / "config.yml"
            for legacy, expected in (("keyword", False), ("intelligent", True), ("import", False)):
                config_path.write_text(f"default_search_mode: {legacy}\n", encoding="utf-8")
                server = create_server("127.0.0.1", 0, config_path)
                _, data = self._request(server, "GET", "/api/config")
                self.assertEqual(data["search_ai_review"], expected)
            for enabled in (True, False):
                server = create_server("127.0.0.1", 0, config_path)
                status, saved = self._request(server, "POST", "/api/config/default-search-mode",
                    json.dumps({"mode": "import", "ai_review": enabled}))
                self.assertEqual(status, 200)
                self.assertEqual(saved["default_search_mode"], "import")
                self.assertEqual(saved["search_ai_review"], enabled)
                server = create_server("127.0.0.1", 0, config_path)
                _, loaded = self._request(server, "GET", "/api/config")
                self.assertEqual(loaded["search_ai_review"], enabled)
            server = create_server("127.0.0.1", 0, config_path)
            status, saved = self._request(server, "POST", "/api/config/default-search-mode",
                json.dumps({"mode": "intelligent", "ai_review": False}))
            self.assertEqual(saved["default_search_mode"], "keyword")
            server = create_server("127.0.0.1", 0, config_path)
            status, _ = self._request(server, "POST", "/api/config/default-search-mode",
                json.dumps({"mode": "keyword", "ai_review": "false"}))
            self.assertEqual(status, 400)

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

    def test_search_ignores_legacy_web_year_settings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            usage_path = temp_path / "usage.json"
            config_path.write_text(
                "enabled_backends: arxiv,websearch\n"
                "searxng_url: http://127.0.0.1:8888/search\n"
                "web_ignore_year_filter: false\n",
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
        self.assertNotIn("websearch_strict_year_filter", payload["warnings"])

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

    def test_legacy_web_only_search_falls_back_to_academic_defaults(self):
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
        self.assertFalse(payload["can_find_more"])
        self.assertEqual(payload["enabled_backends"], ["arxiv", "openalex", "semanticscholar"])
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

    def test_config_requires_confirmation_before_removing_obsolete_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            original = (
                "email: old@example.com\n"
                "enabled_backends: arxiv,websearch\n"
                "searxng_url: http://127.0.0.1:8888/search\n"
                "web_ignore_year_filter: true\n"
                "ai_base_url: http://127.0.0.1:8000/v1\n"
                "ai_chat_model: old-model\n"
            )
            config_path.write_text(original, encoding="utf-8")

            server = create_server("127.0.0.1", 0, config_path)
            status, payload = self._request(
                server,
                "POST",
                "/api/config",
                json.dumps({"email": "new@example.com", "enabled_backends": ["arxiv"]}),
            )

            self.assertEqual(status, 409)
            self.assertEqual(payload["error"], "obsolete_config_confirmation_required")
            self.assertEqual(config_path.read_text(encoding="utf-8"), original)
            keys = {item["key"] for item in payload["obsolete_config_items"]}
            self.assertTrue({
                "searxng_url",
                "web_ignore_year_filter",
                "ai_base_url",
                "ai_chat_model",
                "enabled_backends:websearch",
            }.issubset(keys))

    def test_confirmed_config_save_removes_obsolete_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            config_path.write_text(
                "enabled_backends: arxiv,websearch\n"
                "searxng_proxy: http://host.docker.internal:7890\n"
                "ai_timeout_seconds: 120\n"
                "ai_verify_limit: 30\n"
                "future_setting: keep-me\n",
                encoding="utf-8",
            )

            server = create_server("127.0.0.1", 0, config_path)
            status, payload = self._request(
                server,
                "POST",
                "/api/config",
                json.dumps({
                    "email": "new@example.com",
                    "enabled_backends": ["arxiv"],
                    "confirm_remove_obsolete_config": True,
                }),
            )

            self.assertEqual(status, 200)
            stored = config_path.read_text(encoding="utf-8")
            self.assertIn("email: new@example.com", stored)
            self.assertIn("enabled_backends: arxiv", stored)
            self.assertNotIn("websearch", stored)
            self.assertNotIn("searxng_proxy", stored)
            self.assertNotIn("ai_timeout_seconds", stored)
            self.assertNotIn("ai_verify_limit", stored)
            self.assertIn("future_setting: keep-me", stored)
            self.assertEqual(payload["enabled_backends"], ["arxiv"])

    def test_config_rejects_web_only_backend_selection(self):
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

            self.assertEqual(status, 400)
            self.assertEqual(payload["error"], "no_search_backends")

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

    def test_ai_profile_config_is_write_only_and_routes_embedding_separately(self):
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
                        "ai_model_profiles": [
                            {
                                "id": "chat",
                                "name": "Chat model",
                                "provider": "openai_compatible",
                                "base_url": "https://chat.test/v1",
                                "model": "chat-model",
                                "api_key": "chat-secret",
                                "capabilities": ["chat"],
                            },
                            {
                                "id": "embed",
                                "name": "Embedding model",
                                "provider": "openai_compatible",
                                "base_url": "http://127.0.0.1:11434/v1",
                                "model": "embed-model",
                                "api_key": "embed-secret",
                                "capabilities": ["embeddings"],
                            },
                        ],
                        "ai_role_assignments": {
                            "intelligent_search": "chat",
                            "embedding": "embed",
                        },
                        "intelligent_max_results": 25,
                        "ai_verify_batch_size": 4,
                        "ai_verify_concurrency": 2,
                        "ai_search_timeout_seconds": 600,
                        "ai_stage_timeout_seconds": 300,
                        "ai_evidence_source_limit": 9,
                        "ai_claim_evidence_limit": 45,
                        "ai_wiki_claim_limit": 350,
                        "ai_claim_comparison_limit": 150,
                        "ai_copilot_context_limit": 24,
                    }
                ),
            )
            server = create_server("127.0.0.1", 0, config_path)
            get_status, fetched = self._request(server, "GET", "/api/config")

            self.assertEqual(status, 200)
            self.assertEqual(get_status, 200)
            self.assertTrue(saved["ai_configured"])
            profiles = {item["id"]: item for item in fetched["ai_model_profiles"]}
            self.assertTrue(profiles["chat"]["api_key_configured"])
            self.assertTrue(profiles["embed"]["api_key_configured"])
            self.assertEqual(fetched["ai_api_key"], "")
            self.assertEqual(fetched["ai_embedding_api_key"], "")
            self.assertEqual(fetched["intelligent_max_results"], 25)
            self.assertEqual(fetched["ai_verify_batch_size"], 4)
            self.assertEqual(fetched["ai_verify_concurrency"], 2)
            self.assertEqual(fetched["ai_search_timeout_seconds"], 600)
            self.assertEqual(fetched["ai_stage_timeout_seconds"], 300)
            self.assertEqual(fetched["ai_evidence_source_limit"], 9)
            self.assertEqual(fetched["ai_claim_evidence_limit"], 45)
            self.assertEqual(fetched["ai_wiki_claim_limit"], 350)
            self.assertEqual(fetched["ai_claim_comparison_limit"], 150)
            self.assertEqual(fetched["ai_copilot_context_limit"], 24)
            config_text = config_path.read_text(encoding="utf-8")
            self.assertIn("chat-secret", config_text)
            self.assertIn("embed-secret", config_text)
            self.assertNotIn("ai_base_url:", config_text)
            self.assertNotIn("ai_timeout_seconds:", config_text)

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
