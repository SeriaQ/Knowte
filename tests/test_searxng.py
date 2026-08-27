import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from knowte import searxng


class ManagedSearxngTests(unittest.TestCase):
    def test_managed_proxy_is_written_and_running_service_restarts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            managed_dir = Path(temp_dir) / "searxng"
            config_dir = managed_dir / "config"
            config_dir.mkdir(parents=True)
            settings_path = config_dir / "settings.yml"
            compose_path = managed_dir / "compose.yml"
            metadata_path = managed_dir / "managed.json"
            settings_path.write_text("use_default_settings: true\n", encoding="utf-8")
            compose_path.write_text("services: {}\n", encoding="utf-8")
            metadata_path.write_text(json.dumps({"port": 8888, "image": "image"}), encoding="utf-8")
            completed = subprocess.CompletedProcess([], 0, "", "")
            with patch.object(searxng, "MANAGED_DIR", managed_dir), patch.object(
                searxng, "CONFIG_DIR", config_dir
            ), patch.object(searxng, "SETTINGS_PATH", settings_path), patch.object(
                searxng, "COMPOSE_PATH", compose_path
            ), patch.object(searxng, "METADATA_PATH", metadata_path), patch(
                "knowte.searxng._docker_state", return_value={"running": True}
            ), patch("knowte.searxng._run_docker", return_value=completed) as restart:
                self.assertTrue(searxng.configure_searxng_proxy("socks5://proxy.test:1080"))

            settings = settings_path.read_text(encoding="utf-8")
            self.assertIn("all://", settings)
            self.assertIn("socks5://proxy.test:1080", settings)
            restart.assert_called_once()

    def test_pull_falls_back_to_official_ghcr_registry(self):
        failed = subprocess.CompletedProcess(
            args=["docker"], returncode=1, stdout="", stderr="timeout"
        )
        succeeded = subprocess.CompletedProcess(
            args=["docker"], returncode=0, stdout="pulled", stderr=""
        )
        with patch("knowte.searxng._write_managed_files") as write_files, patch(
            "knowte.searxng._run_docker_streaming", side_effect=[failed, succeeded]
        ) as pull:
            image, result = searxng._pull_searxng_image(8888)

        self.assertEqual(image, "ghcr.io/searxng/searxng:latest")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(write_files.call_args_list, [
            call(8888, "docker.io/searxng/searxng:latest"),
            call(8888, "ghcr.io/searxng/searxng:latest"),
        ])
        self.assertEqual(pull.call_count, 2)

    def test_health_check_uses_local_healthz_without_searching(self):
        response = MagicMock()
        response.read.return_value = b"OK"
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value = response

        with patch("knowte.searxng.build_opener", return_value=opener):
            healthy = searxng._is_healthy(
                "http://127.0.0.1:8890/search", timeout=1.5
            )

        self.assertTrue(healthy)
        opener.open.assert_called_once_with(
            "http://127.0.0.1:8890/healthz", timeout=1.5
        )

    def test_docker_commands_include_desktop_helpers_in_path(self):
        completed = subprocess.CompletedProcess(
            args=["docker"], returncode=0, stdout="", stderr=""
        )
        docker_path = "/Applications/Docker.app/Contents/Resources/bin/docker"
        with patch(
            "knowte.searxng._docker_executable", return_value=docker_path
        ), patch("knowte.searxng.subprocess.run", return_value=completed) as run:
            searxng._run_docker(["info"])

        environment_path = run.call_args.kwargs["env"]["PATH"].split(
            searxng.os.pathsep
        )
        self.assertIn(
            "/Applications/Docker.app/Contents/Resources/bin", environment_path
        )
        self.assertIn(str(Path.home() / ".docker" / "bin"), environment_path)

    def test_explicit_docker_binary_override_takes_precedence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            docker_path = Path(temp_dir) / "custom-docker"
            docker_path.touch()
            with patch.dict(
                searxng.os.environ,
                {"KNOWTE_DOCKER_BIN": str(docker_path)},
            ), patch("knowte.searxng.shutil.which", return_value="/usr/bin/docker"):
                discovered = searxng._docker_executable()

        self.assertEqual(discovered, str(docker_path))

    def test_status_reports_missing_docker(self):
        with patch("knowte.searxng._is_healthy", return_value=False), patch(
            "knowte.searxng._docker_executable", return_value=None
        ):
            status = searxng.get_searxng_status()

        self.assertEqual(status["state"], "docker_not_installed")
        self.assertFalse(status["installed"])

    def test_setup_writes_private_local_configuration_and_starts_compose(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            managed_dir = Path(temp_dir) / "searxng"
            config_dir = managed_dir / "config"
            settings_path = config_dir / "settings.yml"
            compose_path = managed_dir / "compose.yml"
            metadata_path = managed_dir / "managed.json"
            completed = subprocess.CompletedProcess(
                args=["docker"], returncode=0, stdout="", stderr=""
            )
            healthy = {
                "state": "running",
                "installed": True,
                "running": True,
                "healthy": True,
                "managed": True,
                "url": searxng.SEARCH_URL,
                "message": "Local Web Search is running.",
            }

            with patch.object(searxng, "MANAGED_DIR", managed_dir), patch.object(
                searxng, "CONFIG_DIR", config_dir
            ), patch.object(searxng, "SETTINGS_PATH", settings_path), patch.object(
                searxng, "COMPOSE_PATH", compose_path
            ), patch.object(
                searxng, "METADATA_PATH", metadata_path
            ), patch("knowte.searxng._docker_state", return_value={}), patch(
                "knowte.searxng._inspect_container", return_value=None
            ), patch(
                "knowte.searxng._is_healthy", return_value=False
            ), patch(
                "knowte.searxng._select_available_port", return_value=8888
            ), patch(
                "knowte.searxng._run_docker", return_value=completed
            ), patch(
                "knowte.searxng._run_docker_streaming", return_value=completed
            ) as run_streaming, patch(
                "knowte.searxng.get_searxng_status", return_value=healthy
            ):
                result = searxng.setup_searxng(wait_seconds=0.1)

            self.assertTrue(result["healthy"])
            self.assertIn("- json", settings_path.read_text(encoding="utf-8"))
            compose = compose_path.read_text(encoding="utf-8")
            self.assertIn('"127.0.0.1:8888:8080"', compose)
            self.assertIn('io.knowte.managed: "true"', compose)
            self.assertIn('max-size: "10m"', compose)
            self.assertIn('max-file: "3"', compose)
            self.assertEqual(
                run_streaming.call_args_list[-1].args[0],
                ["compose", "-f", str(compose_path), "up", "-d"],
            )
            self.assertEqual(
                run_streaming.call_args_list[-1].kwargs["timeout"],
                searxng.CONTAINER_START_TIMEOUT,
            )
            self.assertEqual(
                run_streaming.call_args_list[-2].args[0],
                ["compose", "-f", str(compose_path), "pull", "searxng"],
            )
            self.assertEqual(
                run_streaming.call_args_list[-2].kwargs["timeout"],
                searxng.IMAGE_PULL_TIMEOUT,
            )
            self.assertEqual(
                json.loads(metadata_path.read_text(encoding="utf-8"))["port"], 8888
            )
            self.assertEqual(settings_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(compose_path.stat().st_mode & 0o777, 0o600)

    def test_setup_refuses_unmanaged_container_name_conflict(self):
        completed = subprocess.CompletedProcess(
            args=["docker"], returncode=0, stdout="", stderr=""
        )
        with patch("knowte.searxng._docker_state", return_value={}), patch(
            "knowte.searxng._run_docker", return_value=completed
        ), patch(
            "knowte.searxng._inspect_container",
            return_value={"managed": False, "running": True},
        ):
            with self.assertRaises(searxng.SearxngManagerError) as error:
                searxng.setup_searxng()

        self.assertEqual(error.exception.code, "container_name_conflict")

    def test_port_selection_skips_occupied_ports(self):
        availability = {8888: False, 8889: False, 8890: True}
        with patch(
            "knowte.searxng._port_is_available",
            side_effect=lambda port: availability.get(port, True),
        ):
            selected = searxng._select_available_port()

        self.assertEqual(selected, 8890)

    def test_setup_reuses_compatible_external_service(self):
        completed = subprocess.CompletedProcess(
            args=["docker"], returncode=0, stdout="", stderr=""
        )
        external = {
            "state": "external_running",
            "installed": False,
            "running": True,
            "healthy": True,
            "managed": False,
            "url": searxng.SEARCH_URL,
            "message": "A compatible SearXNG service is already running.",
        }
        with patch("knowte.searxng._docker_state", return_value={}), patch(
            "knowte.searxng._run_docker", return_value=completed
        ), patch("knowte.searxng._inspect_container", return_value=None), patch(
            "knowte.searxng._is_healthy", return_value=True
        ), patch(
            "knowte.searxng.get_searxng_status", return_value=external
        ):
            result = searxng.setup_searxng()

        self.assertEqual(result["state"], "external_running")

    def test_failed_first_setup_cleans_generated_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            managed_dir = Path(temp_dir) / "searxng"
            config_dir = managed_dir / "config"
            settings_path = config_dir / "settings.yml"
            compose_path = managed_dir / "compose.yml"
            metadata_path = managed_dir / "managed.json"
            compose_ok = subprocess.CompletedProcess(
                args=["docker"], returncode=0, stdout="", stderr=""
            )
            setup_failed = subprocess.CompletedProcess(
                args=["docker"], returncode=1, stdout="", stderr="port conflict"
            )

            with patch.object(searxng, "MANAGED_DIR", managed_dir), patch.object(
                searxng, "CONFIG_DIR", config_dir
            ), patch.object(searxng, "SETTINGS_PATH", settings_path), patch.object(
                searxng, "COMPOSE_PATH", compose_path
            ), patch.object(
                searxng, "METADATA_PATH", metadata_path
            ), patch("knowte.searxng._docker_state", return_value={}), patch(
                "knowte.searxng._inspect_container", side_effect=[None, None]
            ), patch("knowte.searxng._is_healthy", return_value=False), patch(
                "knowte.searxng._select_available_port", return_value=8888
            ), patch(
                "knowte.searxng._run_docker",
                return_value=compose_ok,
            ), patch(
                "knowte.searxng._run_docker_streaming",
                side_effect=[compose_ok, setup_failed],
            ):
                with self.assertRaises(searxng.SearxngManagerError) as error:
                    searxng.setup_searxng()

            self.assertEqual(error.exception.code, "setup_failed")
            self.assertFalse(managed_dir.exists())

    def test_timed_out_first_pull_cleans_generated_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            managed_dir = Path(temp_dir) / "searxng"
            config_dir = managed_dir / "config"
            settings_path = config_dir / "settings.yml"
            compose_path = managed_dir / "compose.yml"
            metadata_path = managed_dir / "managed.json"
            compose_ok = subprocess.CompletedProcess(
                args=["docker"], returncode=0, stdout="", stderr=""
            )
            timeout_error = searxng.SearxngManagerError(
                "docker_timeout", "Docker did not respond in time."
            )

            with patch.object(searxng, "MANAGED_DIR", managed_dir), patch.object(
                searxng, "CONFIG_DIR", config_dir
            ), patch.object(searxng, "SETTINGS_PATH", settings_path), patch.object(
                searxng, "COMPOSE_PATH", compose_path
            ), patch.object(
                searxng, "METADATA_PATH", metadata_path
            ), patch("knowte.searxng._docker_state", return_value={}), patch(
                "knowte.searxng._inspect_container", side_effect=[None, None]
            ), patch("knowte.searxng._is_healthy", return_value=False), patch(
                "knowte.searxng._select_available_port", return_value=8888
            ), patch(
                "knowte.searxng._run_docker",
                return_value=compose_ok,
            ), patch(
                "knowte.searxng._run_docker_streaming",
                side_effect=timeout_error,
            ):
                with self.assertRaises(searxng.SearxngManagerError) as error:
                    searxng.setup_searxng()

            self.assertEqual(error.exception.code, "docker_timeout")
            self.assertFalse(managed_dir.exists())

    def test_update_does_not_recreate_when_image_is_current(self):
        completed = subprocess.CompletedProcess(
            args=["docker"], returncode=0, stdout="", stderr=""
        )
        status = {
            "state": "running",
            "installed": True,
            "running": True,
            "healthy": True,
            "managed": True,
            "url": searxng.SEARCH_URL,
        }
        with patch("knowte.searxng._require_docker"), patch(
            "knowte.searxng._require_managed_container"
        ), patch(
            "knowte.searxng._write_managed_files"
        ), patch(
            "knowte.searxng._container_log_rotation_configured",
            return_value=True,
        ), patch("knowte.searxng._container_image_id", return_value="sha256:same"), patch(
            "knowte.searxng._latest_image_id", return_value="sha256:same"
        ), patch(
            "knowte.searxng._run_docker_streaming", return_value=completed
        ) as streaming, patch(
            "knowte.searxng.get_searxng_status", return_value=status
        ):
            result = searxng.update_searxng()

        self.assertEqual(result["update_status"], "up_to_date")
        self.assertEqual(streaming.call_count, 1)

    def test_update_removes_only_replaced_image_after_health_check(self):
        completed = subprocess.CompletedProcess(
            args=["docker"], returncode=0, stdout="", stderr=""
        )
        healthy = {
            "state": "running",
            "installed": True,
            "running": True,
            "healthy": True,
            "managed": True,
            "url": searxng.SEARCH_URL,
        }
        with patch("knowte.searxng._require_docker"), patch(
            "knowte.searxng._require_managed_container"
        ), patch(
            "knowte.searxng._write_managed_files"
        ), patch(
            "knowte.searxng._container_log_rotation_configured",
            return_value=True,
        ), patch("knowte.searxng._container_image_id", return_value="sha256:old"), patch(
            "knowte.searxng._latest_image_id", return_value="sha256:new"
        ), patch(
            "knowte.searxng._run_docker_streaming", return_value=completed
        ), patch(
            "knowte.searxng.get_searxng_status", return_value=healthy
        ), patch(
            "knowte.searxng._run_docker", return_value=completed
        ) as run_docker:
            result = searxng.update_searxng()

        self.assertEqual(result["update_status"], "updated")
        self.assertTrue(result["old_image_removed"])
        run_docker.assert_called_once_with(
            ["image", "rm", "sha256:old"], timeout=60
        )

    def test_update_recreates_current_image_to_apply_log_rotation(self):
        completed = subprocess.CompletedProcess(
            args=["docker"], returncode=0, stdout="", stderr=""
        )
        healthy = {
            "state": "running",
            "installed": True,
            "running": True,
            "healthy": True,
            "managed": True,
            "url": searxng.SEARCH_URL,
        }
        with patch("knowte.searxng._require_docker"), patch(
            "knowte.searxng._require_managed_container"
        ), patch(
            "knowte.searxng._write_managed_files"
        ) as write_files, patch(
            "knowte.searxng._container_log_rotation_configured",
            return_value=False,
        ), patch(
            "knowte.searxng._container_image_id", return_value="sha256:same"
        ), patch(
            "knowte.searxng._latest_image_id", return_value="sha256:same"
        ), patch(
            "knowte.searxng._run_docker_streaming", return_value=completed
        ) as streaming, patch(
            "knowte.searxng.get_searxng_status", return_value=healthy
        ):
            result = searxng.update_searxng()

        self.assertEqual(result["update_status"], "reconfigured")
        self.assertEqual(streaming.call_count, 2)
        write_files.assert_called_once()

    def test_remove_can_delete_only_the_managed_container_image(self):
        completed = subprocess.CompletedProcess(
            args=["docker"], returncode=0, stdout="", stderr=""
        )
        status = {
            "state": "not_installed",
            "installed": False,
            "running": False,
            "healthy": False,
        }
        with patch("knowte.searxng._require_docker"), patch(
            "knowte.searxng._require_managed_container"
        ), patch(
            "knowte.searxng._container_image_id", return_value="sha256:managed"
        ), patch(
            "knowte.searxng._managed_port", return_value=8888
        ), patch(
            "knowte.searxng._cleanup_managed_files"
        ), patch(
            "knowte.searxng.get_searxng_status", return_value=status
        ), patch(
            "knowte.searxng._run_docker", return_value=completed
        ) as run_docker:
            result = searxng.remove_searxng(remove_image=True)

        self.assertTrue(result["image_cache_removed"])
        self.assertEqual(
            run_docker.call_args_list,
            [
                call(["rm", "-f", searxng.CONTAINER_NAME], timeout=60),
                call(["image", "rm", "sha256:managed"], timeout=60),
            ],
        )

    def test_background_job_preserves_raw_docker_output(self):
        searxng._JOBS.clear()

        def managed(action, progress=None):
            progress("pulling", "layer 1: 37.2MB / 100MB")
            progress("starting", "Container knowte-searxng Started")
            return {"state": "running", "healthy": True}

        with patch("knowte.searxng.manage_searxng", side_effect=managed):
            job = searxng.start_searxng_job("setup")
            for _ in range(100):
                snapshot = searxng.get_searxng_job(job["job_id"])
                if snapshot["status"] != "running":
                    break
                searxng.time.sleep(0.01)

        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(
            snapshot["output"],
            ["layer 1: 37.2MB / 100MB", "Container knowte-searxng Started"],
        )
        self.assertIn(
            "[Knowte] Docker image pull started.", snapshot["display_output"]
        )

    def test_logs_preserve_stdout_stderr_order_from_docker(self):
        completed = subprocess.CompletedProcess(
            args=["docker"],
            returncode=0,
            stdout="first\nsecond\n",
            stderr="",
        )
        status = {
            "state": "running",
            "installed": True,
            "running": True,
            "healthy": True,
        }
        with patch("knowte.searxng._require_docker"), patch(
            "knowte.searxng._require_managed_container"
        ), patch(
            "knowte.searxng._run_docker_streaming", return_value=completed
        ) as streaming, patch(
            "knowte.searxng.get_searxng_status", return_value=status
        ):
            result = searxng.get_searxng_logs()

        self.assertEqual(result["logs"], "first\nsecond")
        self.assertEqual(result["logs_limit"], 500)
        streaming.assert_called_once_with(
            ["logs", "--tail", "500", searxng.CONTAINER_NAME],
            timeout=30,
        )


if __name__ == "__main__":
    unittest.main()
