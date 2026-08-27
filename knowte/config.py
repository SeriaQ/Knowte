from __future__ import annotations

from pathlib import Path
import json
from typing import Dict
from urllib.parse import urlparse

CONFIG_DIR = Path.home() / ".knowte"
CONFIG_PATH = CONFIG_DIR / "config.yml"

AI_ROLES = (
    "embedding", "intelligent_search", "copilot",
    "evidence", "claims", "wiki", "article",
)
AI_CHAT_ROLES = tuple(role for role in AI_ROLES if role != "embedding")

AI_CAPABILITIES = {
    "chat", "embeddings", "native_documents", "file_extraction",
    "web_search", "url_fetch",
}


def ai_available_capabilities(profile: dict) -> set[str]:
    """Capabilities Knowte has a documented request adapter for.

    Chat and embeddings describe the user's intended model role. Advanced
    capabilities are granted conservatively from provider, model and endpoint.
    """
    provider = str(profile.get("provider") or "openai_compatible").strip().lower()
    model = str(profile.get("model") or "").strip().lower()
    base_url = str(profile.get("base_url") or "").strip().lower()
    available = {"chat", "embeddings"}
    if provider == "deepseek":
        return {"chat"}
    if provider == "openai":
        if model.startswith(("gpt-4.1", "gpt-5", "o3", "o4")):
            available.update({"native_documents", "web_search"})
        return available
    if provider == "google":
        if model.startswith("gemini-"):
            available.update({"native_documents", "url_fetch"})
        return available
    if provider == "anthropic":
        available.discard("embeddings")
        if model.startswith("claude-"):
            available.update({"native_documents", "web_search"})
        return available
    if provider == "qwen":
        search_families = (
            "qwen3.8", "qwen3.7", "qwen3.6", "qwen3.5", "qwen3-max",
            "qwen-max", "qwen-plus", "qwen-turbo",
        )
        if model.startswith(search_families):
            available.add("web_search")
        if model == "qwen3.8-max" and "cn-beijing.maas.aliyuncs.com" in base_url:
            available.add("native_documents")
        return available
    if provider == "kimi":
        available.discard("embeddings")
        available.add("file_extraction")
        if model.startswith("kimi-k2.6"):
            available.add("web_search")
        return available
    if provider == "custom":
        # Custom is the explicit escape hatch: its JSON recipe is the contract.
        return set(AI_CAPABILITIES)
    return available


def ai_thinking_available(profile: dict) -> bool:
    provider = str(profile.get("provider") or "openai_compatible").strip().lower()
    model = str(profile.get("model") or "").strip().lower()
    if provider in {"openai_compatible", "deepseek", "custom"}:
        return True
    if provider == "qwen":
        return model.startswith(("qwen3", "qwq"))
    if provider == "kimi":
        return model.startswith("kimi-k2.6")
    return False


def _normalize_capabilities(profile: dict, requested: object) -> list[str]:
    values = [str(item) for item in requested] if isinstance(requested, list) else []
    # Migrate the previous broad labels through the adapter's proven abilities.
    if "documents" in values:
        values.extend(["native_documents", "file_extraction"])
    if "web_browsing" in values:
        values.extend(["web_search", "url_fetch"])
    available = ai_available_capabilities(profile)
    return list(dict.fromkeys(item for item in values if item in available))


def _json_object(value: str, default):
    try:
        parsed = json.loads(value or "")
    except (json.JSONDecodeError, TypeError):
        return default
    return parsed if isinstance(parsed, type(default)) else default


def ai_model_profiles(config: Dict[str, str]) -> list[dict]:
    """Return configured profiles, projecting legacy AI fields when needed."""
    stored = _json_object(config.get("ai_model_profiles", ""), [])
    if stored:
        profiles = []
        for item in stored:
            if not isinstance(item, dict):
                continue
            profile = dict(item)
            profile["capabilities"] = _normalize_capabilities(
                profile, profile.get("capabilities", [])
            )
            profile["enable_thinking"] = (
                bool(profile.get("enable_thinking", False))
                and ai_thinking_available(profile)
            )
            profiles.append(profile)
        return profiles
    base_url = str(config.get("ai_base_url") or "").strip()
    chat_model = str(config.get("ai_chat_model") or "").strip()
    profiles: list[dict] = []
    if base_url or chat_model:
        legacy_profile = {
            "id": "legacy-language", "name": chat_model or "Language model",
            "provider": config.get("ai_provider") or "openai_compatible",
            "base_url": base_url, "model": chat_model,
            "api_key": config.get("ai_api_key") or "",
            "capabilities": [],
            "enable_thinking": str(config.get("ai_enable_thinking") or "").lower()
            in {"1", "true", "yes", "on"},
            "custom_recipe": _json_object(config.get("ai_custom_recipe", ""), {}),
        }
        legacy_profile["capabilities"] = _normalize_capabilities(
            legacy_profile, ["chat", "documents", "web_browsing"]
        )
        legacy_profile["enable_thinking"] = (
            bool(legacy_profile.get("enable_thinking"))
            and ai_thinking_available(legacy_profile)
        )
        profiles.append(legacy_profile)
    embedding_model = str(config.get("ai_embedding_model") or "").strip()
    if embedding_model:
        separate = str(config.get("ai_embedding_separate_connection") or "").lower() in {
            "1", "true", "yes", "on"
        }
        profiles.append({
            "id": "legacy-embedding", "name": embedding_model,
            "provider": "openai_compatible",
            "base_url": (
                str(config.get("ai_embedding_base_url") or "").strip()
                if separate else base_url
            ),
            "model": embedding_model,
            "api_key": (
                config.get("ai_embedding_api_key") or ""
                if separate else config.get("ai_api_key") or ""
            ),
            "capabilities": ["embeddings"], "enable_thinking": False,
            "custom_recipe": {},
        })
    return profiles


