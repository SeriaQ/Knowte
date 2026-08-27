from __future__ import annotations

import json
import os
import queue
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse, urlsplit, urlunsplit
from urllib.request import ProxyHandler, build_opener

MANAGED_DIR = Path.home() / ".knowte" / "searxng"
CONFIG_DIR = MANAGED_DIR / "config"
SETTINGS_PATH = CONFIG_DIR / "settings.yml"
COMPOSE_PATH = MANAGED_DIR / "compose.yml"
METADATA_PATH = MANAGED_DIR / "managed.json"
CONTAINER_NAME = "knowte-searxng"
MANAGED_LABEL = "io.knowte.managed"
DEFAULT_PORT = 8888
MAX_PORT = 8898
SEARCH_URL = "http://127.0.0.1:8888/search"
IMAGE_PULL_TIMEOUT = 10 * 60
SEARXNG_IMAGES = (
    "docker.io/searxng/searxng:latest",
    "ghcr.io/searxng/searxng:latest",
)
CONTAINER_START_TIMEOUT = 2 * 60
_MANAGER_LOCK = threading.RLock()
_JOBS: Dict[str, Dict[str, object]] = {}
_JOBS_LOCK = threading.RLock()
_JOB_PHASE_MESSAGES = {
    "queued": "Task queued.",
    "checking": "Checking Docker and the current service.",
    "pulling": "Docker image pull started.",
    "starting": "Starting the SearXNG container.",
    "health_check": "Checking the local SearXNG health endpoint.",
    "cleanup": "Asking Docker to remove the replaced image.",
    "complete": "Task completed.",
    "failed": "Task failed.",
}


class SearxngManagerError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _docker_executable() -> str | None:
    configured = (os.environ.get("KNOWTE_DOCKER_BIN") or "").strip()
    if configured:
        configured_path = Path(configured).expanduser()
        if configured_path.is_file():
            return str(configured_path)

    discovered = shutil.which("docker")
    if discovered:
        return discovered

    candidates = [
        Path.home() / ".docker" / "bin" / "docker",
        Path.home() / ".local" / "bin" / "docker",
        Path("/usr/bin/docker"),
        Path("/usr/local/bin/docker"),
        Path("/opt/homebrew/bin/docker"),
        Path("/snap/bin/docker"),
    ]
    if sys.platform == "darwin":
        candidates.extend(
            [
                Path("/Applications/Docker.app/Contents/Resources/bin/docker"),
                Path.home()
                / "Applications"
                / "Docker.app"
                / "Contents"
                / "Resources"
                / "bin"
                / "docker",
            ]
        )
    if os.name == "nt":
        for base in (
            os.environ.get("ProgramFiles"),
            os.environ.get("LOCALAPPDATA"),
        ):
            if base:
                candidates.extend(
                    [
                        Path(base)
                        / "Docker"
                        / "Docker"
                        / "resources"
                        / "bin"
                        / "docker.exe",
                        Path(base) / "Docker" / "resources" / "bin" / "docker.exe",
                    ]
                )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def _docker_process_context() -> tuple[str, Dict[str, str]]:
    executable = _docker_executable()
    if not executable:
        raise SearxngManagerError(
            "docker_not_installed", "Docker CLI is not installed."
        )
    docker_paths = [
        str(Path(executable).parent),
        str(Path.home() / ".docker" / "bin"),
        str(Path.home() / ".local" / "bin"),
    ]
    if os.name != "nt":
        docker_paths.extend(["/usr/local/bin", "/usr/bin", "/snap/bin"])
    if sys.platform == "darwin":
        docker_paths.append("/Applications/Docker.app/Contents/Resources/bin")
    if os.name == "nt":
        docker_paths.extend(
            str(Path(base) / "Docker" / "Docker" / "resources" / "bin")
            for base in (os.environ.get("ProgramFiles"),)
            if base
        )
    inherited_paths = os.environ.get("PATH", "").split(os.pathsep)
    command_paths = list(
        dict.fromkeys(path for path in [*docker_paths, *inherited_paths] if path)
    )
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join(command_paths)
    environment.setdefault("COMPOSE_ANSI", "never")
    environment.setdefault("COMPOSE_PROGRESS", "plain")
    return executable, environment


