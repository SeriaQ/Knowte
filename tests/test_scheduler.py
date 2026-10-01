import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from knowte.automation import catalog, mutate
from knowte.scheduler import clean_schedule, next_due, tick


def utc(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


class ScheduleTimeTests(unittest.TestCase):
    def test_server_lifecycle_starts_and_stops_scheduler_without_socket(self):
        from knowte.server import KnowteTCPServer
        server = KnowteTCPServer.__new__(KnowteTCPServer)
        server.plan_scheduler = Mock()
        with patch("socketserver.ThreadingTCPServer.serve_forever", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                server.serve_forever()
        server.plan_scheduler.start.assert_called_once()
        server.plan_scheduler.stop.assert_called_once()

    def test_validation(self):
        for value in ({"type": "unknown"}, {"type": "interval", "hours": 0},
                      {"type": "daily", "time": "28:00"},
                      {"type": "weekly", "time": "08:00", "weekday": 7},
                      {"type": "daily", "time": "08:00", "timezone": "not/a/zone"}):
            with self.assertRaises(ValueError):
                clean_schedule(value)

    def test_daily_weekly_and_interval(self):
        daily = clean_schedule({"type": "daily", "time": "08:00", "timezone": "Asia/Shanghai"})
        self.assertEqual(next_due(daily, utc("2026-09-26T00:00:00")), utc("2026-09-27T00:00:00"))
        weekly = clean_schedule({"type": "weekly", "time": "08:00", "weekday": 0, "timezone": "Asia/Shanghai"})
        self.assertEqual(next_due(weekly, utc("2026-09-26T00:00:00")), utc("2026-09-28T00:00:00"))
        interval = clean_schedule({"type": "interval", "hours": 6})
        self.assertEqual(next_due(interval, utc("2026-09-29T03:00:00"), utc("2026-09-26T00:00:00")), utc("2026-09-29T06:00:00"))

    def test_dst_gap_shifts_and_fold_runs_once(self):
        spring = {"type": "daily", "time": "02:30", "timezone": "America/New_York"}
        self.assertEqual(next_due(spring, utc("2026-03-08T05:00:00")), utc("2026-03-08T07:30:00"))
        fall = {"type": "daily", "time": "01:30", "timezone": "America/New_York"}
        self.assertEqual(next_due(fall, utc("2026-11-01T04:00:00")), utc("2026-11-01T05:30:00"))
        self.assertEqual(next_due(fall, utc("2026-11-01T05:30:00")), utc("2026-11-02T06:30:00"))


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "knowte.db"
        self.config = self.db.with_name("config.yml")
        action = mutate({"operation": "save_action", "config": {"query": "RL"}}, self.db)["saved_id"]
        self.plan = mutate({"operation": "save_plan", "name": "Daily", "action_ids": [action],
            "schedule": {"type": "daily", "time": "08:00", "timezone": "UTC"}}, self.db)["saved_id"]
        self.due("2026-09-26T08:00:00+00:00")
        self.launched = []

    def due(self, value):
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE plan_schedule_state SET next_due_at = ? WHERE plan_id = ?", (value, self.plan))

    def launch(self, run, *args):
        self.launched.append(run)
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE plan_runs SET status = 'running' WHERE id = ?", (run,))

    def run_tick(self, date):
        return tick(self.db, self.config, now=utc(date), launch=self.launch)

    def finish(self):
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE plan_runs SET status = 'completed' WHERE status = 'running'")

    def test_due_and_no_duplicate_tick(self):
        self.assertEqual(self.run_tick("2026-09-26T07:59:59"), [])
        self.assertEqual(len(self.run_tick("2026-09-26T08:00:00")), 1)
        self.assertEqual(self.run_tick("2026-09-26T08:00:01"), [])
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT trigger FROM plan_runs").fetchone()[0], "scheduled")

    def test_missed_days_catch_up_once(self):
        self.run_tick("2026-09-30T10:00:00")
        self.finish()
        self.run_tick("2026-09-30T10:00:10")
        self.assertEqual(len(self.launched), 1)
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT trigger FROM plan_runs").fetchone()[0], "catch_up")
        self.assertEqual(catalog(self.db)["plans"][0]["next_run"], "2026-10-01T08:00:00+00:00")

    def test_long_run_coalesces_many_triggers_to_one(self):
        self.run_tick("2026-09-26T08:00:00")
        self.run_tick("2026-09-27T08:00:00")
        self.run_tick("2026-09-28T08:00:00")
        self.assertEqual(len(self.launched), 1)
        self.assertTrue(catalog(self.db)["plans"][0]["run_pending"])
        self.finish()
        self.run_tick("2026-09-28T09:00:00")
        self.finish()
        self.run_tick("2026-09-28T09:00:10")
        self.assertEqual(len(self.launched), 2)

    def test_disabled_and_manual_do_not_schedule(self):
        mutate({"operation": "save_plan", "id": self.plan, "enabled": False}, self.db)
        self.run_tick("2027-09-30T08:00:00")
        self.assertFalse(self.launched)
        mutate({"operation": "save_plan", "id": self.plan, "enabled": True, "schedule": {"type": "manual"}}, self.db)
        self.run_tick("2027-09-30T08:00:00")
        self.assertFalse(self.launched)

    def test_rename_preserves_due_and_schedule(self):
        mutate({"operation": "save_plan", "id": self.plan, "name": "Renamed"}, self.db)
        plan = catalog(self.db)["plans"][0]
        self.assertEqual(plan["next_run"], "2026-09-26T08:00:00+00:00")
        self.assertEqual(plan["schedule"]["type"], "daily")

    def test_pause_during_run_clears_coalesced_trigger_without_stopping_run(self):
        self.run_tick("2026-09-26T08:00:00")
        self.run_tick("2026-09-27T08:00:00")
        mutate({"operation": "save_plan", "id": self.plan, "enabled": False}, self.db)
        plan = catalog(self.db)["plans"][0]
        self.assertFalse(plan["run_pending"])
        self.assertIsNone(plan["next_run"])
        self.assertEqual(plan["last_run"]["status"], "running")
        self.finish()
        self.run_tick("2026-09-28T08:00:00")
        self.assertEqual(len(self.launched), 1)

    def test_dead_scheduled_run_requeues_once(self):
        self.run_tick("2026-09-26T08:00:00")
        with patch("knowte.plan_runs.os.kill", side_effect=ProcessLookupError):
            self.run_tick("2026-09-26T09:00:00")
        self.assertEqual(len(self.launched), 2)
        self.assertFalse(catalog(self.db)["plans"][0]["run_pending"])

    def test_launch_interruption_keeps_durable_job_for_next_tick(self):
        def interrupt(*args):
            raise RuntimeError("Interrupted before thread start")
        with self.assertRaises(RuntimeError):
            tick(self.db, self.config, now=utc("2026-09-26T08:00:00"), launch=interrupt)
        self.run_tick("2026-09-26T08:00:10")
        self.assertEqual(len(self.launched), 1)
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM plan_runs").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
