from __future__ import annotations

import json
import secrets
import threading
import time
from pathlib import Path
from typing import Any
from uuid import uuid4


_LOCK = threading.RLock()
_PAIRINGS: dict[str, tuple[str, float, str]] = {}


class CompanionStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.token_path = root / "companion-token.json"
        self.inbox_path = root / "companion-inbox.json"

    @staticmethod
    def _theme(value: Any) -> str:
        return str(value) if str(value) in {"light", "dark"} else "auto"

    def create_pairing(self, theme: str = "auto") -> dict[str, Any]:
        code = f"{secrets.randbelow(1_000_000):06d}"
        nonce = secrets.token_urlsafe(12)
        expires_at = time.time() + 300
        with _LOCK:
            _PAIRINGS[str(self.root.resolve())] = (
                f"{code}:{nonce}", expires_at, self._theme(theme)
            )
        return {"code": code, "nonce": nonce, "expires_in": 300}

    def pair(self, code: str, nonce: str) -> str:
        key = str(self.root.resolve())
        with _LOCK:
            expected = _PAIRINGS.get(key)
            if not expected or expected[1] < time.time():
                raise ValueError("Pairing code expired. Generate a new code in Knowte.")
            if not secrets.compare_digest(expected[0], f"{code}:{nonce}"):
                raise ValueError("Pairing code is invalid.")
            _PAIRINGS.pop(key, None)
        token = secrets.token_urlsafe(32)
        self.root.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(
            json.dumps({"token": token, "theme": expected[2]}), encoding="utf-8"
        )
        self.token_path.chmod(0o600)
        return token

    def preferences(self) -> dict[str, str]:
        try:
            saved = json.loads(self.token_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"theme": "auto"}
        return {"theme": self._theme(saved.get("theme"))}

    def set_theme(self, theme: str) -> None:
        try:
            saved = json.loads(self.token_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        saved["theme"] = self._theme(theme)
        self.token_path.write_text(json.dumps(saved), encoding="utf-8")
        self.token_path.chmod(0o600)

    def authenticated(self, token: str) -> bool:
        try:
            saved = json.loads(self.token_path.read_text(encoding="utf-8"))["token"]
        except (OSError, KeyError, json.JSONDecodeError):
            return False
        return bool(token) and secrets.compare_digest(saved, token)

    def _read(self) -> list[dict[str, Any]]:
        try:
            value = json.loads(self.inbox_path.read_text(encoding="utf-8"))
            return value if isinstance(value, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _write(self, items: list[dict[str, Any]]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.inbox_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(self.inbox_path)

    def list(self) -> list[dict[str, Any]]:
        with _LOCK:
            return self._read()

    def add(self, payload: dict[str, Any]) -> dict[str, Any]:
        kind = str(payload.get("kind") or "source").strip().lower()
        if kind not in {"source", "text", "snapshot"}:
            raise ValueError("Unsupported Companion capture type.")
        source = payload.get("source")
        if not isinstance(source, dict) or not str(source.get("url") or "").strip():
            raise ValueError("The current page URL is required.")
        item = {
            "id": uuid4().hex,
            "kind": kind,
            "source": source,
            "quote": str(payload.get("quote") or "")[:100_000],
            "prefix": str(payload.get("prefix") or "")[:2_000],
            "suffix": str(payload.get("suffix") or "")[:2_000],
            "blocks": payload.get("blocks") if isinstance(payload.get("blocks"), list) else [],
            "image_data": str(payload.get("image_data") or ""),
            "anchor": payload.get("anchor") if isinstance(payload.get("anchor"), dict) else {},
            "created_at": time.time(),
        }
        if kind == "text" and not item["quote"].strip():
            raise ValueError("Select text before adding Text Evidence.")
        if kind == "snapshot" and not item["image_data"].startswith(
            "data:image/png;base64,"
        ):
            raise ValueError("Snapshot data is missing.")
        if len(item["image_data"]) > 14 * 1024 * 1024:
            raise ValueError("Snapshot exceeds the 10 MB Evidence limit.")
        with _LOCK:
            items = self._read()
            items.insert(0, item)
            self._write(items[:100])
        return item

    def get(self, item_id: str) -> dict[str, Any]:
        for item in self.list():
            if item.get("id") == item_id:
                return item
        raise ValueError("Companion capture not found.")

    def remove(self, item_id: str) -> bool:
        with _LOCK:
            items = self._read()
            remaining = [item for item in items if item.get("id") != item_id]
            if len(remaining) == len(items):
                return False
            self._write(remaining)
            return True
