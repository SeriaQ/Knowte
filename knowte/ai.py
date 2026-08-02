from __future__ import annotations

import json
import ipaddress
import math
import threading
from dataclasses import dataclass
from typing import Any, Dict, List
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener, urlopen


class AIError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _api_endpoint(base_url: str, resource: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    for suffix in ("/chat/completions", "/embeddings"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    parsed = urlparse(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AIError("invalid_base_url", "Base URL must be an HTTP(S) URL.")
    return f"{base}/{resource.lstrip('/')}"


def _json_request(
    url: str,
    payload: Dict[str, Any],
    api_key: str = "",
    timeout: int = 45,
) -> Dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        hostname = (urlparse(url).hostname or "").lower()
        direct_connection = hostname in {"127.0.0.1", "localhost", "::1"}
        if not direct_connection:
            try:
                address = ipaddress.ip_address(hostname)
                direct_connection = (
                    address.is_private or address.is_loopback or address.is_link_local
                )
            except ValueError:
                pass
        response_context = (
            build_opener(ProxyHandler({})).open(request, timeout=timeout)
            if direct_connection
            else urlopen(request, timeout=timeout)
        )
        with response_context as response:
            body = response.read()
    except TimeoutError as error:
        raise AIError(
            "timeout",
            f"AI service did not respond within {timeout} seconds.",
        ) from error
    except OSError as error:
        raise AIError("connection_failed", f"AI service request failed: {error}") from error
    try:
        decoded = json.loads(body)
    except json.JSONDecodeError as error:
        raise AIError("invalid_response", "AI service returned invalid JSON.") from error
    if not isinstance(decoded, dict):
        raise AIError("invalid_response", "AI service returned an unexpected payload.")
    if decoded.get("error"):
        detail = decoded["error"]
        if isinstance(detail, dict):
            detail = detail.get("message") or detail.get("type") or "unknown error"
        raise AIError("provider_error", f"AI service error: {detail}")
    return decoded


def _content_text(message: Dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(part.get("text") or "")
            for part in content
            if isinstance(part, dict)
        )
    return str(content or "")


def _extract_json(text: str) -> Any:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start_candidates = [pos for pos in (cleaned.find("{"), cleaned.find("[")) if pos >= 0]
        if not start_candidates:
            raise AIError("invalid_model_json", "Model response did not contain JSON.")
        start = min(start_candidates)
        closing = "}" if cleaned[start] == "{" else "]"
        end = cleaned.rfind(closing)
        if end <= start:
            raise AIError("invalid_model_json", "Model response contained incomplete JSON.")
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as error:
            raise AIError("invalid_model_json", "Model response contained invalid JSON.") from error


@dataclass(frozen=True)
class AIConnection:
    base_url: str
    api_key: str


class OpenAICompatibleClient:
    def __init__(
        self,
        connection: AIConnection,
        chat_model: str,
        embedding_connection: AIConnection,
        embedding_model: str,
        timeout: int = 45,
        enable_thinking: bool = True,
    ):
        self.connection = connection
        self.chat_model = (chat_model or "").strip()
        self.embedding_connection = embedding_connection
        self.embedding_model = (embedding_model or "").strip()
        self.timeout = max(5, min(int(timeout or 45), 600))
        self.enable_thinking = bool(enable_thinking)
        self.chat_requests = 0
        self.chat_tokens = 0
        self.embedding_requests = 0
        self.embedding_tokens = 0
        self._usage_lock = threading.Lock()

    def _capture_usage(self, response: Dict[str, Any], channel: str) -> None:
        usage = response.get("usage") or {}
        token_count = 0
        if isinstance(usage, dict):
            token_count = max(
                0,
                int(
                    usage.get(
                        "total_tokens",
                        int(
                            usage.get(
                                "prompt_tokens",
                                usage.get("input_tokens", 0),
                            )
                            or 0
                        )
                        + int(
                            usage.get(
                                "completion_tokens",
                                usage.get("output_tokens", 0),
                            )
                            or 0
                        ),
                    )
                    or 0
                ),
            )
        with self._usage_lock:
            if channel == "embedding":
                self.embedding_requests += 1
                self.embedding_tokens += token_count
            else:
                self.chat_requests += 1
                self.chat_tokens += token_count

    def usage_snapshot(self) -> Dict[str, int]:
        with self._usage_lock:
            return {
                "chat_requests": self.chat_requests,
                "chat_tokens": self.chat_tokens,
                "embedding_requests": self.embedding_requests,
                "embedding_tokens": self.embedding_tokens,
            }

    def chat_json(
        self,
        system: str,
        user: str | List[Dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        extra_parameters: Dict[str, Any] | None = None,
    ) -> Any:
        if not self.chat_model:
            raise AIError("chat_model_missing", "Language model is not configured.")
        payload = {
            "model": self.chat_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max(1, int(max_tokens))
        reserved = {"model", "messages", "temperature", "max_tokens", "stream", "chat_template_kwargs"}
        for key, value in (extra_parameters or {}).items():
            if key not in reserved:
                payload[key] = value
        if not self.enable_thinking:
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        response = _json_request(
            _api_endpoint(self.connection.base_url, "chat/completions"),
            payload,
            self.connection.api_key,
            self.timeout,
        )
        self._capture_usage(response, "chat")
        choices = response.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            raise AIError("invalid_response", "Language model returned no choices.")
        message = choices[0].get("message") or {}
        return _extract_json(_content_text(message))

    def embeddings(self, texts: List[str]) -> List[List[float]]:
        if not self.embedding_model:
            raise AIError("embedding_model_missing", "Embedding model is not configured.")
        if not texts:
            return []
        response = _json_request(
            _api_endpoint(self.embedding_connection.base_url, "embeddings"),
            {"model": self.embedding_model, "input": texts},
            self.embedding_connection.api_key,
            self.timeout,
        )
        self._capture_usage(response, "embedding")
        data = response.get("data") or []
        ordered = sorted(
            (item for item in data if isinstance(item, dict)),
            key=lambda item: int(item.get("index", 0)),
        )
        vectors = [item.get("embedding") for item in ordered]
        if len(vectors) != len(texts) or not all(isinstance(vector, list) for vector in vectors):
            raise AIError("invalid_response", "Embedding service returned incomplete vectors.")
        return [[float(value) for value in vector] for vector in vectors]


def cosine_similarity(left: List[float], right: List[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)
