from __future__ import annotations

import json
import ipaddress
import math
import ast
import re
import threading
import base64
import uuid
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
    for suffix in (
        "/chat/completions", "/embeddings", "/interactions", "/responses", "/messages",
    ):
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
    extra_headers: Dict[str, str] | None = None,
    proxy_mode: str = "auto",
    proxy_url: str = "",
) -> Dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"
    headers.update(extra_headers or {})
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    body = _request_bytes(request, timeout, proxy_mode, proxy_url)
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


def _request_bytes(
    request: Request,
    timeout: int,
    proxy_mode: str = "auto",
    proxy_url: str = "",
) -> bytes:
    """Open one request with the same local/direct proxy policy as model calls."""
    try:
        hostname = (urlparse(request.full_url).hostname or "").lower()
        direct_connection = hostname in {"127.0.0.1", "localhost", "::1"}
        if not direct_connection:
            try:
                address = ipaddress.ip_address(hostname)
                direct_connection = (
                    address.is_private or address.is_loopback or address.is_link_local
                )
            except ValueError:
                pass
        mode = str(proxy_mode or "auto").strip().lower()
        if mode not in {"auto", "system", "direct", "custom"}:
            raise AIError("invalid_proxy", "Unknown proxy routing mode.")
        if mode == "direct" or (mode == "auto" and direct_connection):
            response_context = build_opener(ProxyHandler({})).open(request, timeout=timeout)
        elif mode == "custom":
            parsed_proxy = urlparse(str(proxy_url or "").strip())
            if parsed_proxy.scheme not in {"http", "https"} or not parsed_proxy.netloc:
                raise AIError("invalid_proxy", "Custom proxy must be an HTTP(S) URL.")
            response_context = build_opener(ProxyHandler({
                "http": parsed_proxy.geturl(), "https": parsed_proxy.geturl(),
            })).open(request, timeout=timeout)
        else:
            response_context = urlopen(request, timeout=timeout)
        with response_context as response:
            return response.read()
    except TimeoutError as error:
        raise AIError("timeout", f"AI service did not respond within {timeout} seconds.") from error
    except OSError as error:
        raise AIError("connection_failed", f"AI service request failed: {error}") from error


def _kimi_extract_file(
    connection: "AIConnection", document: Dict[str, Any], timeout: int,
) -> str:
    """Use Moonshot's Files API, which extracts text rather than attaching a PDF block."""
    boundary = f"knowte-{uuid.uuid4().hex}"
    filename = str(document.get("filename") or "source.pdf").replace('"', "")
    media_type = str(document.get("mime_type") or "application/pdf")
    data = bytes(document.get("data") or b"")
    chunks = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"purpose\"\r\n\r\nfile-extract\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: {media_type}\r\n\r\n".encode(),
        data,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if connection.api_key.strip():
        headers["Authorization"] = f"Bearer {connection.api_key.strip()}"
    upload_request = Request(
        _api_endpoint(connection.base_url, "files"), data=b"".join(chunks),
        headers=headers, method="POST",
    )
    raw = _request_bytes(
        upload_request, timeout, connection.proxy_mode, connection.proxy_url,
    )
    try:
        uploaded = json.loads(raw)
        file_id = str(uploaded.get("id") or "")
    except (json.JSONDecodeError, AttributeError):
        file_id = ""
    if not file_id:
        raise AIError("invalid_response", "Kimi Files API did not return a file id.")
    authorization = {"Authorization": f"Bearer {connection.api_key.strip()}"}
    try:
        content_request = Request(
            _api_endpoint(connection.base_url, f"files/{file_id}/content"),
            headers=authorization, method="GET",
        )
        return _request_bytes(
            content_request, timeout, connection.proxy_mode, connection.proxy_url,
        ).decode("utf-8", errors="replace")
    finally:
        # Extraction is transient in Knowte. Do not consume the user's Moonshot
        # file quota after the content has been placed into this request.
        try:
            delete_request = Request(
                _api_endpoint(connection.base_url, f"files/{file_id}"),
                headers=authorization, method="DELETE",
            )
            _request_bytes(
                delete_request, timeout, connection.proxy_mode, connection.proxy_url,
            )
        except AIError:
            pass


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


def _openai_response_text(response: Dict[str, Any]) -> str:
    """Extract text from the raw Responses REST payload (not an SDK helper)."""

    shortcut = response.get("output_text")
    if isinstance(shortcut, str) and shortcut.strip():
        return shortcut
    parts: List[str] = []
    for item in response.get("output") or []:
        if not isinstance(item, dict):
            continue
        text = _content_text(item)
        if text:
            parts.append(text)
    return "".join(parts)


