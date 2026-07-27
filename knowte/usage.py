from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

USAGE_DIR = Path.home() / ".knowte"
USAGE_PATH = USAGE_DIR / "usage.json"

WINDOW_SECONDS = 5 * 60
DAY_SECONDS = 24 * 60 * 60
PAPER_5MIN_LIMIT = 100
PAPER_DAY_LIMIT = 5000
WEB_5MIN_LIMIT = 10
WEB_DAY_LIMIT = 500
_USAGE_LOCK = threading.RLock()


def _empty_usage() -> Dict[str, object]:
    return {
        "day": "",
        "day_paper_count": 0,
        "recent_paper": [],
        "day_web_count": 0,
        "recent_web": [],
    }


def _load_usage() -> Dict[str, object]:
    if not USAGE_PATH.exists():
        return _empty_usage()
    try:
        data = json.loads(USAGE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_usage()
    if not isinstance(data, dict):
        return _empty_usage()
    return data


def _save_usage(data: Dict[str, object]) -> None:
    USAGE_DIR.mkdir(parents=True, exist_ok=True)
    USAGE_PATH.write_text(json.dumps(data), encoding="utf-8")


def _today_key(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def _normalize_usage(data: Dict[str, object], now: float) -> Dict[str, object]:
    day_key = _today_key(now)
    recent_paper = [t for t in data.get("recent_paper", []) if now - t <= WINDOW_SECONDS]
    recent_web = [t for t in data.get("recent_web", []) if now - t <= WINDOW_SECONDS]

    if "recent_paper" not in data and "recent" in data:
        recent_paper = [t for t in data.get("recent", []) if now - t <= WINDOW_SECONDS]
    if "day_paper_count" not in data and "day_count" in data:
        day_paper_count = int(data.get("day_count", 0) or 0)
    else:
        day_paper_count = int(data.get("day_paper_count", 0) or 0)

    day_web_count = int(data.get("day_web_count", 0) or 0)
    if data.get("day") != day_key:
        day_paper_count = 0
        day_web_count = 0

    normalized = {
        "day": day_key,
        "day_paper_count": day_paper_count,
        "recent_paper": recent_paper,
        "day_web_count": day_web_count,
        "recent_web": recent_web,
    }
    return normalized


def get_usage(now: float | None = None) -> Dict[str, int]:
    if now is None:
        now = time.time()
    with _USAGE_LOCK:
        data = _normalize_usage(_load_usage(), now)
        _save_usage(data)
        return {
            "last_5_min": len(data["recent_paper"]),
            "last_day": int(data["day_paper_count"]),
            "last_5_min_web": len(data["recent_web"]),
            "last_day_web": int(data["day_web_count"]),
        }


def record_request(backends: list[str] | None = None, now: float | None = None) -> Dict[str, int]:
    if now is None:
        now = time.time()
    with _USAGE_LOCK:
        data = _normalize_usage(_load_usage(), now)

        selected_backends = backends or []
        has_paper = any(backend != "websearch" for backend in selected_backends)
        has_web = "websearch" in selected_backends

        if has_paper:
            recent_paper = list(data["recent_paper"])
            recent_paper.append(now)
            data["recent_paper"] = recent_paper
            data["day_paper_count"] = int(data["day_paper_count"]) + 1
        if has_web:
            recent_web = list(data["recent_web"])
            recent_web.append(now)
            data["recent_web"] = recent_web
            data["day_web_count"] = int(data["day_web_count"]) + 1

        _save_usage(data)
        return {
            "last_5_min": len(data["recent_paper"]),
            "last_day": int(data["day_paper_count"]),
            "last_5_min_web": len(data["recent_web"]),
            "last_day_web": int(data["day_web_count"]),
        }


def can_request(backends: list[str] | None = None) -> Dict[str, int | bool]:
    usage = get_usage()
    paper_allowed = True
    if backends is None or any(backend != "websearch" for backend in backends):
        paper_allowed = (
            usage["last_5_min"] < PAPER_5MIN_LIMIT
            and usage["last_day"] < PAPER_DAY_LIMIT
        )
    web_allowed = True
    if backends is not None and "websearch" in backends:
        web_allowed = (
            usage["last_5_min_web"] < WEB_5MIN_LIMIT
            and usage["last_day_web"] < WEB_DAY_LIMIT
        )
    return {
        "allowed": paper_allowed,
        "allowed_paper": paper_allowed,
        "allowed_web": web_allowed,
        **usage,
    }
