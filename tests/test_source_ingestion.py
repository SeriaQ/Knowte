import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from knowte.automation import catalog, mutate
from knowte.knowledge import get_source_workspace, list_sources, save_source
from knowte.plan_runs import execute_run, list_runs, queue_run
from knowte.source_ingestion import ingest_run, source_discoveries


def paper(name, **extra):
    return {"title": name, "authors": "A. Researcher", "url": f"https://example.org/{name}", **extra}


class SourceIngestionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / "knowte.db"
        self.config = self.db.with_name("config.yml")
        self.config.write_text("{}")
        self.action = self.add_action("RL")
        self.plan = mutate({"operation": "save_plan", "name": "Daily", "action_ids": [self.action],
            "processing": {"save_sources": True, "max_new_sources": 1}}, self.db)["saved_id"]

    def add_action(self, name):
        return mutate({"operation": "save_action", "name": name,
            "config": {"query": name, "sources": ["arxiv"]}}, self.db)["saved_id"]

    def run_fake(self, items):
        run_id, _ = queue_run(self.plan, self.db)
        execute_run(run_id, self.db, self.config, retrieve=lambda *args: items,
                    review=lambda config, candidates, *args: {"results": candidates})
        return list_runs(self.db, run_id=run_id)[0]

    def test_overflow_is_deferred_not_lost_and_no_second_review(self):
        one = self.run_fake([paper("A"), paper("B")])
        self.assertEqual(one["ingestion"], {"sources_created": 1, "sources_reused": 0, "deferred": 1, "enabled": True})
        two = self.run_fake([])
        self.assertEqual(two["ingestion"]["sources_created"], 1)
        self.assertEqual(two["ingestion"]["deferred"], 0)
        self.assertEqual(two["counts"]["selected_count"], 0)
        self.assertEqual({s["title"] for s in list_sources(self.db)}, {"A", "B"})
        source = next(s for s in list_sources(self.db) if s["title"] == "B")
        path = source_discoveries(source["id"], self.db)[0]
        self.assertEqual(path["run_id"], one["id"])
        self.assertEqual(path["ingestion_run_id"], two["id"])

    def test_cross_action_dedup_provenance_and_idempotence(self):
        other = self.add_action("Robotics")
        mutate({"operation": "save_plan", "id": self.plan, "action_ids": [self.action, other]}, self.db)
        run = self.run_fake([paper("A")])
        self.assertEqual(run["ingestion"]["sources_created"], 1)
        self.assertEqual(run["ingestion"]["sources_reused"], 0)
        source = list_sources(self.db)[0]
        self.assertEqual(len(source_discoveries(source["id"], self.db)), 2)
        self.assertEqual(ingest_run(run["id"], self.db), run["ingestion"])
        self.assertEqual(len(list_sources(self.db)), 1)
        again = self.run_fake([paper("A")])
        self.assertEqual(again["ingestion"]["sources_reused"], 1)
        self.assertEqual(len(get_source_workspace(source["id"], self.db)["source"]["discoveries"]), 4)

    def test_existing_source_preserved_and_reuse_does_not_spend_limit(self):
        source, _, _ = save_source(paper("B", abstract="User content"), path=self.db)
        run = self.run_fake([paper("A"), paper("B", abstract="Provider replacement")])
        self.assertEqual(run["ingestion"]["sources_reused"], 1)
        self.assertEqual(run["ingestion"]["sources_created"], 1)
        saved = next(item for item in list_sources(self.db) if item["id"] == source["id"])
        self.assertEqual(saved["abstract"], "User content")
        self.assertEqual(saved["updated_at"], source["updated_at"])

    def test_failure_rolls_back_sources_receipts_and_provenance(self):
        mutate({"operation": "save_plan", "id": self.plan, "processing": {"save_sources": True, "max_new_sources": 2}}, self.db)
        def fail_second(payload, **kwargs):
            if payload["title"] == "B":
                raise RuntimeError("fixture")
            return save_source(payload, **kwargs)
        with patch("knowte.source_ingestion.save_source", side_effect=fail_second):
            failed = self.run_fake([paper("A"), paper("B")])
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(list_sources(self.db), [])
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT processing_status FROM plan_action_seen").fetchone()[0], "selected")
            self.assertEqual(connection.execute("SELECT count(*) FROM source_discoveries").fetchone()[0], 0)
        retry = self.run_fake([])
        self.assertEqual(retry["ingestion"]["sources_created"], 2)

    def test_search_and_subscribe_share_source_keep_both_paths(self):
        from knowte.subscriptions import save_subscription
        channel = save_subscription({"name": "Research blog", "url": "https://example.org/feed"}, self.db)
        action = mutate({"operation": "save_action", "name": "Blogs", "kind": "subscribe",
            "config": {"subscription_ids": [channel]}}, self.db)["saved_id"]
        mutate({"operation": "save_plan", "id": self.plan, "action_ids": [self.action, action]}, self.db)
        with patch("knowte.subscriptions.fetch_subscription", return_value=[paper("A", result_type="web")]):
            run = self.run_fake([paper("A")])
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["ingestion"]["sources_created"], 1)
        paths = source_discoveries(list_sources(self.db)[0]["id"], self.db)
        self.assertEqual({item["kind"] for item in paths}, {"search", "subscribe"})
        self.assertIn("Research blog", {item["channel"] for item in paths})

    def test_policy_snapshot_and_old_plan_compatibility(self):
        with sqlite3.connect(self.db) as connection:
            connection.execute("DELETE FROM plan_processing_policy")
        self.assertFalse(catalog(self.db)["plans"][0]["processing"]["save_sources"])
        run = self.run_fake([paper("A")])
        self.assertFalse(run["processing"]["save_sources"])
        self.assertEqual(list_sources(self.db), [])
        mutate({"operation": "save_plan", "id": self.plan, "processing": {"save_sources": True, "max_new_sources": 2}}, self.db)
        self.assertFalse(list_runs(self.db, run_id=run["id"])[0]["processing"]["save_sources"])
        self.assertEqual(self.run_fake([])["ingestion"]["sources_created"], 1)

    def test_deleted_ingested_source_not_resurrected(self):
        self.run_fake([paper("A")])
        with sqlite3.connect(self.db) as connection:
            connection.execute("DELETE FROM sources")
        again = self.run_fake([paper("A")])
        self.assertEqual(again["ingestion"]["sources_created"], 0)
        self.assertEqual(list_sources(self.db), [])

    def test_identity_enrichment_reuses_existing_source(self):
        saved, _, _ = save_source(paper("A"), path=self.db)
        run = self.run_fake([paper("A", doi_url="https://doi.org/10.1234/a", year=2026)])
        self.assertEqual(run["ingestion"]["sources_reused"], 1)
        self.assertEqual(list_sources(self.db)[0]["id"], saved["id"])

    def test_processing_validation(self):
        for policy in ({}, {"save_sources": "yes", "max_new_sources": 2},
                       {"save_sources": True, "max_new_sources": False},
                       {"save_sources": True, "max_new_sources": 0}):
            with self.assertRaises(ValueError):
                mutate({"operation": "save_plan", "id": self.plan, "processing": policy}, self.db)
