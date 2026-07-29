from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import CONFIG_DIR

PLANS_PATH = CONFIG_DIR / "plans.json"
_LOCK = threading.Lock()
_ALLOWED_MODES = {"keyword", "intelligent"}
_ALLOWED_SOURCES = {"arxiv", "openalex", "semanticscholar", "websearch"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return payload if isinstance(payload, list) else []


def _write(path: Path, plans: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(plans, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _year(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if 1900 <= parsed <= 2100 else None


def _clean(payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    query = str(payload.get("query", existing.get("query", "") if existing else "")).strip()
    if not query:
        raise ValueError("query is required")
    query = query[:1000]
    fallback_name = query if len(query) <= 72 else query[:69].rstrip() + "..."
    name = str(payload.get("name", existing.get("name", "") if existing else "")).strip()
    mode = str(payload.get("mode", existing.get("mode", "keyword") if existing else "keyword"))
    if mode not in _ALLOWED_MODES:
        mode = "keyword"
    raw_areas = payload.get("areas", existing.get("areas", []) if existing else [])
    if not isinstance(raw_areas, list):
        raw_areas = []
    areas = [
        str(area).strip()
        for area in raw_areas
        if isinstance(area, str) and area.strip()
    ][:50]
    raw_sources = payload.get(
        "sources",
        existing.get("sources", []) if existing else [],
    )
    if not isinstance(raw_sources, list):
        raw_sources = []
    sources = [
        source
        for source in raw_sources
        if isinstance(source, str) and source in _ALLOWED_SOURCES
    ]
    if not sources:
        sources = ["arxiv", "openalex", "semanticscholar"]
    created_at = existing.get("created_at", _now()) if existing else _now()
    return {
        "id": existing.get("id", uuid4().hex) if existing else uuid4().hex,
        "name": (name or fallback_name)[:120],
        "mode": mode,
        "query": query,
        "areas": list(dict.fromkeys(areas)),
        "year_from": _year(payload.get("year_from", existing.get("year_from") if existing else None)),
        "year_to": _year(payload.get("year_to", existing.get("year_to") if existing else None)),
        "sources": list(dict.fromkeys(sources)),
        "created_at": created_at,
        "updated_at": _now(),
        "last_run_at": payload.get(
            "last_run_at",
            existing.get("last_run_at") if existing else None,
        ),
    }


def list_plans(path: Path | None = None) -> list[dict[str, Any]]:
    plans_path = path or PLANS_PATH
    with _LOCK:
        plans = _read(plans_path)
    return sorted(plans, key=lambda plan: plan.get("updated_at", ""), reverse=True)


def create_plan(payload: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    plans_path = path or PLANS_PATH
    plan = _clean(payload)
    with _LOCK:
        plans = _read(plans_path)
        plans.append(plan)
        _write(plans_path, plans)
    return plan


def update_plan(
    plan_id: str,
    payload: dict[str, Any],
    path: Path | None = None,
) -> dict[str, Any] | None:
    plans_path = path or PLANS_PATH
    with _LOCK:
        plans = _read(plans_path)
        for index, existing in enumerate(plans):
            if existing.get("id") != plan_id:
                continue
            updated = _clean(payload, existing)
            plans[index] = updated
            _write(plans_path, plans)
            return updated
    return None


def delete_plan(plan_id: str, path: Path | None = None) -> bool:
    plans_path = path or PLANS_PATH
    with _LOCK:
        plans = _read(plans_path)
        remaining = [plan for plan in plans if plan.get("id") != plan_id]
        if len(remaining) == len(plans):
            return False
        _write(plans_path, remaining)
    return True
