import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from unittest.mock import patch, MagicMock

from knowte.server import create_server, main, prepare_library_config
from knowte import usage


class NamedLibraryTests(unittest.TestCase):
    def test_invalid_names_cannot_escape_or_reuse_reserved_directories(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ("", "..", "../other", "/tmp", "a/b", "a\\b", "skills", "NUL", "x" * 65):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    prepare_library_config(Path(folder) / "config.yml", name)

    def test_seeds_only_settings_and_skills_without_overwriting_progress(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "config.yml"
            source.write_text("email: original@example.test\n", encoding="utf-8")
            (root / "knowte.db").write_text("production database")
            (root / "plans.json").write_text("[]")
            (root / "skills" / "custom").mkdir(parents=True)
            (root / "skills" / "custom" / "SKILL.md").write_text("custom guidance")
            target = prepare_library_config(source, "learning")
            self.assertEqual(target.parent, root / "learning")
            self.assertEqual(target.read_text(), source.read_text())
            self.assertFalse((target.parent / "knowte.db").exists())
            self.assertFalse((target.parent / "plans.json").exists())
            self.assertEqual((target.parent / "skills/custom/SKILL.md").read_text(), "custom guidance")
            target.write_text("email: test@example.test\n")
            (target.parent / "knowte.db").write_text("test progress")
            with self.assertRaisesRegex(ValueError, "already exists"):
                prepare_library_config(source, "learning")
            self.assertEqual(prepare_library_config(source, "learning", create=False), target)
            self.assertIn("test@example.test", target.read_text())
            self.assertEqual((target.parent / "knowte.db").read_text(), "test progress")
            self.assertIn("original@example.test", source.read_text())

    def test_cli_new_library_uses_separate_usage_and_common_port(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch("sys.argv", ["knowte", "--new", "learning", "--config", str(Path(folder) / "config.yml")]), \
                patch.dict("os.environ", {}, clear=True), \
                patch("knowte.server.create_server", return_value=MagicMock()) as server, \
                patch.object(usage, "USAGE_DIR", usage.USAGE_DIR), \
                patch.object(usage, "USAGE_PATH", usage.USAGE_PATH):
            main()
            target = Path(folder).resolve() / "learning" / "config.yml"
            server.assert_called_once_with("127.0.0.1", 7880, target, library_name="learning")
            self.assertEqual(usage.USAGE_PATH, target.parent / "usage.json")
            self.assertTrue(target.is_file())

    def test_default_is_an_alias_and_mount_never_creates_missing_library(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "config.yml"
            self.assertEqual(prepare_library_config(source, "default", create=False), source)
            self.assertFalse(source.exists())
            with self.assertRaisesRegex(ValueError, "default library already exists"):
                prepare_library_config(source, "default")
            with self.assertRaisesRegex(ValueError, "not found"):
                prepare_library_config(source, "missing", create=False)
            self.assertFalse((source.parent / "missing").exists())
            (source.parent / "empty").mkdir()
            with self.assertRaisesRegex(ValueError, "already exists"):
                prepare_library_config(source, "empty")
            with self.assertRaisesRegex(ValueError, "not found"):
                prepare_library_config(source, "empty", create=False)

    def test_mount_default_named_and_port_overrides(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder).resolve() / "config.yml"
            named = prepare_library_config(source, "learning")
            for options, environment, name, path, port in (
                ([], {}, "default", source, 7880),
                (["--mount", "default"], {}, "default", source, 7880),
                (["--mount", "learning"], {}, "learning", named, 7880),
                (["--mount", "learning"], {"PORT": "8123"}, "learning", named, 8123),
                (["--mount", "learning", "--port", "8124"], {"PORT": "8123"}, "learning", named, 8124),
            ):
                with self.subTest(options=options, environment=environment), \
                        patch("sys.argv", ["knowte", "--config", str(source), *options]), \
                        patch.dict("os.environ", environment, clear=True), \
                        patch("knowte.server.create_server", return_value=MagicMock()) as server, \
                        patch.object(usage, "USAGE_DIR", usage.USAGE_DIR), \
                        patch.object(usage, "USAGE_PATH", usage.USAGE_PATH):
                    main()
                    server.assert_called_once_with("127.0.0.1", port, path, library_name=name)
                    self.assertEqual(usage.USAGE_PATH, path.parent / "usage.json")

    def test_new_and_mount_are_mutually_exclusive(self):
        with patch("sys.argv", ["knowte", "--new", "a", "--mount", "b"]), \
                patch("knowte.server.create_server") as server, \
                self.assertRaises(SystemExit) as error:
            main()
        self.assertEqual(error.exception.code, 2)
        server.assert_not_called()

    def test_test_server_reports_mode_and_blocks_shared_container_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            target = prepare_library_config(Path(folder) / "config.yml", "learning")
            server = create_server("127.0.0.1", 0, target, library_name="learning")
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                connection = HTTPConnection(*server.server_address)
                connection.request("GET", "/api/config")
                self.assertEqual(json.loads(connection.getresponse().read())["library_name"], "learning")
                connection.request("GET", "/api/library/sources")
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read())["sources"], [])
                connection.request("POST", "/api/searxng", json.dumps({"action": "stop"}),
                                   {"Content-Type": "application/json"})
                response = connection.getresponse()
                self.assertEqual(response.status, 409)
                response.read()
                connection.close()
            finally:
                server.shutdown()
                server.server_close()
                worker.join()