def _google_interaction_text(response: Dict[str, Any]) -> str:
    """Extract model text from a Gemini Interactions REST response."""

    shortcut = response.get("output_text")
    if isinstance(shortcut, str) and shortcut.strip():
        return shortcut
    parts: List[str] = []
    for step in response.get("steps") or []:
        if not isinstance(step, dict) or step.get("type") != "model_output":
            continue
        text = _content_text(step)
        if text:
            parts.append(text)
    return "".join(parts)


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
        try:
            value, _ = json.JSONDecoder().raw_decode(cleaned[start:])
            return value
        except json.JSONDecodeError:
            pass
        closing = "}" if cleaned[start] == "{" else "]"
        end = cleaned.rfind(closing)
        if end <= start:
            raise AIError("invalid_model_json", "Model response contained incomplete JSON.")
        candidate = cleaned[start : end + 1]
        repaired = re.sub(r",\s*([}\]])", r"\1", _escape_json_string_controls(candidate))
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            try:
                value = ast.literal_eval(candidate)
                if isinstance(value, (dict, list)):
                    return value
            except (SyntaxError, ValueError):
                pass
        raise AIError("invalid_model_json", "Model response contained invalid JSON.")


def _escape_json_string_controls(text: str) -> str:
    """Escape literal line controls inside double-quoted JSON strings."""

    output: list[str] = []
    in_string = False
    escaped = False
    replacements = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}
    for character in text:
        if in_string and character in replacements and not escaped:
            output.append(replacements[character])
            continue
        output.append(character)
        if character == '"' and not escaped:
            in_string = not in_string
        if character == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
    return "".join(output)


@dataclass(frozen=True)
class AIConnection:
    base_url: str
    api_key: str
    proxy_mode: str = "auto"
    proxy_url: str = ""


