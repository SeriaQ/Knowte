import io
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from knowte.automation import catalog, mutate, search_settings


class AutomationDefinitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "knowte.db"
        self.legacy = self.db.with_name("plans.json")

    def write(self, **payload):
        return mutate(payload, self.db, self.legacy)

    def action(self, query="RL"):
        return self.write(operation="save_action", name=query, config={"query": query})["saved_id"]

    def test_migration_idempotent_atomic_preserves_original_and_modes(self):
        original = json.dumps([{"name": "RL", "query": "RL", "mode": "intelligent",
                                "search_actions": [{"query": "policy gradient", "target": "academic"}],
                                "year_from": 2020, "sources": ["arxiv"], "api_key": "SECRET"}])
        self.legacy.write_text(original)
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _: catalog(self.db, self.legacy), range(4)))
        self.assertTrue(all(len(item["plans"]) == 1 for item in results))
        self.assertEqual(len({item["plans"][0]["id"] for item in results}), 1)
        action = results[0]["actions"][0]
        self.assertEqual(action["config"]["mode"], "intelligent")
        self.assertEqual(action["config"]["search_actions"][0]["query"], "policy gradient")
        self.assertNotIn("SECRET", json.dumps(results))
        self.assertEqual(self.legacy.read_text(), original)
        plan_id = results[0]["plans"][0]["id"]
        self.write(operation="delete_plan", id=plan_id)
        self.assertEqual(catalog(self.db, self.legacy)["plans"], [])

    def test_malformed_migration_never_drops_partial_entries(self):
        self.legacy.write_text(json.dumps([{"query": "valid"}, {"name": "broken"}]))
        with self.assertRaisesRegex(ValueError, "Nothing was migrated"):
            catalog(self.db, self.legacy)
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM actions").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT count(*) FROM automation_meta").fetchone()[0], 0)
        self.legacy.write_text("invalid json")
        with self.assertRaisesRegex(ValueError, "original file is unchanged"):
            catalog(self.db, self.legacy)
        self.legacy.write_text('[{"query":"repaired"}]')
        self.assertEqual(len(catalog(self.db, self.legacy)["plans"]), 1)

    def test_reuse_and_reorder_preserve_independent_execution_state(self):
        a, b = self.action(), self.action("LLM")
        first = self.write(operation="save_plan", name="Daily", action_ids=[a, b])["saved_id"]
        second = self.write(operation="save_plan", name="Weekly", action_ids=[a])["saved_id"]
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE plan_actions SET execution_state = ? WHERE plan_id = ? AND action_id = ?",
                               ('{"checkpoint":"A"}', first, a))
            old_id = connection.execute("SELECT id FROM plan_actions WHERE plan_id = ? AND action_id = ?", (first, a)).fetchone()[0]
        self.write(operation="save_plan", id=first, name="Renamed", action_ids=[b, a])
        with sqlite3.connect(self.db) as connection:
            own = connection.execute("SELECT id, execution_state, position FROM plan_actions WHERE plan_id = ? AND action_id = ?", (first, a)).fetchone()
            other = connection.execute("SELECT id, execution_state FROM plan_actions WHERE plan_id = ?", (second,)).fetchone()
        self.assertEqual(own, (old_id, '{"checkpoint":"A"}', 1))
        self.assertNotEqual(other[0], old_id)
        self.assertEqual(other[1], "{}")
        self.assertEqual(len(next(item for item in catalog(self.db)["actions"] if item["id"] == a)["used_by"]), 2)

    def test_action_update_shared_versioned_and_safe_delete(self):
        a = self.action()
        plan = self.write(operation="save_plan", name="Plan", action_ids=[a])["saved_id"]
        result = self.write(operation="save_action", id=a, version=1, name="Changed")
        self.assertEqual(result["actions"][0]["version"], 2)
        self.assertEqual(result["plans"][0]["actions"][0]["action_id"], a)
        with self.assertRaisesRegex(ValueError, "changed"):
            self.write(operation="save_action", id=a, version=1, name="Lost update")
        with self.assertRaisesRegex(ValueError, "Remove this Action"):
            self.write(operation="delete_action", id=a)
        self.write(operation="delete_plan", id=plan)
        self.assertEqual(len(catalog(self.db)["actions"]), 1)
        self.write(operation="delete_action", id=a)
        self.assertFalse(catalog(self.db)["actions"])

    def test_empty_plan_can_keep_schedule_but_not_enable_it(self):
        plan = self.write(operation="save_plan", name="Draft", action_ids=[], enabled=False,
                          schedule={"type": "daily", "time": "08:00", "timezone": "UTC"})["saved_id"]
        with self.assertRaisesRegex(ValueError, "Add an Action"):
            self.write(operation="save_plan", id=plan, enabled=True)
        action = self.action()
        self.write(operation="save_plan", id=plan, action_ids=[action], enabled=True)
        self.write(operation="save_plan", id=plan, action_ids=[], enabled=False)
        saved = next(p for p in catalog(self.db)["plans"] if p["id"] == plan)
        self.assertFalse(saved["enabled"])
        self.assertEqual(saved["schedule"]["type"], "daily")

    def test_evidence_focus_is_optional_but_model_is_required(self):
        policy = {"save_sources": True, "max_new_sources": 20,
                  "evidence": {"enabled": True, "focus": "", "model_profile_id": "model"}}
        result = self.write(operation="save_plan", name="Optional focus", enabled=False, action_ids=[], processing=policy)
        self.assertEqual(result["plans"][0]["processing"]["evidence"]["focus"], "")
        policy["claims"] = {"enabled": True, "focus": "", "model_profile_id": "model"}
        result = self.write(operation="save_plan", name="Optional claim focus", enabled=False, action_ids=[], processing=policy)
        self.assertEqual(result["plans"][-1]["processing"].get("claims", {}).get("focus", ""), "")
        policy["claims"]["model_profile_id"] = ""
        with self.assertRaisesRegex(ValueError, "explicit model"):
            self.write(operation="save_plan", name="Missing claim model", enabled=False, action_ids=[], processing=policy)
        policy.pop("claims")
        policy["evidence"]["model_profile_id"] = ""
        with self.assertRaisesRegex(ValueError, "explicit model"):
            self.write(operation="save_plan", name="Missing model", enabled=False, action_ids=[], processing=policy)

    def test_save_and_attach_atomic_and_secrets_not_copied(self):
        with self.assertRaisesRegex(ValueError, "Plan not found"):
            self.write(operation="save_action", name="Not saved", config={"query": "RL"}, plan_id="missing")
        self.assertFalse(catalog(self.db)["actions"])
        p = self.write(operation="save_plan", name="Empty")["saved_id"]
        result = self.write(operation="save_action", name="Search", plan_id=p, config={
            "query": "RL", "max_papers": 200, "intelligent_max_results": 40,
            "model_profile_id": "local", "api_key": "SECRET", "base_url": "SECRET",
            "profiles": [{"api_key": "SECRET"}], "areas": ["ai.rl"],
        })
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertEqual(result["actions"][0]["config"]["max_papers"], 200)
        self.assertEqual(result["plans"][0]["actions"][0]["action_id"], result["saved_id"])

    def test_validation_rolls_back(self):
        a = self.action()
        for payload in ({"action_ids": [a, a]}, {"action_ids": ["missing"]},
                        {"enabled": "false"}, {"schedule": {"type": "daily"}}):
            with self.assertRaises(ValueError):
                self.write(operation="save_plan", name="Invalid", **payload)
        self.assertFalse(catalog(self.db)["plans"])
        with self.assertRaises(ValueError):
            self.write(operation="save_action", config={"query": "RL", "max_papers": 0})

    def test_library_isolation(self):
        self.action()
        other = self.db.with_name("other.db")
        self.assertFalse(catalog(other)["actions"])

    def test_search_settings_allowlist_and_limits(self):
        self.assertEqual(search_settings({"max_papers": 250, "ai_verify_batch_size": 8,
            "ai_verify_concurrency": 2, "ai_search_timeout_seconds": 120,
            "api_key": "SECRET", "base_url": "SECRET"}),
            {"max_papers": 250, "ai_verify_batch_size": 8, "ai_verify_concurrency": 2,
             "ai_search_timeout_seconds": 120})
        for settings in ({"intelligent_max_results": 101}, {"ai_verify_batch_size": True},
                         {"ai_verify_concurrency": 9}):
            with self.assertRaises(ValueError):
                search_settings(settings)

    def test_http_dispatch_without_socket(self):
        from knowte.server import KnowteHandler
        def request(payload=None):
            handler = KnowteHandler.__new__(KnowteHandler)
            handler.path = "/api/plans"
            handler.knowledge_db_path = self.db
            handler.plans_path = self.legacy
            handler.wfile = io.BytesIO()
            statuses = []
            handler.send_response = statuses.append
            handler.send_header = lambda *args: None
            handler.end_headers = lambda: None
            handler._send_json = lambda value, status=200: (statuses.append(status), handler.wfile.write(json.dumps(value).encode()))
            if payload is not None:
                body = json.dumps(payload).encode()
                handler.headers = {"Content-Length": str(len(body))}
                handler.rfile = io.BytesIO(body)
                handler.do_POST()
            else:
                handler.do_GET()
            return statuses[0], json.loads(handler.wfile.getvalue())
        status, data = request({"operation": "save_action", "config": {"query": "RL"}})
        self.assertEqual(status, 201)
        self.assertEqual(len(data["actions"]), 1)
        status, legacy = request({"query": "Old client", "api_key": "SECRET"})
        self.assertEqual(status, 201)
        status, listing = request()
        self.assertEqual(listing["plans"][0]["id"], legacy["id"])
        self.assertNotIn("SECRET", json.dumps(listing))


if __name__ == "__main__":
    unittest.main()
