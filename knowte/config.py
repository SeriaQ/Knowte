from __future__ import annotations

from pathlib import Path
from typing import Dict

CONFIG_DIR = Path.home() / ".knowte"
CONFIG_PATH = CONFIG_DIR / "config.yml"


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


def set_web_ignore_year_filter(enabled: bool, path: Path | None = None) -> Dict[str, str]:
    config = load_config(path)
    config["web_ignore_year_filter"] = "true" if enabled else "false"
    save_config(config, path)
    return config