def ai_role_assignments(config: Dict[str, str]) -> dict[str, str]:
    stored = _json_object(config.get("ai_role_assignments", ""), {})
    profiles = ai_model_profiles(config)
    chat_id = next((item.get("id") for item in profiles if "chat" in item.get("capabilities", [])), "")
    embedding_id = next((item.get("id") for item in profiles if "embeddings" in item.get("capabilities", [])), "")
    legacy_default = str(stored.get("default") or chat_id or "")
    roles = {role: str(stored.get(role) or "") for role in AI_ROLES}
    for role in AI_CHAT_ROLES:
        roles[role] = roles[role] or legacy_default
    roles["embedding"] = roles["embedding"] or str(embedding_id or "")
    return roles


def ai_profile_for_role(config: Dict[str, str], role: str) -> dict:
    profiles = {str(item.get("id")): item for item in ai_model_profiles(config)}
    roles = ai_role_assignments(config)
    return profiles.get(roles.get(role) or "") or {}


def _parse_yaml(text: str) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("\"")
    return data


def load_config(path: Path | None = None) -> Dict[str, str]:
    config_path = path or CONFIG_PATH
    if not config_path.exists():
        return {}
    try:
        return _parse_yaml(config_path.read_text(encoding="utf-8"))
    except OSError:
        return {}


def save_config(config: Dict[str, str], path: Path | None = None) -> None:
    config_path = path or CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, value in config.items():
        safe_value = str(value).replace("\n", " ")
        lines.append(f"{key}: {safe_value}")
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        config_path.chmod(0o600)
    except OSError:
        pass


