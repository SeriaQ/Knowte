import json
from http.client import HTTPConnection
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from knowte import usage
from knowte import search as search_module
from knowte.models import Paper
from knowte.server import create_server


class SearchApiTests(unittest.TestCase):
    def _request(self, server, method, path, body=None):
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            port = server.server_address[1]
            connection = HTTPConnection("127.0.0.1", port)
            headers = {"Content-Type": "application/json"} if body else {}
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join()

    def test_unconfigured_websearch_is_removed_without_web_usage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            usage_path = temp_path / "usage.json"
            config_path.write_text(
                "enabled_backends: arxiv,websearch\nmax_papers: 20\n",
                encoding="utf-8",
            )

            with patch.object(usage, "USAGE_DIR", temp_path), patch.object(
                usage, "USAGE_PATH", usage_path
            ), patch("knowte.server.search_papers", return_value=[]):
                server = create_server("127.0.0.1", 0, config_path)
                thread = threading.Thread(target=server.serve_forever)
                thread.start()
                try:
                    port = server.server_address[1]
                    connection = HTTPConnection("127.0.0.1", port)
                    connection.request("GET", "/api/search?q=test&limit=20")
                    response = connection.getresponse()
                    payload = json.loads(response.read())
                    connection.close()
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join()

        self.assertEqual(payload["enabled_backends"], ["arxiv"])
        self.assertEqual(payload["warnings"], ["websearch_unconfigured"])
        self.assertEqual(payload["usage"]["last_day"], 1)
        self.assertEqual(payload["usage"]["last_day_web"], 0)

    def test_cached_find_more_does_not_increment_paper_usage(self):
        def papers(prefix, source):
            return [
                Paper(
                    id=f"{prefix}-{index}",
                    title=f"Alpha {prefix} {index}",
                    authors="Author",
                    year=2020,
                    abstract="alpha",
                    url=f"https://example.test/{prefix}/{index}",
                    keywords=[],
                    source=source,
                )
                for index in range(60)
            ]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            usage_path = temp_path / "usage.json"
            config_path.write_text(
                "enabled_backends: arxiv,openalex,semanticscholar\n"
                "max_papers: 60\n",
                encoding="utf-8",
            )
            search_module._ACADEMIC_CACHE.clear()
            with patch.object(usage, "USAGE_DIR", temp_path), patch.object(
                usage, "USAGE_PATH", usage_path
            ), patch(
                "knowte.search.search_arxiv", return_value=papers("a", "arXiv")
            ) as arxiv, patch(
                "knowte.search.search_openalex",
                return_value=papers("o", "OpenAlex"),
            ) as openalex, patch(
                "knowte.search.search_semanticscholar",
                return_value=papers("s", "Semantic Scholar"),
            ) as semanticscholar:
                first_server = create_server("127.0.0.1", 0, config_path)
                first_status, first = self._request(
                    first_server, "GET", "/api/search?q=alpha&limit=60"
                )
                second_server = create_server("127.0.0.1", 0, config_path)
                second_status, second = self._request(
                    second_server, "GET", "/api/search?q=alpha&limit=120"
                )

        self.assertEqual(first_status, 200)
        self.assertEqual(second_status, 200)
        self.assertEqual(first["usage"]["last_day"], 1)
        self.assertEqual(second["usage"]["last_day"], 1)
        self.assertTrue(second["search_diagnostics"]["academic"]["cache_hit"])
        self.assertFalse(
            second["search_diagnostics"]["academic"]["external_request"]
        )
        arxiv.assert_called_once()
        openalex.assert_called_once()
        semanticscholar.assert_called_once()

    def test_new_config_uses_academic_sources_and_one_hundred_as_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            server = create_server("127.0.0.1", 0, config_path)
            status, payload = self._request(server, "GET", "/api/config")

        self.assertEqual(status, 200)
        self.assertEqual(
            payload["enabled_backends"],
            ["arxiv", "openalex", "semanticscholar"],
        )
        self.assertNotIn("websearch", payload["enabled_backends"])
        self.assertEqual(payload["max_papers"], 100)

    def test_server_can_restart_immediately_on_same_port(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            first = create_server("127.0.0.1", 0, config_path)
            port = first.server_address[1]
            thread = threading.Thread(target=first.serve_forever)
            thread.start()
            try:
                connection = HTTPConnection("127.0.0.1", port)
                connection.request("GET", "/api/health")
                response = connection.getresponse()
                response.read()
                connection.close()
            finally:
                first.shutdown()
                first.server_close()
                thread.join()

            second = create_server("127.0.0.1", port, config_path)
            second.server_close()

        self.assertEqual(response.status, 200)

    def test_managed_searxng_setup_updates_app_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            config_path.write_text(
                "enabled_backends: arxiv\nmax_papers: 100\n", encoding="utf-8"
            )
            managed_status = {
                "state": "running",
                "installed": True,
                "running": True,
                "healthy": True,
                "managed": True,
                "url": "http://127.0.0.1:8889/search",
                "message": "Local Web Search is running.",
            }
            def start_job(action, on_complete=None):
                on_complete(managed_status)
                return {
                    "job_id": "setup-job",
                    "action": action,
                    "status": "running",
                    "phase": "queued",
                    "output": [],
                }

            with patch(
                "knowte.server.start_searxng_job", side_effect=start_job
            ) as start:
                server = create_server("127.0.0.1", 0, config_path)
                status, payload = self._request(
                    server,
                    "POST",
                    "/api/searxng",
                    json.dumps({"action": "setup"}),
                )

            self.assertEqual(status, 202)
            self.assertEqual(payload["job_id"], "setup-job")
            start.assert_called_once()
            config = config_path.read_text(encoding="utf-8")
            self.assertIn(
                "searxng_url: http://127.0.0.1:8889/search", config
            )
            self.assertIn("enabled_backends: arxiv,websearch", config)

    def test_managed_searxng_remove_forwards_image_cache_choice(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            removed = {
                "state": "not_installed",
                "installed": False,
                "removed_url": "http://127.0.0.1:8888/search",
                "image_cache_requested": True,
                "image_cache_removed": True,
            }
            with patch(
                "knowte.server.manage_searxng", return_value=removed
            ) as manage:
                server = create_server("127.0.0.1", 0, config_path)
                status, payload = self._request(
                    server,
                    "POST",
                    "/api/searxng",
                    json.dumps({"action": "remove", "remove_image": True}),
                )

        self.assertEqual(status, 200)
        self.assertTrue(payload["image_cache_removed"])
        manage.assert_called_once_with("remove", remove_image=True)

    def test_search_reports_source_counts_and_strict_web_year_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            usage_path = temp_path / "usage.json"
            config_path.write_text(
                "enabled_backends: arxiv,websearch\n"
                "searxng_url: http://127.0.0.1:8888/search\n",
                encoding="utf-8",
            )
            results = [
                {"source": "arXiv", "title": "One"},
                {"source": "arXiv", "title": "Two"},
                {"source": "Google", "title": "Three"},
            ]

            with patch.object(usage, "USAGE_DIR", temp_path), patch.object(
                usage, "USAGE_PATH", usage_path
            ), patch("knowte.server.search_papers", return_value=results):
                server = create_server("127.0.0.1", 0, config_path)
                status, payload = self._request(
                    server, "GET", "/api/search?q=alpha&year_from=2015&year_to=2018"
                )

        self.assertEqual(status, 200)
        self.assertEqual(payload["source_counts"], {"arXiv": 2, "Google": 1})
        self.assertIn("websearch_strict_year_filter", payload["warnings"])

    def test_search_reports_unavailable_web_backend(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            usage_path = temp_path / "usage.json"
            config_path.write_text(
                "enabled_backends: websearch\n"
                "searxng_url: http://127.0.0.1:8888/search\n",
                encoding="utf-8",
            )

            def unavailable_search(*args, **kwargs):
                kwargs["diagnostics"]["websearch"] = {
                    "attempted": True,
                    "fetched": 0,
                    "accepted": 0,
                    "error": "unavailable",
                }
                return []

            with patch.object(usage, "USAGE_DIR", temp_path), patch.object(
                usage, "USAGE_PATH", usage_path
            ), patch("knowte.server.search_papers", side_effect=unavailable_search):
                server = create_server("127.0.0.1", 0, config_path)
                status, payload = self._request(server, "GET", "/api/search?q=alpha")

        self.assertEqual(status, 200)
        self.assertIn("websearch_unavailable", payload["warnings"])

    def test_search_passes_web_page_count_and_reports_more_from_actual_page(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            usage_path = temp_path / "usage.json"
            config_path.write_text(
                "enabled_backends: websearch\n"
                "searxng_url: http://127.0.0.1:8888/search\n"
                "web_ignore_year_filter: true\n",
                encoding="utf-8",
            )

            def paged_search(*args, **kwargs):
                kwargs["diagnostics"]["websearch"] = {
                    "attempted": True,
                    "fetched": 13,
                    "accepted": 13,
                    "pages": [
                        {"page": 1, "returned": 7},
                        {"page": 2, "returned": 6},
                    ],
                    "has_more": True,
                }
                return [{"source": "brave", "title": "Alpha"}]

            with patch.object(usage, "USAGE_DIR", temp_path), patch.object(
                usage, "USAGE_PATH", usage_path
            ), patch(
                "knowte.server.search_papers", side_effect=paged_search
            ) as search:
                server = create_server("127.0.0.1", 0, config_path)
                status, payload = self._request(
                    server,
                    "GET",
                    "/api/search?q=alpha&limit=100&web_pages=2",
                )

        self.assertEqual(status, 200)
        self.assertEqual(search.call_args.kwargs["web_pages"], 2)
        self.assertEqual(payload["web_pages"], 2)
        self.assertTrue(payload["can_find_more"])
        self.assertEqual(
            [page["returned"] for page in payload["search_diagnostics"]["websearch"]["pages"]],
            [7, 6],
        )

    def test_empty_query_is_rejected_without_recording_usage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.yml"
            usage_path = temp_path / "usage.json"
            config_path.write_text("enabled_backends: arxiv\n", encoding="utf-8")

            with patch.object(usage, "USAGE_DIR", temp_path), patch.object(
                usage, "USAGE_PATH", usage_path
            ), patch("knowte.server.search_papers") as search:
                server = create_server("127.0.0.1", 0, config_path)
                status, payload = self._request(server, "GET", "/api/search?q=%20%20")

        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "empty_query")
        self.assertEqual(payload["usage"]["last_day"], 0)
        search.assert_not_called()

    def test_config_does_not_return_api_key_and_blank_update_preserves_it(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            config_path.write_text(
                "semanticscholar_api_key: secret-value\nemail: old@example.com\n",
                encoding="utf-8",
            )

            server = create_server("127.0.0.1", 0, config_path)
            status, payload = self._request(server, "GET", "/api/config")
            self.assertEqual(status, 200)
            self.assertEqual(payload["semanticscholar_api_key"], "")
            self.assertTrue(payload["semanticscholar_api_key_configured"])

            server = create_server("127.0.0.1", 0, config_path)
            status, payload = self._request(
                server,
                "POST",
                "/api/config",
                json.dumps({"email": "new@example.com", "enabled_backends": ["arxiv"]}),
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["semanticscholar_api_key_configured"])
            self.assertIn(
                "semanticscholar_api_key: secret-value",
                config_path.read_text(encoding="utf-8"),
            )

            server = create_server("127.0.0.1", 0, config_path)
            status, payload = self._request(
                server,
                "POST",
                "/api/config",
                json.dumps({"semanticscholar_api_key": ""}),
            )
            self.assertEqual(status, 200)
            self.assertFalse(payload["semanticscholar_api_key_configured"])
            self.assertNotIn(
                "semanticscholar_api_key:", config_path.read_text(encoding="utf-8")
            )

    def test_config_rejects_empty_backend_selection_without_overwriting_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            original = "enabled_backends: arxiv\nmax_papers: 100\n"
            config_path.write_text(original, encoding="utf-8")

            server = create_server("127.0.0.1", 0, config_path)
            status, payload = self._request(
                server,
                "POST",
                "/api/config",
                json.dumps({"enabled_backends": []}),
            )

            self.assertEqual(status, 400)
            self.assertEqual(payload["error"], "no_search_backends")
            self.assertEqual(config_path.read_text(encoding="utf-8"), original)

    def test_config_persists_web_year_filter_exemption(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            server = create_server("127.0.0.1", 0, config_path)
            status, payload = self._request(
                server,
                "POST",
                "/api/config",
                json.dumps(
                    {
                        "enabled_backends": ["websearch"],
                        "searxng_url": "http://127.0.0.1:8888/search",
                        "web_ignore_year_filter": True,
                    }
                ),
            )

            self.assertEqual(status, 200)
            self.assertTrue(payload["web_ignore_year_filter"])
            self.assertIn(
                "web_ignore_year_filter: true",
                config_path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
