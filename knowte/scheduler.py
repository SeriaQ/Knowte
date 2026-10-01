"""Local process scheduler with durable due times and one coalesced pending tick."""
from __future__ import annotations

import logging
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def clean_schedule(value):
    if not isinstance(value, dict):
        raise ValueError("Schedule must be an object")
    kind = value.get("type", "manual")
    if kind == "manual":
        return {"type": "manual"}
    if kind not in {"interval", "daily", "weekly"}:
        raise ValueError("Choose Manual, Every N hours, Daily or Weekly")
    zone = str(value.get("timezone") or "UTC")
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("Unknown timezone. Use an IANA name such as Asia/Shanghai or UTC; install tzdata if timezone data is unavailable.") from None
    result = {"type": kind, "timezone": zone}
    if kind == "interval":
        hours = value.get("hours")
        if isinstance(hours, bool) or not isinstance(hours, int) or not 1 <= hours <= 8760:
            raise ValueError("Interval must be 1–8760 whole hours")
        result["hours"] = hours
    else:
        value_time = str(value.get("time") or "")
        try:
            parsed = datetime.strptime(value_time, "%H:%M")
        except ValueError:
            raise ValueError("Choose a valid local time (HH:MM)") from None
        result["time"] = parsed.strftime("%H:%M")
        if kind == "weekly":
            weekday = value.get("weekday")
            if isinstance(weekday, bool) or not isinstance(weekday, int) or not 0 <= weekday <= 6:
                raise ValueError("Choose a weekday")
            result["weekday"] = weekday
    return result


def next_due(schedule, after, previous=None):
    """Return a strictly future UTC occurrence; daily/weekly follow wall time."""
    if schedule["type"] == "manual":
        return None
    after = after.astimezone(timezone.utc)
    if schedule["type"] == "interval":
        step = timedelta(hours=schedule["hours"])
        anchor = previous or after
        count = max(1, (after - anchor) // step + 1)
        return anchor + step * count
    zone = ZoneInfo(schedule["timezone"])
    local = after.astimezone(zone)
    hour, minute = map(int, schedule["time"].split(":"))
    for offset in range(9):
        day = local.date() + timedelta(days=offset)
        if schedule["type"] == "weekly" and day.weekday() != schedule["weekday"]:
            continue
        candidate = datetime(day.year, day.month, day.day, hour, minute, tzinfo=zone, fold=0)
        # Nonexistent spring-forward time shifts forward through the DST gap.
        # Fall-back chooses the first occurrence, never both copies of the hour.
        candidate = candidate.astimezone(timezone.utc)
        if candidate > after:
            return candidate
    raise ValueError("Cannot find the next scheduled occurrence")


def tick(path, config_path, *, now=None, launch=None):
    from .automation import _database
    from .plan_runs import queue_run, launch_run, recover_interrupted
    now = now or datetime.now(timezone.utc)
    launch = launch or launch_run
    recover_interrupted(path)
    ready = []
    with _database(path) as connection:
        rows = connection.execute("""SELECT s.*, p.schedule_json FROM plan_schedule_state s
            JOIN plans p ON p.id = s.plan_id WHERE p.enabled = 1""").fetchall()
        for row in rows:
            schedule = json.loads(row["schedule_json"])
            if schedule["type"] == "manual":
                continue
            due = datetime.fromisoformat(row["next_due_at"]) if row["next_due_at"] else None
            is_due = due is not None and due <= now
            if not is_due and not row["pending"]:
                continue
            active = connection.execute("SELECT 1 FROM plan_runs WHERE plan_id = ? AND status IN ('queued', 'running')", (row["plan_id"],)).fetchone()
            future = next_due(schedule, now, due).isoformat() if is_due else row["next_due_at"]
            if active:
                connection.execute("UPDATE plan_schedule_state SET pending = 1, next_due_at = ? WHERE plan_id = ?", (future, row["plan_id"]))
                continue
            trigger = "catch_up" if row["pending"] or (due and now - due > timedelta(seconds=30)) else "scheduled"
            run_id, created = queue_run(row["plan_id"], path, trigger=trigger, connection=connection)
            connection.execute("UPDATE plan_schedule_state SET pending = 0, next_due_at = ? WHERE plan_id = ?", (future, row["plan_id"]))
            if created:
                ready.append(run_id)
        # A queued job may have survived a thread-launch failure/interruption in
        # this process. Execution claims queued -> running atomically.
        ready.extend(row[0] for row in connection.execute("SELECT id FROM plan_runs WHERE status = 'queued' AND owner_pid = ?", (os.getpid(),)))
    ready = list(dict.fromkeys(ready))
    for run_id in ready:
        try:
            launch(run_id, path, config_path)
        except ValueError:
            logging.getLogger(__name__).warning("Could not launch Plan Run %s", run_id)
    return ready


class LocalScheduler:
    def __init__(self, path, config_path):
        self.path = path
        self.config_path = config_path
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, name="knowte-scheduler", daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=2)

    def _run(self):
        while not self.stop_event.is_set():
            try:
                tick(self.path, self.config_path)
            except Exception as error:
                logging.getLogger(__name__).warning("Scheduler tick failed (%s); retrying", type(error).__name__)
            self.stop_event.wait(10)