class OpenAICompatibleClient:
    def __init__(
        self,
        connection: AIConnection,
        chat_model: str,
        embedding_connection: AIConnection,
        embedding_model: str,
        timeout: int = 45,
        enable_thinking: bool = True,
        provider: str = "openai_compatible",
        custom_recipe: Dict[str, Any] | None = None,
    ):
        self.connection = connection
        self.chat_model = (chat_model or "").strip()
        self.embedding_connection = embedding_connection
        self.embedding_model = (embedding_model or "").strip()
        self.timeout = max(5, min(int(timeout or 45), 600))
        self.enable_thinking = bool(enable_thinking)
        self.provider = (provider or "openai_compatible").strip().lower()
        self.custom_recipe = custom_recipe if isinstance(custom_recipe, dict) else {}
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
        self, system, user, temperature=None, max_tokens=None,
        extra_parameters=None, allow_text_fallback=False,
    ):
        from .stage_skills import prepare_skill_request, validate_skill_result
        fixed_system, guided_user = prepare_skill_request(system, user)
        result = self._chat_json(
            fixed_system, guided_user, temperature, max_tokens,
            extra_parameters, allow_text_fallback,
        )
        return validate_skill_result(system, result)

    def _chat_json(
        self,
        system: str,
        user: str | List[Dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        extra_parameters: Dict[str, Any] | None = None,
        allow_text_fallback: bool = False,
    ) -> Any:
        if not self.chat_model:
            raise AIError("chat_model_missing", "Language model is not configured.")
        if self.provider != "openai_compatible":
            return self._provider_json(
                system, user, temperature, max_tokens, extra_parameters,
                allow_text_fallback=allow_text_fallback,
            )
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
            proxy_mode=self.connection.proxy_mode,
            proxy_url=self.connection.proxy_url,
        )
        self._capture_usage(response, "chat")
        choices = response.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            raise AIError("invalid_response", "Language model returned no choices.")
        message = choices[0].get("message") or {}
        content = _content_text(message)
        try:
            return _extract_json(content)
        except AIError:
            if allow_text_fallback and content.strip():
                return {
                    "answer": content.strip(),
                    "_structured_output_degraded": True,
                }
            raise AIError(
                "invalid_model_json",
                "The model response could not be parsed as JSON. Nothing was saved. "
                f"Original response:\n\n{content}",
            )

    @staticmethod
    def _path(value: Any, path: str) -> Any:
        current = value
        for part in str(path or "").strip("$.").split("."):
            if not part:
                continue
            try:
                current = current[int(part)] if isinstance(current, list) else current[part]
            except (KeyError, IndexError, TypeError, ValueError) as error:
                raise AIError("invalid_response", f"Response path not found: {path}") from error
        return current

    @classmethod
    def _render_recipe(cls, value: Any, variables: Dict[str, Any]) -> Any:
        if isinstance(value, dict):
            return {key: cls._render_recipe(item, variables) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._render_recipe(item, variables) for item in value]
        if not isinstance(value, str):
            return value
        exact = re.fullmatch(r"\{\{([a-z_]+)(?:\|([a-z0-9_]+))?\}\}", value)
        if exact:
            raw = variables.get(exact.group(1), "")
            if exact.group(2) == "base64":
                raw = base64.b64encode(bytes(raw)).decode("ascii")
            return raw
        rendered = value
        for key, raw in variables.items():
            if isinstance(raw, (str, int, float)):
                rendered = rendered.replace(f"{{{{{key}}}}}", str(raw))
        return rendered

    def _custom_call(self, operation: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        recipe = self.custom_recipe.get(operation)
        if not isinstance(recipe, dict):
            raise AIError("recipe_missing", f"Custom Recipe has no {operation} operation.")
        url = self._render_recipe(recipe.get("url", ""), variables)
        if not isinstance(url, str) or not url:
            raise AIError("invalid_recipe", "Custom Recipe requires an HTTP(S) url.")
        headers = self._render_recipe(recipe.get("headers", {}), variables)
        body = self._render_recipe(recipe.get("body", {}), variables)
        if not isinstance(headers, dict) or not isinstance(body, dict):
            raise AIError("invalid_recipe", "Recipe headers and body must be JSON objects.")
        return _json_request(
            url, body, timeout=self.timeout,
            extra_headers={str(key): str(value) for key, value in headers.items()},
            proxy_mode=self.connection.proxy_mode,
            proxy_url=self.connection.proxy_url,
        )

    def _provider_json(
        self, system: str, user: str | List[Dict[str, Any]],
        temperature: float | None, max_tokens: int | None,
        extra_parameters: Dict[str, Any] | None,
        document: bytes | None = None, mime_type: str = "application/pdf",
        documents: List[Dict[str, Any]] | None = None,
        urls: List[str] | None = None,
        allow_text_fallback: bool = False,
    ) -> Any:
        user_text = user if isinstance(user, str) else json.dumps(user, ensure_ascii=False)
        native_documents = list(documents or [])
        if document is not None:
            native_documents.insert(0, {
                "data": document, "mime_type": mime_type, "filename": "source.pdf",
            })
        source_urls = [str(url).strip() for url in (urls or []) if str(url).strip()]
        variables = {
            "base_url": self.connection.base_url.rstrip("/"),
            "api_key": self.connection.api_key, "model": self.chat_model,
            "system": system, "user": user_text,
            "document": (
                bytes(native_documents[0].get("data") or b"")
                if native_documents else b""
            ),
            "mime_type": (
                str(native_documents[0].get("mime_type") or mime_type)
                if native_documents else mime_type
            ),
            "documents": [{
                "data": base64.b64encode(bytes(item.get("data") or b"")).decode("ascii"),
                "mime_type": str(item.get("mime_type") or "application/pdf"),
                "filename": str(item.get("filename") or "source.pdf"),
            } for item in native_documents],
            "urls": source_urls,
        }
        provider = self.provider
        if provider == "custom":
            operation = "document" if native_documents else "chat"
            response = self._custom_call(operation, variables)
            recipe = self.custom_recipe[operation]
            content = self._path(response, str(recipe.get("response_text") or "$.output_text"))
        elif provider == "deepseek":
            if native_documents or source_urls:
                raise AIError(
                    "recipe_missing",
                    "DeepSeek's public API does not provide native document or web-search input.",
                )
            payload = {
                "model": self.chat_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
                "thinking": {"type": "enabled" if self.enable_thinking else "disabled"},
            }
            if self.enable_thinking:
                payload["reasoning_effort"] = "high"
            if temperature is not None:
                payload["temperature"] = temperature
            if max_tokens is not None:
                payload["max_tokens"] = max(1, int(max_tokens))
            self._merge_extra_parameters(payload, extra_parameters)
            response = self._chat_completion_request(payload)
            content = self._chat_completion_text(response)
        elif provider == "qwen":
            if len(native_documents) > 1:
                raise AIError(
                    "recipe_missing",
                    "Qwen's documented PDF contract does not confirm multiple PDFs in one request.",
                )
            content_blocks: List[Dict[str, Any]] = []
            for index, item in enumerate(native_documents):
                mime = str(item.get("mime_type") or "application/pdf")
                if mime != "application/pdf":
                    raise AIError("unsupported_document", "Qwen document input currently supports PDF files.")
                content_blocks.append({
                    "type": "file",
                    "file_data": f"data:{mime};base64," + base64.b64encode(
                        bytes(item.get("data") or b"")
                    ).decode("ascii"),
                    "filename": str(item.get("filename") or f"source-{index + 1}.pdf"),
                })
            content_blocks.append({"type": "text", "text": user_text})
            payload = {
                "model": self.chat_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": content_blocks if native_documents else user},
                ],
                "response_format": {"type": "json_object"},
                "enable_thinking": self.enable_thinking,
            }
            if source_urls:
                payload["enable_search"] = True
            if temperature is not None:
                payload["temperature"] = temperature
            if max_tokens is not None:
                payload["max_tokens"] = max(1, int(max_tokens))
            self._merge_extra_parameters(payload, extra_parameters)
            response = self._chat_completion_request(payload)
            content = self._chat_completion_text(response)
        elif provider == "kimi":
            messages: List[Dict[str, Any]] = [{"role": "system", "content": system}]
            for index, item in enumerate(native_documents):
                extracted = _kimi_extract_file(self.connection, item, self.timeout)
                messages.append({
                    "role": "system",
                    "content": (
                        f"Extracted content of {str(item.get('filename') or f'source-{index + 1}')}:\n"
                        f"{extracted}"
                    ),
                })
            messages.append({"role": "user", "content": user})
            payload = {
                "model": self.chat_model,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "thinking": {"type": "disabled" if source_urls else (
                    "enabled" if self.enable_thinking else "disabled"
                )},
            }
            if source_urls:
                payload["tools"] = [{
                    "type": "builtin_function",
                    "function": {"name": "$web_search"},
                }]
            if temperature is not None:
                payload["temperature"] = temperature
            if max_tokens is not None:
                payload["max_tokens"] = max(1, int(max_tokens))
            self._merge_extra_parameters(payload, extra_parameters)
            response = self._chat_completion_request(payload)
            if source_urls:
                response = self._complete_kimi_web_search(payload, response)
            content = self._chat_completion_text(response)
        elif provider == "google":
            content_blocks: List[Dict[str, Any]] = []
            for item in native_documents:
                content_blocks.append({
                    "type": "document",
                    "data": base64.b64encode(bytes(item.get("data") or b"")).decode("ascii"),
                    "mime_type": str(item.get("mime_type") or "application/pdf"),
                })
            content_blocks.append({"type": "text", "text": user_text})
            payload: Dict[str, Any] = {
                "model": self.chat_model, "system_instruction": system,
                "input": content_blocks, "store": False,
            }
            if source_urls:
                payload["tools"] = [{"type": "url_context"}]
            response = _json_request(
                _api_endpoint(self.connection.base_url, "interactions"),
                payload,
                timeout=self.timeout,
                extra_headers={"x-goog-api-key": self.connection.api_key},
                proxy_mode=self.connection.proxy_mode,
                proxy_url=self.connection.proxy_url,
            )
            content = _google_interaction_text(response)
        elif provider == "anthropic":
            blocks: List[Dict[str, Any]] = []
            for item in native_documents:
                blocks.append({"type": "document", "source": {
                    "type": "base64",
                    "media_type": str(item.get("mime_type") or "application/pdf"),
                    "data": base64.b64encode(bytes(item.get("data") or b"")).decode("ascii"),
                }})
            blocks.append({"type": "text", "text": user_text})
            payload = {
                "model": self.chat_model, "system": system,
                "messages": [{"role": "user", "content": blocks}],
                "max_tokens": max_tokens or 3000,
            }
            if source_urls:
                payload["tools"] = [{
                    "type": "web_search_20250305", "name": "web_search",
                    "max_uses": max(1, min(len(source_urls), 6)),
                }]
            response = _json_request(
                _api_endpoint(self.connection.base_url, "messages"),
                payload,
                timeout=self.timeout,
                extra_headers={"x-api-key": self.connection.api_key, "anthropic-version": "2023-06-01"},
                proxy_mode=self.connection.proxy_mode,
                proxy_url=self.connection.proxy_url,
            )
            content = _content_text({"content": response.get("content", [])})
        elif provider == "openai":
            inputs: List[Dict[str, Any]] = []
            for index, item in enumerate(native_documents):
                inputs.append({"type": "input_file",
                               "filename": str(item.get("filename") or f"source-{index + 1}.pdf"),
                               "file_data": (
                                   f"data:{str(item.get('mime_type') or 'application/pdf')};base64,"
                                   + base64.b64encode(bytes(item.get("data") or b"")).decode("ascii")
                               )})
            inputs.append({"type": "input_text", "text": user_text})
            payload = {
                "model": self.chat_model, "instructions": system,
                "input": [{"role": "user", "content": inputs}],
            }
            if source_urls:
                payload["tools"] = [{"type": "web_search"}]
            response = _json_request(
                _api_endpoint(self.connection.base_url, "responses"),
                payload,
                self.connection.api_key, self.timeout,
                proxy_mode=self.connection.proxy_mode,
                proxy_url=self.connection.proxy_url,
            )
            content = _openai_response_text(response)
        else:
            raise AIError("unsupported_provider", f"Unsupported AI provider: {provider}")
        self._capture_usage(response, "chat")
        try:
            return _extract_json(str(content or ""))
        except AIError:
            if allow_text_fallback and str(content or "").strip():
                return {"answer": str(content).strip(), "_structured_output_degraded": True}
            raise AIError(
                "invalid_model_json",
                "The model response could not be parsed as JSON. Nothing was saved. "
                f"Original response:\n\n{str(content or '')}",
            )

    @staticmethod
    def _merge_extra_parameters(
        payload: Dict[str, Any], extra_parameters: Dict[str, Any] | None,
    ) -> None:
        reserved = {
            "model", "messages", "temperature", "max_tokens", "stream",
            "chat_template_kwargs", "tools", "response_format", "thinking",
            "enable_thinking", "enable_search",
        }
        for key, value in (extra_parameters or {}).items():
            if key not in reserved:
                payload[key] = value

    def _chat_completion_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return _json_request(
            _api_endpoint(self.connection.base_url, "chat/completions"),
            payload, self.connection.api_key, self.timeout,
            proxy_mode=self.connection.proxy_mode,
            proxy_url=self.connection.proxy_url,
        )

    @staticmethod
    def _chat_completion_text(response: Dict[str, Any]) -> str:
        choices = response.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            raise AIError("invalid_response", "Language model returned no choices.")
        return _content_text(choices[0].get("message") or {})

    def _complete_kimi_web_search(
        self, payload: Dict[str, Any], response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute Moonshot's built-in search hand-off, bounded to six tool rounds."""
        current = response
        for _ in range(6):
            choices = current.get("choices") or []
            message = choices[0].get("message") if choices and isinstance(choices[0], dict) else None
            tool_calls = message.get("tool_calls") if isinstance(message, dict) else None
            if not tool_calls:
                return current
            payload["messages"].append(message)
            for call in tool_calls:
                function = call.get("function") if isinstance(call, dict) else {}
                if not isinstance(function, dict) or function.get("name") != "$web_search":
                    raise AIError("unsupported_tool", "Kimi requested an unsupported built-in tool.")
                payload["messages"].append({
                    "role": "tool",
                    "tool_call_id": str(call.get("id") or ""),
                    "name": "$web_search",
                    "content": str(function.get("arguments") or "{}"),
                })
            self._capture_usage(current, "chat")
            current = self._chat_completion_request(payload)
        raise AIError("provider_error", "Kimi web search exceeded six tool rounds.")

    def document_json(
        self, system: str, user: str, document: bytes, mime_type: str,
        max_tokens: int = 3000,
    ) -> Any:
        from .stage_skills import prepare_skill_request, validate_skill_result
        prompt = system
        system, user = prepare_skill_request(system, user)
        if self.provider == "openai_compatible":
            raise AIError("recipe_missing", "This provider has no native document recipe.")
        result = self._provider_json(
            system, user, 0.1, max_tokens, None,
            document=document, mime_type=mime_type,
        )
        return validate_skill_result(prompt, result)

    def grounded_json(
        self, system: str, user: str,
        documents: List[Dict[str, Any]] | None = None,
        urls: List[str] | None = None,
        max_tokens: int = 3000,
    ) -> Any:
        """Send one grounded request containing zero or more documents and URLs."""
        native_documents = list(documents or [])
        source_urls = list(urls or [])
        if self.provider == "openai_compatible":
            if native_documents or source_urls:
                raise AIError(
                    "recipe_missing",
                    "This provider has no native document or web browsing recipe.",
                )
            return self.chat_json(system, user, temperature=0.1, max_tokens=max_tokens)
        from .stage_skills import prepare_skill_request, validate_skill_result
        prompt = system
        system, user = prepare_skill_request(system, user)
        result = self._provider_json(
            system, user, 0.1, max_tokens, None,
            documents=native_documents, urls=source_urls,
        )
        return validate_skill_result(prompt, result)

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
            proxy_mode=self.embedding_connection.proxy_mode,
            proxy_url=self.embedding_connection.proxy_url,
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
