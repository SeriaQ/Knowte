import json
import tempfile
import unittest
from pathlib import Path

from knowte.plans import create_plan, delete_plan, list_plans, update_plan


class PlanStorageTests(unittest.TestCase):
    def test_plan_round_trip_keeps_behavior_but_not_secrets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "plans.json"
            created = create_plan(
                {
                    "name": "AlphaGo follow-up",
                    "mode": "intelligent",
                    "query": "work that extends AlphaGo beyond board games",
                    "areas": ["ai.rl", "ai.ml"],
                    "year_from": 2015,
                    "sources": ["arxiv", "websearch"],
                    "semanticscholar_api_key": "must-not-be-saved",
                    "searxng_url": "http://secret-endpoint.test/search",
                },
                path,
            )

            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(stored[0]["id"], created["id"])
            self.assertEqual(stored[0]["mode"], "intelligent")
            self.assertEqual(stored[0]["sources"], ["arxiv", "websearch"])
            self.assertNotIn("semanticscholar_api_key", stored[0])
            self.assertNotIn("searxng_url", stored[0])
            self.assertEqual(list_plans(path)[0]["query"], created["query"])

    def test_update_preserves_unspecified_conditions_and_delete_removes_plan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "plans.json"
            created = create_plan(
                {
                    "query": "semantic research retrieval",
                    "areas": ["ai.ir"],
                    "year_from": 2020,
                    "sources": ["openalex"],
                },
                path,
            )
            updated = update_plan(created["id"], {"name": "Retrieval plan"}, path)

            self.assertEqual(updated["name"], "Retrieval plan")
            self.assertEqual(updated["areas"], ["ai.ir"])
            self.assertEqual(updated["year_from"], 2020)
            self.assertEqual(updated["sources"], ["openalex"])
            self.assertTrue(delete_plan(created["id"], path))
            self.assertEqual(list_plans(path), [])

    def test_invalid_collection_fields_are_safely_normalized(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "plans.json"
            created = create_plan(
                {
                    "query": "test",
                    "areas": "ai.rl",
                    "sources": {"websearch": True},
                },
                path,
            )

            self.assertEqual(created["areas"], [])
            self.assertEqual(
                created["sources"],
                ["arxiv", "openalex", "semanticscholar"],
            )


if __name__ == "__main__":
    unittest.main()