def export_config(path: Path | None = None, redact_secrets: bool = True) -> bytes:
    config = load_config(path)
    secret_markers = ("api_key", "token", "secret", "password", "credential")

    def redact(value):
        if isinstance(value, dict):
            return {
                key: ("*" if any(marker in str(key).lower() for marker in secret_markers)
                      and item not in (None, "") else redact(item))
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [redact(item) for item in value]
        return value

    exported = dict(config)
    if redact_secrets:
        for key, value in list(exported.items()):
            if any(marker in key.lower() for marker in secret_markers):
                if value:
                    exported[key] = "*"
                continue
            if key in {"ai_model_profiles", "ai_custom_recipe"}:
                try:
                    exported[key] = json.dumps(redact(json.loads(value)), ensure_ascii=False)
                except (TypeError, json.JSONDecodeError):
                    pass
    lines = [f"{key}: {str(value).replace(chr(10), ' ')}" for key, value in exported.items()]
    return ("\n".join(lines) + "\n").encode("utf-8")


def set_email(email: str, path: Path | None = None) -> Dict[str, str]:
    config = load_config(path)
    if email:
        config["email"] = email.strip()
    else:
        config.pop("email", None)
    save_config(config, path)
    return config



def set_searxng_url(url: str, path: Path | None = None) -> Dict[str, str]:
    config = load_config(path)
    if url:
        config["searxng_url"] = url.strip()
    else:
        config.pop("searxng_url", None)
    save_config(config, path)
    return config


def set_searxng_proxy(proxy: str, path: Path | None = None) -> Dict[str, str]:
    config = load_config(path)
    if proxy:
        config["searxng_proxy"] = proxy.strip()
    else:
        config.pop("searxng_proxy", None)
    save_config(config, path)
    return config


def set_semanticscholar_key(api_key: str, path: Path | None = None) -> Dict[str, str]:
    config = load_config(path)
    if api_key:
        config["semanticscholar_api_key"] = api_key.strip()
    else:
        config.pop("semanticscholar_api_key", None)
    save_config(config, path)
    return config


def set_enabled_backends(backends: list[str], path: Path | None = None) -> Dict[str, str]:
    config = load_config(path)
    filtered = [b.strip() for b in backends if b and b.strip()]
    if filtered:
        config["enabled_backends"] = ",".join(filtered)
    else:
        config.pop("enabled_backends", None)
    save_config(config, path)
    return config


def set_max_papers(max_papers: int, path: Path | None = None) -> Dict[str, str]:
    config = load_config(path)
    if max_papers > 0:
        config["max_papers"] = str(max_papers)
    else:
        config.pop("max_papers", None)
    save_config(config, path)
    return config


def set_intelligent_max_results(
    max_results: int,
    path: Path | None = None,
) -> Dict[str, str]:
    config = load_config(path)
    if max_results > 0:
        config["intelligent_max_results"] = str(max_results)
    else:
        config.pop("intelligent_max_results", None)
    save_config(config, path)
    return config


def set_default_search_mode(
    mode: str,
    path: Path | None = None,
) -> Dict[str, str]:
    normalized = str(mode or "").strip().lower()
    if normalized not in {"keyword", "intelligent", "import"}:
        raise ValueError("default search mode must be keyword, intelligent, or import")
    config = load_config(path)
    config["default_search_mode"] = normalized
    save_config(config, path)
    return config


def set_web_ignore_year_filter(enabled: bool, path: Path | None = None) -> Dict[str, str]:
    config = load_config(path)
    config["web_ignore_year_filter"] = "true" if enabled else "false"
    save_config(config, path)
    return config


def set_ai_settings(
    settings: Dict[str, object],
    path: Path | None = None,
) -> Dict[str, str]:
    config = load_config(path)
    config.pop("ai_verify_limit", None)
    config.pop("ai_candidate_limit", None)
    text_fields = (
        "ai_provider",
        "ai_base_url",
        "ai_chat_model",
        "ai_embedding_model",
        "ai_embedding_base_url",
        "ai_copilot_instructions",
        "ai_custom_recipe",
    )
    for field in text_fields:
        value = str(settings.get(field) or "").strip()
        if value:
            config[field] = value
        else:
            config.pop(field, None)
    legacy_timeout = (
        settings.get("ai_timeout_seconds")
        or config.get("ai_timeout_seconds")
        or 45
    )
    for field, default, minimum, maximum in (
        ("ai_verify_batch_size", 5, 1, 20),
        ("ai_verify_concurrency", 1, 1, 8),
        ("ai_timeout_seconds", legacy_timeout, 5, 600),
        (
            "ai_search_timeout_seconds",
            config.get("ai_search_timeout_seconds") or legacy_timeout,
            5, 600,
        ),
        (
            "ai_stage_timeout_seconds",
            config.get("ai_stage_timeout_seconds") or legacy_timeout,
            5, 600,
        ),
        ("ai_copilot_max_tokens", 1200, 1, 32768),
    ):
        try:
            value = int(settings.get(field) or default)
        except (TypeError, ValueError):
            value = default
        config[field] = str(max(minimum, min(value, maximum)))
    try:
        temperature = float(settings.get("ai_copilot_temperature", 0.2))
    except (TypeError, ValueError):
        temperature = 0.2
    config["ai_copilot_temperature"] = str(max(0.0, min(temperature, 2.0)))
    advanced = settings.get("ai_copilot_advanced_parameters", {"top_p": 0.9})
    if not isinstance(advanced, dict):
        advanced = {"top_p": 0.9}
    config["ai_copilot_advanced_parameters"] = json.dumps(
        advanced, ensure_ascii=False, separators=(",", ":")
    )
    provider = str(settings.get("ai_provider") or "openai_compatible").strip().lower()
    if provider not in {
        "openai_compatible", "openai", "google", "anthropic",
        "deepseek", "qwen", "kimi", "custom"
    }:
        raise ValueError("unsupported AI provider")
    config["ai_provider"] = provider
    custom_recipe = settings.get("ai_custom_recipe") or {}
    if isinstance(custom_recipe, str):
        try:
            custom_recipe = json.loads(custom_recipe or "{}")
        except json.JSONDecodeError as error:
            raise ValueError("Custom Recipe must be valid JSON") from error
    if not isinstance(custom_recipe, dict):
        raise ValueError("Custom Recipe must be a JSON object")
    config["ai_custom_recipe"] = json.dumps(
        custom_recipe, ensure_ascii=False, separators=(",", ":")
    )
    config["ai_embedding_separate_connection"] = (
        "true" if settings.get("ai_embedding_separate_connection") else "false"
    )
    config["ai_enable_thinking"] = (
        "true" if settings.get("ai_enable_thinking", False) else "false"
    )
    for field in ("ai_api_key", "ai_embedding_api_key"):
        if field not in settings:
            continue
        value = str(settings.get(field) or "").strip()
        if value:
            config[field] = value
        else:
            config.pop(field, None)
    save_config(config, path)
    return config


def set_ai_model_profiles(
    profiles: object,
    roles: object,
    path: Path | None = None,
) -> Dict[str, str]:
    if not isinstance(profiles, list):
        raise ValueError("AI model profiles must be a list")
    if not isinstance(roles, dict):
        raise ValueError("AI role assignments must be an object")
    config = load_config(path)
    existing = {
        str(item.get("id")): item
        for item in ai_model_profiles(config)
        if isinstance(item, dict) and item.get("id")
    }
    normalized = []
    seen = set()
    allowed_providers = {
        "openai_compatible", "openai", "google", "anthropic",
        "deepseek", "qwen", "kimi", "custom",
    }
    allowed_capabilities = AI_CAPABILITIES | {"documents", "web_browsing"}
    for raw in profiles[:30]:
        if not isinstance(raw, dict):
            continue
        profile_id = str(raw.get("id") or "").strip()[:80]
        if not profile_id or profile_id in seen:
            raise ValueError("Every AI model profile needs a unique id")
        seen.add(profile_id)
        provider = str(raw.get("provider") or "openai_compatible").strip().lower()
        if provider not in allowed_providers:
            raise ValueError("unsupported AI provider")
        requested_capabilities = [
            str(item) for item in raw.get("capabilities", [])
            if str(item) in allowed_capabilities
        ] if isinstance(raw.get("capabilities"), list) else []
        recipe = raw.get("custom_recipe") or {}
        if not isinstance(recipe, dict):
            raise ValueError("Custom Recipe must be a JSON object")
        prior = existing.get(profile_id, {})
        proxy_mode = str(raw.get("proxy_mode") or "auto").strip().lower()
        if proxy_mode not in {"auto", "system", "direct", "custom"}:
            raise ValueError("Proxy mode must be auto, system, direct, or custom")
        proxy_url = str(raw.get("proxy_url") or "").strip()[:1000]
        if proxy_mode == "custom":
            parsed_proxy = urlparse(proxy_url)
            if parsed_proxy.scheme not in {"http", "https"} or not parsed_proxy.netloc:
                raise ValueError("Custom proxy must be an HTTP(S) URL")
            if parsed_proxy.username or parsed_proxy.password:
                raise ValueError("Proxy credentials in URLs are not supported")
        api_key = str(prior.get("api_key") or "")
        if raw.get("remove_api_key"):
            api_key = ""
        elif str(raw.get("api_key") or "").strip():
            api_key = str(raw.get("api_key") or "").strip()
        normalized_profile = {
            "id": profile_id,
            "name": str(raw.get("name") or raw.get("model") or "Model").strip()[:120],
            "provider": provider,
            "base_url": str(raw.get("base_url") or "").strip()[:1000],
            "model": str(raw.get("model") or "").strip()[:300],
            "api_key": api_key,
            "capabilities": [],
            "enable_thinking": False,
            "custom_recipe": recipe,
            "proxy_mode": proxy_mode,
            "proxy_url": proxy_url if proxy_mode == "custom" else "",
        }
        normalized_profile["capabilities"] = _normalize_capabilities(
            normalized_profile, requested_capabilities
        )
        normalized_profile["enable_thinking"] = (
            bool(raw.get("enable_thinking", False))
            and ai_thinking_available(normalized_profile)
        )
        normalized.append(normalized_profile)
    ids = {item["id"] for item in normalized}
    profile_by_id = {item["id"]: item for item in normalized}
    normalized_roles = {
        role: str(roles.get(role) or "")
        for role in AI_ROLES
        if not roles.get(role) or str(roles.get(role)) in ids
    }
    first_chat_id = next(
        (item["id"] for item in normalized if "chat" in item.get("capabilities", [])),
        "",
    )
    for role in AI_CHAT_ROLES:
        normalized_roles[role] = normalized_roles.get(role) or first_chat_id
    for role, profile_id in normalized_roles.items():
        if not profile_id:
            continue
        required = "embeddings" if role == "embedding" else "chat"
        if required not in profile_by_id[profile_id].get("capabilities", []):
            raise ValueError(f"The model assigned to {role} lacks the {required} capability")
    config["ai_model_profiles"] = json.dumps(
        normalized, ensure_ascii=False, separators=(",", ":")
    )
    config["ai_role_assignments"] = json.dumps(
        normalized_roles, ensure_ascii=False, separators=(",", ":")
    )
    save_config(config, path)
    return config
