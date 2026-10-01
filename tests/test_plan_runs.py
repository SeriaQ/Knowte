import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from knowte.automation import catalog, mutate
from knowte.plan_runs import execute_run, list_runs, queue_run, recover_interrupted


def paper(name, year=None, **extra):
    return {"title": name, "authors": "A. Researcher", "year": year,
            "url": f"https://example.org/{name}", **extra}


class PlanRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "knowte.db"
        self.config = self.db.with_name("config.yml")
        self.config.write_text("{}")
        self.action = mutate({"operation": "save_action", "name": "RL", "config": {
            "query": "RL", "sources": ["arxiv"], "max_papers": 100}}, self.db)["saved_id"]
        self.plan = self.new_plan("Daily")

    def new_plan(self, name):
        return mutate({"operation": "save_plan", "name": name, "action_ids": [self.action]}, self.db)["saved_id"]

    def run_fake(self, items, plan=None, review=None):
        run_id, created = queue_run(plan or self.plan, self.db)
        self.assertTrue(created)
        execute_run(run_id, self.db, self.config, retrieve=lambda *args: items,
                    review=review or (lambda config, candidates, *args: {"results": candidates}))
        return list_runs(self.db, run_id=run_id)[0]

    def test_incremental_undated_and_date_changes_not_identity(self):
        one = self.run_fake([paper("A"), paper("B"), paper("C")])
        two = self.run_fake([paper("B", 2025), paper("C"), paper("D")])
        self.assertEqual(one["counts"]["new_count"], 3)
        self.assertEqual(two["counts"]["new_count"], 1)
        self.assertEqual(two["counts"]["duplicate_count"], 2)
        self.assertEqual(two["counts"]["selected_count"], 1)
        self.assertEqual(two["status"], "completed")
        self.assertEqual(two["actions"][0]["checkpoint_before"], one["actions"][0]["checkpoint_after"])

    def test_shared_action_independent_consumption(self):
        self.run_fake([paper("A")])
        other = self.run_fake([paper("A")], plan=self.new_plan("Weekly"))
        self.assertEqual(other["counts"]["new_count"], 1)

    def test_seen_first_page_is_refilled_with_three_new_items(self):
        from knowte.plan_runs import _refill
        self.run_fake([paper("A"), paper("B"), paper("C")])
        association = catalog(self.db)["plans"][0]["actions"][0]["id"]
        pages = [[paper("A"), paper("B"), paper("C")], [paper("D"), paper("E"), paper("F")]]
        calls = []
        def retrieve(config, *args):
            calls.append(config["_page"])
            return pages[config["_page"]]
        results, report = _refill({"max_papers": 3}, "arxiv", {}, self.db, association, retrieve)
        self.assertEqual(calls, [0, 1])
        self.assertEqual(len(results), 6)
        self.assertEqual(report["new_candidates"], 3)
        self.assertEqual(report["stop_reason"], "target reached")

    def test_refill_preserves_partial_results_and_redacts_errors(self):
        from knowte.plan_runs import _refill
        association = catalog(self.db)["plans"][0]["actions"][0]["id"]
        def retrieve(config, *args):
            if config["_page"]:
                raise TimeoutError("secret-token")
            return [paper("A")]
        results, report = _refill({"max_papers": 3}, "arxiv", {}, self.db, association, retrieve)
        self.assertEqual(len(results), 1)
        self.assertTrue(report["incomplete"])
        self.assertNotIn("secret-token", json.dumps(report))

    def test_refill_empty_filtered_page_does_not_stop_scan(self):
        from knowte.plan_runs import _refill
        association = catalog(self.db)["plans"][0]["actions"][0]["id"]
        def retrieve(config, *args):
            config["_raw_count"] = 3
            return [] if config["_page"] == 0 else [paper("A")]
        _, report = _refill({"max_papers": 1}, "arxiv", {}, self.db, association, retrieve)
        self.assertEqual(report["pages"], 2)

    def test_refill_limit_and_partial_checkpoint(self):
        from knowte.plan_runs import _refill
        association = catalog(self.db)["plans"][0]["actions"][0]["id"]
        _, report = _refill({"max_papers": 100}, "arxiv", {}, self.db, association,
                            lambda config, *args: [paper(str(config["_page"]))])
        self.assertEqual(report["pages"], 10)
        self.assertIn("limit", report["stop_reason"])
        first = self.run_fake([paper("A")])
        def retrieve(config, *args):
            if config["_page"]:
                raise TimeoutError("private")
            return [paper("B")]
        run_id, _ = queue_run(self.plan, self.db)
        execute_run(run_id, self.db, self.config, retrieve=retrieve,
                    review=lambda config, candidates, *args: {"results": candidates})
        result = list_runs(self.db, run_id=run_id)[0]
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["counts"]["new_count"], 1)
        self.assertEqual(result["actions"][0]["checkpoint_after"], first["actions"][0]["checkpoint_after"])

    def test_duplicate_queue_is_one_run_and_edit_is_blocked(self):
        first, _ = queue_run(self.plan, self.db)
        self.assertEqual(queue_run(self.plan, self.db), (first, False))
        with self.assertRaisesRegex(ValueError, "active Run"):
            mutate({"operation": "save_plan", "id": self.plan, "name": "Changed"}, self.db)
        with self.assertRaisesRegex(ValueError, "active Run"):
            mutate({"operation": "delete_plan", "id": self.plan}, self.db)

    def test_run_snapshot_does_not_follow_action_edits(self):
        run_id, _ = queue_run(self.plan, self.db)
        mutate({"operation": "save_action", "id": self.action, "version": 1,
            "config": {"query": "CHANGED", "sources": ["arxiv"]}}, self.db)
        seen = []
        def retrieve(config, *args):
            seen.append(config["query"])
            return []
        execute_run(run_id, self.db, self.config, retrieve=retrieve)
        run = list_runs(self.db, run_id=run_id)[0]
        self.assertEqual(seen, ["RL"])
        self.assertEqual(run["actions"][0]["action_version"], 1)

    def test_partial_provider_failure_preserves_checkpoint(self):
        mutate({"operation": "save_action", "id": self.action, "version": 1,
            "config": {"query": "RL", "sources": ["arxiv", "openalex"]}}, self.db)
        baseline = self.run_fake([paper("A")])
        run_id, _ = queue_run(self.plan, self.db)
        def retrieve(config, provider, *args):
            if provider == "openalex":
                raise OSError("secret URL must not be logged")
            return [paper("B")]
        execute_run(run_id, self.db, self.config, retrieve=retrieve,
                    review=lambda config, candidates, *args: {"results": candidates})
        run = list_runs(self.db, run_id=run_id)[0]
        self.assertEqual(run["status"], "partial")
        self.assertEqual(run["actions"][0]["checkpoint_after"]["providers"]["openalex"], baseline["actions"][0]["checkpoint_after"]["providers"]["openalex"])
        self.assertNotIn("secret URL", json.dumps(run))

    def test_failed_commit_does_not_mark_seen_or_advance(self):
        run_id, _ = queue_run(self.plan, self.db)
        execute_run(run_id, self.db, self.config, retrieve=lambda *args: [paper("A"), None])
        run = list_runs(self.db, run_id=run_id)[0]
        self.assertEqual(run["status"], "failed")
        self.assertFalse(run["actions"][0]["checkpoint_after"])
        self.assertEqual(run["counts"]["new_count"], 0)
        retry = self.run_fake([paper("A")])
        self.assertEqual(retry["counts"]["new_count"], 1)

    def test_ai_failure_and_overflow_remain_pending(self):
        def failure(*args):
            raise TimeoutError()
        first = self.run_fake([paper("A"), paper("B")], review=failure)
        self.assertEqual(first["status"], "partial")
        self.assertEqual(first["actions"][0]["report"]["pending_count"], 2)
        seen = []
        def choose_one(config, candidates, *args):
            seen.extend(item["title"] for item in candidates)
            return {"results": candidates[:1]}
        self.run_fake([], review=choose_one)
        self.assertEqual(seen, ["A", "B"])
        seen.clear()
        self.run_fake([], review=choose_one)
        self.assertEqual(seen, ["B"])
        final = self.run_fake([paper("A"), paper("B")], review=lambda *args: self.fail("Reviewed seen items again"))
        self.assertEqual(final["counts"]["selected_count"], 0)

    def test_provider_identity_enrichment_deduplicates(self):
        self.run_fake([paper("A", id="W1", source="OpenAlex")])
        enriched = self.run_fake([paper("A", id="S2id", source="Semantic Scholar", doi_url="https://doi.org/10.123/a")])
        self.assertEqual(enriched["counts"]["new_count"], 0)

    def test_recovery_only_dead_owner_and_preserves_commits(self):
        completed = self.run_fake([paper("A")])
        run_id, _ = queue_run(self.plan, self.db)
        with patch("knowte.plan_runs.os.kill", side_effect=ProcessLookupError):
            recover_interrupted(self.db)
        interrupted = list_runs(self.db, run_id=run_id)[0]
        self.assertEqual(interrupted["status"], "failed")
        self.assertEqual(list_runs(self.db, run_id=completed["id"])[0]["status"], "completed")
        self.assertEqual(self.run_fake([paper("A")])["counts"]["new_count"], 0)

    def test_strict_provider_failure_differs_from_empty(self):
        from knowte.providers.arxiv import search_arxiv
        from knowte.providers.openalex import search_openalex
        from knowte.providers.semanticscholar import search_semanticscholar
        for module, call in (("arxiv", lambda **kw: search_arxiv("RL", **kw)),
                             ("openalex", lambda **kw: search_openalex("RL", None, **kw)),
                             ("semanticscholar", lambda **kw: search_semanticscholar("RL", **kw))):
            with patch(f"knowte.providers.{module}.urlopen", side_effect=OSError):
                self.assertEqual(call(), [])
                with self.assertRaises(OSError):
                    call(raise_errors=True)

    def test_ai_review_injected_candidates_never_fetches_again(self):
        from knowte.intelligent import intelligent_search
        client = Mock(embedding_model="")
        client.usage_snapshot.return_value = {"chat_requests": 1, "chat_tokens": 10}
        candidates = [paper("New", id="new")]
        with patch("knowte.intelligent._client_from_config", return_value=client), \
             patch("knowte.intelligent.search_papers") as retrieval, \
             patch("knowte.intelligent._verify_batched", return_value=([{
                 **candidates[0], "relevance_tier": "strong"}], [], 1)) as verify:
            response = intelligent_search("RL", {}, 20, ["arxiv"], [], None, None,
                                          recall_candidates=candidates)
        retrieval.assert_not_called()
        self.assertEqual(verify.call_args.args[3], candidates)
        self.assertEqual(response["request_budget"]["academic_retrieval"], 0)
        self.assertEqual(response["results"][0]["title"], "New")


if __name__ == "__main__":
    unittest.main()
