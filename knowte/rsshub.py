"""Optional, explicitly requested local RSSHub container; never manages other containers."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import tempfile
import re
from pathlib import Path

from .searxng import _docker_process_context
from .config import load_config, save_config

IMAGE = "docker.io/diygod/rsshub:latest"
LABEL = "io.knowte.rsshub-library"
_LOCK = threading.Lock()
_JOBS = {}


def credential_path(config_path):
    return Path(config_path).parent / "rsshub-secrets.env"


def validate_credentials(payload):
    value = str(payload.get("content") or "").strip()
    if len(value) > 65536 or any(ord(c) < 32 and c not in "\n\r\t" for c in value):
        raise ValueError("Invalid environment file content (maximum 64 KiB)")
    for line in value.splitlines():
        if line.strip() and not line.lstrip().startswith("#") and not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", line):
            raise ValueError("Use KEY=value, one per line; comments start with #")
    return value


def save_credentials(config_path, payload):
    value = validate_credentials(payload)
    path = credential_path(config_path)
    if payload.get("operation") == "env_clear":
        path.unlink(missing_ok=True)
    elif value:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".rsshub-secret-", dir=path.parent)
        try:
            with os.fdopen(fd, "w") as stream:
                stream.write(value + "\n")
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
    config = load_config(config_path)
    if "rsshub_env_file" in config:
        config.pop("rsshub_env_file")
        save_config(config, config_path)


def public_credentials(config_path):
    return {"rsshub_managed_env_configured": credential_path(config_path).is_file()}


def identity(config_path):
    key = hashlib.sha256(str(Path(config_path).resolve().parent).encode()).hexdigest()[:12]
    return key, "knowte-rsshub-" + key


def _docker(args, timeout=30):
    executable, env = _docker_process_context()
    try:
        result = subprocess.run([executable, *args], env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ValueError("Docker timed out. Check Docker Desktop / Engine and retry") from None
    except OSError:
        raise ValueError("Docker is unavailable. Install and start Docker separately") from None
    if result.returncode:
        # CLI output can contain URLs and credentials. Do not return it to the browser.
        raise ValueError("Docker command failed. Check Docker, registry/network access, and local port 1200")
    return result.stdout


def _owned(config_path):
    key, name = identity(config_path)
    names = _docker(["ps", "-a", "--filter", "name=^/" + name + "$", "--format", "{{.Names}}"])
    if name not in names.splitlines():
        return None
    info = json.loads(_docker(["inspect", name]))[0]
    if (info.get("Config", {}).get("Labels") or {}).get(LABEL) != key:
        raise ValueError("Container name is already used by an unmanaged container; Knowte will not change it")
    return info


def status(config_path):
    key, name = identity(config_path)
    with _LOCK:
        job = dict(_JOBS.get(key, {}))
    if job.get("running"):
        return {**job, "container": name, "url": "http://127.0.0.1:1200"}
    info = _owned(config_path)
    return {**job, "running": False, "container": name, "url": "http://127.0.0.1:1200",
            "state": (info or {}).get("State", {}).get("Status", "not installed")}


def start_operation(config_path, operation):
    if operation not in {"setup", "start", "stop", "remove", "reboot"}:
        raise ValueError("Unknown RSSHub operation")
    key, name = identity(config_path)
    with _LOCK:
        if _JOBS.get(key, {}).get("running"):
            raise ValueError("An RSSHub operation is already running")
        _JOBS[key] = {"running": True, "message": "Checking local Docker…", "error": False}

    def progress(message):
        with _LOCK:
            _JOBS[key]["message"] = message

    def work():
        try:
            # Binding localhost only makes sense for a local Docker daemon.
            context = json.loads(_docker(["context", "inspect"]))[0]
            host = context.get("Endpoints", {}).get("docker", {}).get("Host", "")
            if os.environ.get("DOCKER_HOST") and not os.environ.get("DOCKER_CONTEXT"):
                host = os.environ["DOCKER_HOST"]
            if not host.startswith(("unix://", "npipe://")):
                raise ValueError("Managed RSSHub requires a local Docker context. Use Base URL for a remote instance")
            info = _owned(config_path)
            env_args = []
            if operation in {"setup", "reboot"}:
                secret_path = credential_path(config_path)
                if load_config(config_path).get("rsshub_env_file") and not secret_path.is_file():
                    raise ValueError("An old external environment file was configured. Copy its settings into Config → Create environment file and Save before reinstalling. Existing service was not changed")
                if secret_path.is_file():
                    env_args += ["--env-file", str(secret_path)]
            def create_args(command, container, image):
                return [command, *( ["-d"] if command == "run" else []), "--name", container, "--label", LABEL + "=" + key,
                        "--restart", "unless-stopped", "-p", "127.0.0.1:1200:1200",
                        "--log-opt", "max-size=5m", "--log-opt", "max-file=2", *env_args,
                        "-e", "NODE_ENV=production", "-e", "CACHE_TYPE=memory", "-e", "PORT=1200", image]
            if operation == "setup":
                if info:
                    raise ValueError("Already installed. Start it, or remove this managed container before setting up again")
                progress("Pulling RSSHub image… Docker keeps downloaded layers if you need to retry.")
                _docker(["pull", IMAGE], timeout=600)
                progress("Starting RSSHub on localhost:1200…")
                _docker(create_args("run", name, IMAGE), timeout=120)
            elif operation == "reboot" and info:
                progress("Applying saved environment file and rebuilding RSSHub…")
                replacement = name + "-replacement"
                # Validate the env file/image with Docker before interrupting the old service.
                _docker(create_args("create", replacement, info["Image"]), timeout=120)
                was_running = info.get("State", {}).get("Running", False)
                try:
                    if was_running:
                        _docker(["stop", name])
                        _docker(["start", replacement], timeout=120)
                        state = json.loads(_docker(["inspect", replacement]))[0].get("State", {})
                        if not state.get("Running"):
                            raise ValueError("Replacement RSSHub did not start")
                except Exception:
                    _docker(["rm", "-f", replacement])
                    if was_running:
                        _docker(["start", name])
                    raise ValueError("RSSHub rebuild failed. Previous container was retained; check its status before retrying") from None
                _docker(["rm", name])
                _docker(["rename", replacement, name])
            elif info:
                _docker(["rm", "-f", name] if operation == "remove" else [operation, name])
            else:
                raise ValueError("No managed RSSHub container exists for this library")
            progress("Done. Test a Channel separately to verify its feed is accessible.")
        except Exception as error:
            with _LOCK:
                _JOBS[key].update(error=True, message=str(error) if isinstance(error, ValueError) else "Docker operation failed; check Docker installation and permissions")
        finally:
            with _LOCK:
                _JOBS[key]["running"] = False

    threading.Thread(target=work, daemon=True, name="knowte-rsshub").start()
    return {"running": True, "container": name, "message": "Checking local Docker…"}
