import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from knowte.automation import mutate
from knowte.knowledge import create_evidence_proposal, list_evidence_proposals, list_evidence, save_source, accept_evidence_proposal, list_claim_proposals, list_claims
from knowte.plan_runs import queue_run, execute_run, list_runs
from knowte.server import generate_evidence_proposals, generate_claim_proposals


class PlanKnowledgeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / "knowte.db"
        self.config = self.db.with_name("config.yaml")
        self.config.write_text("{}")
        action = mutate({"operation": "save_action", "name": "RL", "config": {"query": "RL", "sources": ["arxiv"]}}, self.db)["saved_id"]
        self.plan = mutate({"operation": "save_plan", "name": "Daily", "action_ids": [action], "processing": {
            "save_sources": True, "max_new_sources": 20, "evidence": {"enabled": True, "focus": "RL foundations", "model_profile_id": "m"}}}, self.db)["saved_id"]
        self.profiles = patch("knowte.plan_knowledge.ai_model_profiles", return_value=[{"id": "m", "capabilities": ["chat"]}])
        self.profiles.start(); self.addCleanup(self.profiles.stop)
        self.settings = patch("knowte.plan_knowledge.load_config", return_value={"ai_evidence_source_limit": 2})
        self.settings_mock = self.settings.start(); self.addCleanup(self.settings.stop)

    def generate(self, payload, config, path, content, *, automation_scope):
        proposals = [create_evidence_proposal({"source_id": sid, "quote": "A grounded excerpt", "verification": "external_unverified"},
            "fixture", "model", automation_scope, path) for sid in payload["source_ids"]]
        return {"proposals": proposals, "warnings": [], "model_usage": {"chat_requests": 1}}, 201

    def run_fake(self, items, generate=None):
        run_id, _ = queue_run(self.plan, self.db)
        with patch("knowte.server.generate_evidence_proposals", side_effect=generate or self.generate) as service:
            execute_run(run_id, self.db, self.config, retrieve=lambda *args: items,
                review=lambda config, candidates, *args: {"results": candidates})
        return list_runs(self.db, run_id=run_id)[0], service.call_count

    def test_sources_to_pending_evidence_and_repeat_does_not_regenerate(self):
        items = [{"title": f"Paper {i}", "url": f"https://example.org/{i}"} for i in range(3)]
        first, calls = self.run_fake(items)
        self.assertEqual(calls, 2)
        self.assertEqual(first["status"], "completed")
        self.assertEqual(len(first["knowledge_jobs"]), 2)
        self.assertEqual(len(list_evidence_proposals(self.db)), 3)
        self.assertEqual(list_evidence(self.db), [])
        second, calls = self.run_fake(items)
        self.assertEqual(calls, 0)
        self.assertEqual(second["knowledge_jobs"], [])
        self.assertEqual(len(list_evidence_proposals(self.db)), 3)

    def test_failed_job_retries_without_erasing_run_history(self):
        first, _ = self.run_fake([{"title": "A", "url": "https://example.org/a"}], lambda *a, **kw: ({"message": "fixture error"}, 502))
        self.assertEqual(first["status"], "partial")
        second, calls = self.run_fake([])
        self.assertEqual(calls, 1)
        self.assertEqual(second["knowledge_jobs"][0]["status"], "completed")
        self.assertEqual(list_runs(self.db, run_id=first["id"])[0]["knowledge_jobs"][0]["status"], "failed")

    def test_review_before_downstream_generation_keeps_result_mapping(self):
        self.run_fake([{"title": "A", "url": "https://example.org/a"}])
        proposal = list_evidence_proposals(self.db)[0]
        evidence = accept_evidence_proposal(proposal["id"], path=self.db)
        with sqlite3.connect(self.db) as connection:
            result = connection.execute("SELECT decision, result_id FROM proposal_outcomes WHERE proposal_id = ?", (proposal["id"],)).fetchone()
        self.assertEqual(result, ("accepted", evidence["id"]))

    def test_partial_persistence_is_recovered_without_duplicate_model_call(self):
        def interrupted(*args, **kwargs):
            self.generate(*args, **kwargs)
            raise RuntimeError("Worker stopped after saving")
        first, _ = self.run_fake([{"title": "A", "url": "https://example.org/a"}], interrupted)
        second, calls = self.run_fake([])
        self.assertEqual(calls, 0)
        self.assertEqual(second["knowledge_jobs"][0]["status"], "partial")
        self.assertEqual(len(list_evidence_proposals(self.db)), 1)
        self.assertEqual(first["status"], "partial")

    def test_individual_mode_and_disabled_compatibility(self):
        self.settings_mock.return_value = {"ai_evidence_request_mode": "individual"}
        _, calls = self.run_fake([{"title": str(i), "url": f"https://example.org/{i}"} for i in range(3)])
        self.assertEqual(calls, 3)
        mutate({"operation": "save_plan", "id": self.plan, "processing": {"save_sources": True, "max_new_sources": 20}}, self.db)
        _, calls = self.run_fake([{"title": "New", "url": "https://example.org/new"}])
        self.assertEqual(calls, 0)

    def test_valid_empty_generation_does_not_repeat_paid_calls(self):
        result, calls = self.run_fake([{"title": "A", "url": "https://example.org/a"}],
            lambda *a, **kw: ({"proposals": [], "warnings": ["No relevant Evidence for this Focus"], "failed_groups": 0}, 201))
        self.assertEqual(calls, 1)
        self.assertEqual(result["knowledge_jobs"][0]["status"], "partial")
        _, calls = self.run_fake([])
        self.assertEqual(calls, 0)

    def test_shared_service_url_fetch_does_not_capture_or_repeat_segments(self):
        source, _, _ = save_source({"title": "Web", "url": "https://example.org/web", "result_type": "web"}, path=self.db)
        client = Mock()
        client.grounded_json.return_value = {"evidence": [{"source_id": source["id"], "quote": "Direct external excerpt"}]}
        client.usage_snapshot.return_value = {"chat_requests": 1}
        with patch("knowte.server._client_from_config", return_value=client), \
             patch("knowte.server.ai_model_profiles", return_value=[{"id": "m", "capabilities": ["chat", "url_fetch"]}]), \
             patch("knowte.server._model_name_from_config", return_value="Fixture"), \
             patch("knowte.server.discover_source_images", return_value=[]), \
             patch("knowte.server.record_ai_usage", return_value={}), \
             patch("knowte.server.capture_source_content") as capture:
            result, status = generate_evidence_proposals({"source_ids": [source["id"]], "focus": "", "model_profile_id": "m"}, self.config, self.db, self.db.parent / "content")
        self.assertEqual(status, 201)
        self.assertEqual(len(result["proposals"]), 1)
        capture.assert_not_called()
        client.chat_json.assert_not_called()
        manifest = json.loads(client.grounded_json.call_args.args[1])
        self.assertEqual(manifest["sources"][0]["segments"], [])
        self.assertEqual(client.grounded_json.call_args.kwargs["urls"], [source["url"]])

    def test_feed_content_is_grounded_locally_even_with_url_fetch(self):
        # Feed content must survive saving and be quote-matched, not revisited at X.
        source, _, _ = save_source({"title": "Post", "url": "https://x.com/test/status/1", "result_type": "web",
            "feed_content": {"text": "A precise post excerpt", "feed_url": "http://localhost/feed"}}, path=self.db)
        client = Mock()
        client.chat_json.return_value = {"evidence": [{"source_id": source["id"], "quote": "A precise post excerpt"}]}
        client.usage_snapshot.return_value = {"chat_requests": 1}
        with patch("knowte.server._client_from_config", return_value=client), \
             patch("knowte.server.ai_model_profiles", return_value=[{"id": "m", "capabilities": ["chat", "url_fetch"]}]), \
             patch("knowte.server._model_name_from_config", return_value="Fixture"), \
             patch("knowte.server.record_ai_usage", return_value={}), \
             patch("knowte.server.capture_source_content") as capture, \
             patch("knowte.server.discover_source_images") as images:
            result, status = generate_evidence_proposals({"source_ids": [source["id"]], "model_profile_id": "m"}, self.config, self.db, self.db.parent / "content")
        self.assertEqual(status, 201)
        self.assertEqual(len(result["proposals"]), 1)
        self.assertEqual(result["proposals"][0]["payload"]["verification"], "local_match")
        client.grounded_json.assert_not_called()
        capture.assert_not_called()
        images.assert_not_called()

    def test_connection_failure_defers_remaining_batches_and_next_run_retries(self):
        self.settings_mock.return_value = {"ai_evidence_source_limit": 1}
        items = [{"title": str(i), "url": f"https://example.org/{i}"} for i in range(3)]
        failed = lambda *a, **kw: ({"proposals": [], "failed_groups": 1,
            "failures": [{"code": "connection_failed"}], "warnings": []}, 201)
        first, calls = self.run_fake(items, failed)
        self.assertEqual(calls, 1)
        second, calls = self.run_fake([])
        self.assertEqual(calls, 3)
        self.assertEqual(second["status"], "completed")

    def test_feed_prefers_content_and_decodes_entities(self):
        from knowte.subscriptions import parse_feed
        entries = parse_feed(b'<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item><title>Post</title><link>https://example.org/post</link><description>Short</description><content:encoded><![CDATA[<p>Full &amp; longer</p>]]></content:encoded></item></channel></rss>', "https://example.org/feed", "Feed")
        self.assertEqual(entries[0]["feed_content"]["text"], "Full & longer")

    def test_provider_errors_do_not_expose_credentials(self):
        from urllib.error import HTTPError
        from knowte.plan_runs import _safe_provider_error
        error = HTTPError("https://example.org?key=secret", 429, "secret", {}, None)
        self.assertEqual(_safe_provider_error(error), "HTTP 429")

    def test_inaccessible_url_is_failed_not_valid_empty_extraction(self):
        source, _, _ = save_source({"title": "Private page", "url": "https://example.org/private"}, path=self.db)
        client = Mock()
        client.grounded_json.return_value = {"evidence": [], "inaccessible_source_ids": [source["id"]]}
        client.usage_snapshot.return_value = {"chat_requests": 1}
        with patch("knowte.server._client_from_config", return_value=client), \
             patch("knowte.server.ai_model_profiles", return_value=[{"id": "m", "capabilities": ["chat", "url_fetch"]}]), \
             patch("knowte.server.discover_source_images", return_value=[]), \
             patch("knowte.server.record_ai_usage", return_value={}):
            result, status = generate_evidence_proposals({"source_ids": [source["id"]], "model_profile_id": "m"}, self.config, self.db, self.db.parent / "content")
        self.assertEqual(result["failed_groups"], 1)
        self.assertEqual(result["failures"][0]["code"], "source_inaccessible")
        self.assertEqual(result["proposals"], [])

    def test_shared_service_native_pdf_uses_original_bytes_without_parsed_text(self):
        source, _, _ = save_source({"title": "PDF", "url": "https://example.org/paper", "pdf_url": "https://example.org/paper.pdf"}, path=self.db)
        document = self.db.with_name("fixture.pdf")
        document.write_bytes(b"%PDF-fixture")
        client = Mock()
        client.grounded_json.return_value = {"evidence": [{"source_id": source["id"], "quote": "Native document excerpt"}]}
        client.usage_snapshot.return_value = {"chat_requests": 1}
        with patch("knowte.server._client_from_config", return_value=client), \
             patch("knowte.server.ai_model_profiles", return_value=[{"id": "m", "capabilities": ["chat", "native_documents"]}]), \
             patch("knowte.server._model_name_from_config", return_value="Fixture"), \
             patch("knowte.server.record_ai_usage", return_value={}), \
             patch("knowte.server.capture_source_content", return_value={"raw_path": str(document), "media_type": "application/pdf"}) as capture:
            result, status = generate_evidence_proposals({"source_ids": [source["id"]], "focus": "RL", "model_profile_id": "m"}, self.config, self.db, self.db.parent / "content")
        self.assertEqual(status, 201)
        self.assertEqual(len(result["proposals"]), 1)
        self.assertFalse(capture.call_args.kwargs["parse_pdf"])
        self.assertEqual(client.grounded_json.call_args.kwargs["documents"][0]["data"], b"%PDF-fixture")
        self.assertEqual(json.loads(client.grounded_json.call_args.args[1])["sources"][0]["segments"], [])

    def enable_claims(self):
        mutate({"operation": "save_plan", "id": self.plan, "processing": {
            "save_sources": True, "max_new_sources": 20,
            "evidence": {"enabled": True, "focus": "RL", "model_profile_id": "m"},
            "claims": {"enabled": True, "focus": "Compare concepts", "model_profile_id": "m"}}}, self.db)

    def claims_client(self, during_call=None):
        client = Mock()
        def respond(prompt, request, **kwargs):
            data = json.loads(request)
            if during_call:
                during_call(data)
            return {"claims": [{"statement": "A combined conclusion", "basis": "inference",
                "evidence": [{"evidence_id": item["evidence_id"], "stance": "supports"} for item in data["evidence"]]}]}
        client.chat_json.side_effect = respond
        client.usage_snapshot.return_value = {"chat_requests": 1}
        return client

    def test_complete_plan_continues_through_pending_evidence_to_claims(self):
        self.enable_claims()
        client = self.claims_client()
        items = [{"title": f"Paper {i}", "url": f"https://example.org/{i}"} for i in range(2)]
        with patch("knowte.server._client_from_config", return_value=client), patch("knowte.server._model_name_from_config", return_value="Fixture"), patch("knowte.server.record_ai_usage", return_value={}):
            run, _ = self.run_fake(items)
            again, _ = self.run_fake(items)
        self.assertEqual(run["status"], "completed")
        self.assertEqual(client.chat_json.call_count, 1)
        self.assertEqual([job["stage"] for job in run["knowledge_jobs"]], ["evidence", "claims"])
        self.assertEqual(again["knowledge_jobs"], [])
        self.assertEqual(list_evidence(self.db), [])
        self.assertEqual(list_claims(self.db), [])
        claim = list_claim_proposals(self.db)[0]
        self.assertEqual(claim["derivation"]["pending_count"], 2)
        self.assertEqual(claim["status"], "awaiting_review")
        self.assertEqual(len(list_evidence_proposals(self.db)), 2)

    def test_unchanged_evidence_review_during_call_resolves_without_retry(self):
        self.enable_claims()
        def accept(data):
            for item in data["evidence"]:
                accept_evidence_proposal(item["evidence_id"][9:], path=self.db)
        client = self.claims_client(accept)
        with patch("knowte.server._client_from_config", return_value=client), patch("knowte.server._model_name_from_config", return_value="Fixture"), patch("knowte.server.record_ai_usage", return_value={}):
            run, _ = self.run_fake([{"title": str(i), "url": f"https://example.org/{i}"} for i in range(2)])
        self.assertEqual(run["status"], "completed")
        proposal = list_claim_proposals(self.db)[0]
        self.assertEqual(proposal["derivation"]["pending_count"], 0)
        self.assertTrue(all(not link["evidence_id"].startswith("proposal:") for link in proposal["payload"]["evidence"]))
        self.assertEqual(proposal["status"], "awaiting_review")

    def test_changed_evidence_during_call_is_not_saved_as_current_claim(self):
        self.enable_claims()
        def revise(data):
            accept_evidence_proposal(data["evidence"][0]["evidence_id"][9:], {"quote": "Changed meaning"}, self.db)
        client = self.claims_client(revise)
        with patch("knowte.server._client_from_config", return_value=client), patch("knowte.server._model_name_from_config", return_value="Fixture"), patch("knowte.server.record_ai_usage", return_value={}):
            run, _ = self.run_fake([{"title": str(i), "url": f"https://example.org/{i}"} for i in range(2)])
        self.assertEqual(run["status"], "partial")
        self.assertEqual(list_claim_proposals(self.db), [])
        self.assertEqual(run["knowledge_jobs"][-1]["status"], "failed")

    def test_claim_failure_retries_from_persisted_evidence_without_recapture(self):
        self.enable_claims()
        with patch("knowte.server.generate_claim_proposals", return_value=({"message": "Fixture failure"}, 502)):
            first, _ = self.run_fake([{"title": str(i), "url": f"https://example.org/{i}"} for i in range(2)])
        client = self.claims_client()
        with patch("knowte.server._client_from_config", return_value=client), patch("knowte.server._model_name_from_config", return_value="Fixture"), patch("knowte.server.record_ai_usage", return_value={}):
            second, evidence_calls = self.run_fake([])
        self.assertEqual(evidence_calls, 0)
        self.assertEqual(client.chat_json.call_count, 1)
        self.assertEqual(second["knowledge_jobs"][0]["status"], "completed")
        self.assertEqual(list_runs(self.db, run_id=first["id"])[0]["knowledge_jobs"][-1]["status"], "failed")

    def test_saved_claims_recover_without_repeat_model_call(self):
        self.enable_claims()
        client = self.claims_client()
        def interrupted(*args, **kwargs):
            generate_claim_proposals(*args, **kwargs)
            raise RuntimeError("Stopped after Claim save")
        with patch("knowte.server._client_from_config", return_value=client), patch("knowte.server._model_name_from_config", return_value="Fixture"), patch("knowte.server.record_ai_usage", return_value={}):
            with patch("knowte.server.generate_claim_proposals", side_effect=interrupted):
                self.run_fake([{"title": str(i), "url": f"https://example.org/{i}"} for i in range(2)])
            second, _ = self.run_fake([])
        self.assertEqual(client.chat_json.call_count, 1)
        self.assertEqual(len(list_claim_proposals(self.db)), 1)
        self.assertEqual(second["knowledge_jobs"][0]["status"], "partial")