def _run_docker(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    executable, environment = _docker_process_context()
    try:
        return subprocess.run(
            [executable, *args],
            cwd=MANAGED_DIR if MANAGED_DIR.exists() else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=environment,
        )
    except FileNotFoundError as exc:
        raise SearxngManagerError(
            "docker_not_installed", "Docker CLI is not installed."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise SearxngManagerError(
            "docker_timeout", "Docker did not respond in time."
        ) from exc


def _run_docker_streaming(
    args: list[str],
    timeout: int,
    on_output=None,
) -> subprocess.CompletedProcess:
    executable, environment = _docker_process_context()
    command = [executable, *args]
    try:
        process = subprocess.Popen(
            command,
            cwd=MANAGED_DIR if MANAGED_DIR.exists() else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=environment,
        )
    except FileNotFoundError as exc:
        raise SearxngManagerError(
            "docker_not_installed", "Docker CLI is not installed."
        ) from exc

    output_queue: queue.Queue = queue.Queue()

    def read_output():
        if process.stdout is not None:
            for line in process.stdout:
                output_queue.put(line)
        output_queue.put(None)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    output_parts = []
    deadline = time.monotonic() + timeout
    finished_output = False
    while not finished_output:
        if time.monotonic() >= deadline:
            process.kill()
            process.wait()
            if process.stdout is not None:
                process.stdout.close()
            raise SearxngManagerError(
                "docker_timeout", "Docker did not respond in time."
            )
        try:
            line = output_queue.get(timeout=0.2)
        except queue.Empty:
            if process.poll() is not None and not reader.is_alive():
                break
            continue
        if line is None:
            finished_output = True
            continue
        output_parts.append(line)
        if on_output is not None:
            on_output(line.rstrip("\n"))

    returncode = process.wait()
    if process.stdout is not None:
        process.stdout.close()
    return subprocess.CompletedProcess(
        args=command,
        returncode=returncode,
        stdout="".join(output_parts),
        stderr="",
    )


def _docker_state() -> Dict[str, object]:
    if not _docker_executable():
        return {
            "state": "docker_not_installed",
            "installed": False,
            "running": False,
            "healthy": False,
            "message": "Docker is not installed.",
        }
    result = _run_docker(["info"], timeout=10)
    if result.returncode != 0:
        return {
            "state": "docker_not_running",
            "installed": False,
            "running": False,
            "healthy": False,
            "message": "Docker is installed but its service is not running.",
        }
    return {}


def _inspect_container() -> Dict[str, object] | None:
    result = _run_docker(
        [
            "inspect",
            "--format",
            '{{json .Config.Labels}}|{{.State.Running}}',
            CONTAINER_NAME,
        ],
        timeout=10,
    )
    if result.returncode != 0:
        return None
    try:
        labels_text, running_text = result.stdout.strip().rsplit("|", 1)
        labels = json.loads(labels_text) if labels_text and labels_text != "null" else {}
    except (ValueError, json.JSONDecodeError):
        return None
    return {
        "managed": labels.get(MANAGED_LABEL) == "true",
        "running": running_text.strip().lower() == "true",
    }


def _search_url(port: int | None = None) -> str:
    return f"http://127.0.0.1:{port or DEFAULT_PORT}/search"


def _managed_port() -> int:
    try:
        payload = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        port = int(payload.get("port", DEFAULT_PORT))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return DEFAULT_PORT
    return port if DEFAULT_PORT <= port <= MAX_PORT else DEFAULT_PORT


def _is_healthy(url: str | None = None, timeout: float = 2.0) -> bool:
    parsed = urlsplit(url or SEARCH_URL)
    health_url = urlunsplit((parsed.scheme, parsed.netloc, "/healthz", "", ""))
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(health_url, timeout=timeout) as response:
            payload = response.read().decode("utf-8", errors="replace").strip()
    except OSError:
        return False
    return payload == "OK"


def get_searxng_status() -> Dict[str, object]:
    if not METADATA_PATH.exists() and _is_healthy(SEARCH_URL):
        return {
            "state": "external_running",
            "installed": False,
            "running": True,
            "healthy": True,
            "managed": False,
            "url": SEARCH_URL,
            "message": "A compatible SearXNG service is already running on port 8888.",
        }
    docker_error = _docker_state()
    if docker_error:
        return {**docker_error, "url": _search_url(_managed_port()), "managed": False}

    container = _inspect_container()
    if container is None:
        return {
            "state": "not_installed",
            "installed": False,
            "running": False,
            "healthy": False,
            "managed": False,
            "url": SEARCH_URL,
            "message": "No Knowte-managed SearXNG service is installed.",
        }
    if not container["managed"]:
        return {
            "state": "container_name_conflict",
            "installed": False,
            "running": bool(container["running"]),
            "healthy": False,
            "managed": False,
            "url": _search_url(_managed_port()),
            "message": f"A container named {CONTAINER_NAME} already exists but is not managed by Knowte.",
        }
    if not container["running"]:
        return {
            "state": "stopped",
            "installed": True,
            "running": False,
            "healthy": False,
            "managed": True,
            "url": _search_url(_managed_port()),
            "message": "The Knowte-managed SearXNG service is stopped.",
        }

    managed_url = _search_url(_managed_port())
    healthy = _is_healthy(managed_url)
    return {
        "state": "running" if healthy else "starting",
        "installed": True,
        "running": True,
        "healthy": healthy,
        "managed": True,
        "url": managed_url,
        "message": (
            f"Local Web Search is running at {managed_url}."
            if healthy
            else "SearXNG is running but its JSON API is not ready."
        ),
    }


def _port_is_available(port: int) -> bool:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind(("127.0.0.1", port))
    except OSError:
        return False
    finally:
        probe.close()
    return True


def _select_available_port() -> int:
    for port in range(DEFAULT_PORT, MAX_PORT + 1):
        if _port_is_available(port):
            return port
    raise SearxngManagerError(
        "no_available_port",
        f"No local port is available in the range {DEFAULT_PORT}-{MAX_PORT}.",
    )


def _proxy_settings(proxy: str = "") -> str:
    proxy = str(proxy or "").strip()
    if not proxy:
        return "\n# knowte-proxy-start\n# knowte-proxy-end\n"
    parsed = urlparse(proxy)
    if parsed.scheme not in {"http", "https", "socks5", "socks5h"} or not parsed.netloc:
        raise SearxngManagerError(
            "invalid_proxy", "SearXNG proxy must be an HTTP, HTTPS, SOCKS5, or SOCKS5H URL."
        )
    return (
        "\n# knowte-proxy-start\n"
        "outgoing:\n"
        "  proxies:\n"
        "    all://:\n"
        f"      - {json.dumps(proxy)}\n"
        "# knowte-proxy-end\n"
    )


def _write_managed_files(
    port: int, image: str = SEARXNG_IMAGES[0], proxy: str | None = None,
) -> None:
    if proxy is None:
        from .config import load_config
        proxy = load_config().get("searxng_proxy", "")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    MANAGED_DIR.chmod(0o700)
    CONFIG_DIR.chmod(0o700)
    if not SETTINGS_PATH.exists():
        secret_key = secrets.token_hex(32)
        SETTINGS_PATH.write_text(
            "use_default_settings: true\n\n"
            "search:\n"
            "  formats:\n"
            "    - html\n"
            "    - json\n\n"
            "server:\n"
            "  limiter: false\n"
            f'  secret_key: "{secret_key}"\n'
            + _proxy_settings(proxy),
            encoding="utf-8",
        )
        SETTINGS_PATH.chmod(0o600)
    COMPOSE_PATH.write_text(
        "services:\n"
        "  searxng:\n"
        f"    image: {image}\n"
        f"    container_name: {CONTAINER_NAME}\n"
        "    restart: unless-stopped\n"
        "    labels:\n"
        f'      {MANAGED_LABEL}: "true"\n'
        "    ports:\n"
        f'      - "127.0.0.1:{port}:8080"\n'
        "    volumes:\n"
        '      - "./config:/etc/searxng:rw"\n'
        "    environment:\n"
        f'      SEARXNG_BASE_URL: "http://127.0.0.1:{port}/"\n'
        "    logging:\n"
        "      driver: json-file\n"
        "      options:\n"
        '        max-size: "10m"\n'
        '        max-file: "3"\n',
        encoding="utf-8",
    )
    COMPOSE_PATH.chmod(0o600)
    METADATA_PATH.write_text(
        json.dumps({"port": port, "url": _search_url(port), "image": image}),
        encoding="utf-8",
    )
    METADATA_PATH.chmod(0o600)


def configure_searxng_proxy(proxy: str) -> bool:
    """Update the managed instance settings. Return False for external instances."""
    block = _proxy_settings(proxy)
    try:
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except (OSError, TypeError, json.JSONDecodeError):
        metadata = {}
    if not metadata or not COMPOSE_PATH.exists():
        return False
    text = SETTINGS_PATH.read_text(encoding="utf-8") if SETTINGS_PATH.exists() else ""
    pattern = re.compile(
        r"\n?# knowte-proxy-start\n.*?# knowte-proxy-end\n?", re.DOTALL
    )
    text = pattern.sub("\n", text).rstrip() + block
    SETTINGS_PATH.write_text(text, encoding="utf-8")
    SETTINGS_PATH.chmod(0o600)
    state = _docker_state()
    if state.get("running"):
        restarted = _run_docker(
            ["compose", "-f", str(COMPOSE_PATH), "restart", "searxng"],
            timeout=CONTAINER_START_TIMEOUT,
        )
        if restarted.returncode != 0:
            raise SearxngManagerError(
                "restart_failed", _friendly_docker_error(restarted) or "Could not restart SearXNG."
            )
    return True


def _pull_searxng_image(port: int, progress=None) -> tuple[str, subprocess.CompletedProcess]:
    last = None
    for index, image in enumerate(SEARXNG_IMAGES):
        _write_managed_files(port, image)
        if progress and index:
            progress("pulling", f"Previous image source failed; trying {image}")
        last = _run_docker_streaming(
            ["compose", "-f", str(COMPOSE_PATH), "pull", "searxng"],
            timeout=IMAGE_PULL_TIMEOUT,
            on_output=((lambda line: progress("pulling", line)) if progress else None),
        )
        if last.returncode == 0:
            return image, last
    return SEARXNG_IMAGES[-1], last


def _cleanup_managed_files() -> None:
    for path in (SETTINGS_PATH, COMPOSE_PATH, METADATA_PATH):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    for directory in (CONFIG_DIR, MANAGED_DIR):
        try:
            directory.rmdir()
        except (FileNotFoundError, OSError):
            pass


def _rollback_first_setup(managed_dir_existed: bool) -> None:
    try:
        created = _inspect_container()
        if created is not None and created["managed"]:
            _run_docker(["rm", "-f", CONTAINER_NAME], timeout=60)
    except SearxngManagerError:
        pass
    if not managed_dir_existed:
        _cleanup_managed_files()


def _require_docker(require_compose: bool = False) -> None:
    state = _docker_state()
    if state:
        raise SearxngManagerError(str(state["state"]), str(state["message"]))
    if require_compose:
        compose = _run_docker(["compose", "version"], timeout=15)
        if compose.returncode != 0:
            raise SearxngManagerError(
                "docker_compose_unavailable",
                "Docker Compose is not available.",
            )


def _require_managed_container() -> None:
    container = _inspect_container()
    if container is None:
        raise SearxngManagerError(
            "not_installed", "No Knowte-managed SearXNG service is installed."
        )
    if not container["managed"]:
        raise SearxngManagerError(
            "container_name_conflict",
            f"A container named {CONTAINER_NAME} exists but is not managed by Knowte.",
        )


def setup_searxng(wait_seconds: float = 30.0, progress=None) -> Dict[str, object]:
    if progress:
        progress("checking")
    _require_docker(require_compose=True)
    existing = _inspect_container()
    if existing is not None and not existing["managed"]:
        raise SearxngManagerError(
            "container_name_conflict",
            f"A container named {CONTAINER_NAME} exists but is not managed by Knowte.",
        )
    if existing is None and _is_healthy(SEARCH_URL):
        return get_searxng_status()

    image_before_pull = _latest_image_id(SEARXNG_IMAGES[0])
    managed_dir_existed = MANAGED_DIR.exists()
    port = _managed_port() if existing is not None else _select_available_port()
    _write_managed_files(port)
    try:
        if progress:
            progress("pulling")
        selected_image, pull = _pull_searxng_image(port, progress)
        if pull.returncode != 0:
            raise SearxngManagerError(
                "image_pull_failed",
                (pull.stdout or pull.stderr).strip()
                or "Docker could not download SearXNG.",
            )
        image_after_pull = _latest_image_id(selected_image)
        if image_before_pull and image_before_pull == image_after_pull:
            image_pull_status = "already_cached"
        elif image_after_pull:
            image_pull_status = "downloaded"
        else:
            image_pull_status = "completed"
        if progress:
            progress("starting")
        result = _run_docker_streaming(
            ["compose", "-f", str(COMPOSE_PATH), "up", "-d"],
            timeout=CONTAINER_START_TIMEOUT,
            on_output=(
                (lambda line: progress("starting", line)) if progress else None
            ),
        )
        if result.returncode != 0:
            raise SearxngManagerError(
                "setup_failed",
                (result.stdout or result.stderr).strip()
                or "Docker could not start SearXNG.",
            )
    except SearxngManagerError:
        _rollback_first_setup(managed_dir_existed)
        raise

    deadline = time.monotonic() + wait_seconds
    if progress:
        progress("health_check")
    while time.monotonic() < deadline:
        status = get_searxng_status()
        if status.get("healthy"):
            status["image_pull_status"] = image_pull_status
            return status
        time.sleep(0.5)
    status = get_searxng_status()
    status["image_pull_status"] = image_pull_status
    return status


def start_searxng(wait_seconds: float = 15.0) -> Dict[str, object]:
    _require_docker()
    _require_managed_container()
    result = _run_docker(["start", CONTAINER_NAME], timeout=60)
    if result.returncode != 0:
        raise SearxngManagerError(
            "start_failed", result.stderr.strip() or "Could not start SearXNG."
        )
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        status = get_searxng_status()
        if status.get("healthy"):
            return status
        time.sleep(0.5)
    return get_searxng_status()


def stop_searxng() -> Dict[str, object]:
    _require_docker()
    _require_managed_container()
    result = _run_docker(["stop", CONTAINER_NAME], timeout=60)
    if result.returncode != 0:
        raise SearxngManagerError(
            "stop_failed", result.stderr.strip() or "Could not stop SearXNG."
        )
    return get_searxng_status()


def restart_searxng(wait_seconds: float = 15.0) -> Dict[str, object]:
    _require_docker()
    _require_managed_container()
    result = _run_docker(["restart", CONTAINER_NAME], timeout=60)
    if result.returncode != 0:
        raise SearxngManagerError(
            "restart_failed", result.stderr.strip() or "Could not restart SearXNG."
        )
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        status = get_searxng_status()
        if status.get("healthy"):
            return status
        time.sleep(0.5)
    return get_searxng_status()


def remove_searxng(remove_image: bool = False) -> Dict[str, object]:
    _require_docker()
    _require_managed_container()
    image_id = _container_image_id()
    result = _run_docker(["rm", "-f", CONTAINER_NAME], timeout=60)
    if result.returncode != 0:
        raise SearxngManagerError(
            "remove_failed", result.stderr.strip() or "Could not remove SearXNG."
        )
    removed_url = _search_url(_managed_port())
    _cleanup_managed_files()
    image_removed = False
    image_retained_reason = ""
    if remove_image and image_id:
        image_result = _run_docker(["image", "rm", image_id], timeout=60)
        image_removed = image_result.returncode == 0
        if not image_removed:
            image_retained_reason = (
                image_result.stderr.strip()
                or "Docker retained the image because it is still in use."
            )
    status = get_searxng_status()
    status.update(
        {
            "removed_url": removed_url,
            "image_cache_requested": remove_image,
            "image_cache_removed": image_removed,
            "image_cache_retained_reason": image_retained_reason,
        }
    )
    return status


def _container_image_id() -> str:
    result = _run_docker(
        ["inspect", "--format", "{{.Image}}", CONTAINER_NAME], timeout=15
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _latest_image_id(image: str = SEARXNG_IMAGES[0]) -> str:
    result = _run_docker(
        [
            "image",
            "inspect",
            "--format",
            "{{.Id}}",
            image,
        ],
        timeout=15,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _container_log_rotation_configured() -> bool:
    result = _run_docker(
        [
            "inspect",
            "--format",
            "{{json .HostConfig.LogConfig}}",
            CONTAINER_NAME,
        ],
        timeout=15,
    )
    if result.returncode != 0:
        return False
    try:
        config = json.loads(result.stdout.strip())
    except (TypeError, json.JSONDecodeError):
        return False
    options = config.get("Config") if isinstance(config, dict) else {}
    return (
        isinstance(options, dict)
        and config.get("Type") == "json-file"
        and options.get("max-size") == "10m"
        and options.get("max-file") == "3"
    )


def update_searxng(wait_seconds: float = 30.0, progress=None) -> Dict[str, object]:
    if progress:
        progress("checking")
    _require_docker(require_compose=True)
    _require_managed_container()
    old_image_id = _container_image_id()
    rotation_configured = _container_log_rotation_configured()
    port = _managed_port()
    if progress:
        progress("pulling")
    selected_image, pull = _pull_searxng_image(port, progress)
    if pull.returncode != 0:
        raise SearxngManagerError(
            "update_failed",
            (pull.stdout or pull.stderr).strip() or "Could not update SearXNG.",
        )
    new_image_id = _latest_image_id(selected_image)
    image_unchanged = (
        bool(old_image_id) and bool(new_image_id) and old_image_id == new_image_id
    )
    if image_unchanged and rotation_configured:
        status = get_searxng_status()
        status.update(
            {
                "update_status": "up_to_date",
                "old_image_removed": False,
                "message": "SearXNG is already using the latest image.",
            }
        )
        if progress:
            progress("complete")
        return status

    if progress:
        progress("starting")
    up = _run_docker_streaming(
        ["compose", "-f", str(COMPOSE_PATH), "up", "-d"],
        timeout=CONTAINER_START_TIMEOUT,
        on_output=((lambda line: progress("starting", line)) if progress else None),
    )
    if up.returncode != 0:
        raise SearxngManagerError(
            "update_failed",
            (up.stdout or up.stderr).strip()
            or "Could not restart updated SearXNG.",
        )
    deadline = time.monotonic() + wait_seconds
    if progress:
        progress("health_check")
    while time.monotonic() < deadline:
        status = get_searxng_status()
        if status.get("healthy"):
            removed = False
            retained_reason = ""
            if old_image_id and old_image_id != new_image_id:
                if progress:
                    progress("cleanup")
                cleanup = _run_docker(["image", "rm", old_image_id], timeout=60)
                removed = cleanup.returncode == 0
                if not removed:
                    retained_reason = (
                        cleanup.stderr.strip()
                        or "The old image is still used by another container."
                    )
            status.update(
                {
                    "update_status": (
                        "reconfigured" if image_unchanged else "updated"
                    ),
                    "old_image_removed": removed,
                    "old_image_retained_reason": retained_reason,
                }
            )
            if image_unchanged:
                status["message"] = (
                    "SearXNG configuration was updated; the image was unchanged."
                )
            if progress:
                progress("complete")
            return status
        time.sleep(0.5)
    status = get_searxng_status()
    status.update(
        {
            "update_status": "unhealthy",
            "old_image_removed": False,
            "message": "The new image was installed but did not become healthy.",
        }
    )
    return status


def get_searxng_logs() -> Dict[str, object]:
    _require_docker()
    _require_managed_container()
    result = _run_docker_streaming(
        ["logs", "--tail", "500", CONTAINER_NAME],
        timeout=30,
    )
    if result.returncode != 0:
        raise SearxngManagerError(
            "logs_failed",
            (result.stdout or result.stderr).strip()
            or "Could not read SearXNG logs.",
        )
    status = get_searxng_status()
    logs = (result.stdout or result.stderr).strip()
    status["logs"] = logs
    status["logs_limit"] = 500
    status["logs_note"] = (
        "Showing the latest 500 lines. SearXNG labels upstream CAPTCHA, "
        "access-denied, and rate-limit responses as errors. Individual engine "
        "errors do not necessarily mean the local service is unhealthy."
    )
    return status


def manage_searxng(
    action: str, progress=None, remove_image: bool = False
) -> Dict[str, object]:
    actions = {
        "setup": setup_searxng,
        "start": start_searxng,
        "stop": stop_searxng,
        "restart": restart_searxng,
        "remove": remove_searxng,
        "logs": get_searxng_logs,
        "update": update_searxng,
    }
    handler = actions.get(action)
    if handler is None:
        raise SearxngManagerError("invalid_action", "Unknown SearXNG action.")
    with _MANAGER_LOCK:
        if action in {"setup", "update"}:
            return handler(progress=progress)
        if action == "remove":
            return handler(remove_image=remove_image)
        return handler()


def _job_snapshot(job: Dict[str, object]) -> Dict[str, object]:
    snapshot = {
        key: value
        for key, value in job.items()
        if key not in {"started_monotonic", "on_complete"}
    }
    started = float(job.get("started_monotonic", time.monotonic()))
    snapshot["elapsed_seconds"] = max(0, round(time.monotonic() - started, 1))
    snapshot["output"] = list(job.get("output", []))
    snapshot["display_output"] = list(job.get("display_output", []))
    return snapshot


def start_searxng_job(action: str, on_complete=None) -> Dict[str, object]:
    if action not in {"setup", "update"}:
        raise SearxngManagerError(
            "invalid_background_action",
            "Only SearXNG setup and update can run as background tasks.",
        )
    with _JOBS_LOCK:
        completed_ids = [
            job_id
            for job_id, existing_job in _JOBS.items()
            if existing_job.get("status") != "running"
        ]
        for completed_id in completed_ids[:-20]:
            _JOBS.pop(completed_id, None)
        active = next(
            (job for job in _JOBS.values() if job.get("status") == "running"),
            None,
        )
        if active is not None:
            raise SearxngManagerError(
                "job_in_progress",
                f"A SearXNG {active['action']} task is already running.",
            )
        job_id = uuid.uuid4().hex
        job: Dict[str, object] = {
            "job_id": job_id,
            "action": action,
            "status": "running",
            "phase": "queued",
            "output": [],
            "display_output": [f"[Knowte] {_JOB_PHASE_MESSAGES['queued']}"],
            "output_truncated": False,
            "started_monotonic": time.monotonic(),
            "on_complete": on_complete,
        }
        _JOBS[job_id] = job

    def progress(phase: str, line: str | None = None) -> None:
        with _JOBS_LOCK:
            previous_phase = job.get("phase")
            job["phase"] = phase
            display_output = job["display_output"]
            if (
                previous_phase != phase
                and isinstance(display_output, list)
                and phase in _JOB_PHASE_MESSAGES
            ):
                display_output.append(f"[Knowte] {_JOB_PHASE_MESSAGES[phase]}")
            if line is not None:
                output = job["output"]
                if isinstance(output, list):
                    output.append(line)
                    if len(output) > 2000:
                        del output[: len(output) - 2000]
                        job["output_truncated"] = True
                if isinstance(display_output, list):
                    display_output.append(line)
            if isinstance(display_output, list) and len(display_output) > 2020:
                del display_output[: len(display_output) - 2020]
                job["output_truncated"] = True

    def run() -> None:
        try:
            result = manage_searxng(action, progress=progress)
            callback = job.get("on_complete")
            if callable(callback):
                callback(result)
            progress("complete")
            with _JOBS_LOCK:
                job["result"] = result
                job["status"] = "completed"
        except SearxngManagerError as error:
            progress("failed")
            with _JOBS_LOCK:
                job["status"] = "failed"
                job["error"] = error.code
                job["message"] = str(error)
        except Exception:
            progress("failed")
            with _JOBS_LOCK:
                job["status"] = "failed"
                job["error"] = "background_task_failed"
                job["message"] = "The SearXNG task failed unexpectedly."

    threading.Thread(
        target=run,
        name=f"knowte-searxng-{action}",
        daemon=True,
    ).start()
    with _JOBS_LOCK:
        return _job_snapshot(job)


def get_searxng_job(job_id: str) -> Dict[str, object]:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            raise SearxngManagerError(
                "job_not_found", "The SearXNG task was not found."
            )
        return _job_snapshot(job)
