import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from knowte.source_discovery import discover_related_papers, semantic_scholar_id
from knowte.source_discovery import _CACHE, _COOLDOWN


class SourceDiscoveryTests(unittest.TestCase):
    def setUp(self):
        _CACHE.clear()
        _COOLDOWN.clear()

    def test_cache_and_rate_limit_cooldown_avoid_repeat_requests(self):
        seed = {"id": "seed", "url": "https://arxiv.org/abs/2309.16609"}
        with patch("knowte.source_discovery._request_json", side_effect=[
            {"data": []}, HTTPError("https://example.test", 429, "Limited", {"Retry-After": "120"}, None),
        ]) as request:
            first = discover_related_papers([seed])
            second = discover_related_papers([seed])
        self.assertEqual(request.call_count, 2)
        self.assertEqual(first["requests"], 2)
        self.assertEqual(second["requests"], 0)
        self.assertEqual(second["cache_hits"], 1)
        self.assertGreater(second["retrieval_failures"][0]["retry_after"], 0)

    def test_withheld_references_are_explicit_and_cached(self):
        seed = {"id": "seed", "url": "https://arxiv.org/abs/2309.16609"}
        with patch("knowte.source_discovery._request_json", side_effect=[
            {"data": None, "citingPaperInfo": {"disclaimer": "references elided by the publisher"}},
            {"data": []}, {"recommendedPapers": []},
        ]) as request:
            first = discover_related_papers([seed])
            second = discover_related_papers([seed])
        self.assertEqual(request.call_count, 3)
        self.assertEqual(first["retrieval_failures"][0]["code"], "provider_restricted")
        self.assertEqual(second["cache_hits"], 3)
        self.assertEqual(second["successful_requests"], 2)

    def test_failed_paths_are_not_successful_empty_results(self):
        seed = {"id": "seed", "url": "https://arxiv.org/abs/2309.16609"}
        for error, code in [
            (HTTPError("https://example.test", 429, "Limited", {}, None), "rate_limited"),
            (TimeoutError(), "timeout"),
            (ValueError("invalid JSON"), "invalid_response"),
        ]:
            self.setUp()
            with self.subTest(code=code), patch("knowte.source_discovery._request_json", side_effect=error):
                result = discover_related_papers([seed])
            self.assertEqual(result["successful_requests"], 0)
            self.assertEqual(len(result["retrieval_failures"]), 3)
            self.assertEqual(result["retrieval_failures"][0]["code"], code)

    def test_partial_and_empty_success_are_distinguishable(self):
        seed = {"id": "seed", "url": "https://arxiv.org/abs/2309.16609"}
        with patch("knowte.source_discovery._request_json", side_effect=[
            {"data": []}, TimeoutError(), {"recommendedPapers": []},
        ]):
            result = discover_related_papers([seed])
        self.assertEqual(result["successful_requests"], 2)
        self.assertEqual(len(result["retrieval_failures"]), 1)
        self.setUp()
        with patch("knowte.source_discovery._request_json", return_value={}):
            result = discover_related_papers([seed])
        self.assertEqual(result["successful_requests"], 0)

    def test_resolves_doi_and_arxiv_seed_ids(self):
        self.assertEqual(
            semantic_scholar_id({"doi_url": "https://doi.org/10.48550/arXiv.2505.09388"}),
            "ARXIV:2505.09388",
        )
        self.assertEqual(
            semantic_scholar_id({"doi_url": "https://doi.org/10.1000/example"}),
            "DOI:10.1000/example",
        )
        self.assertEqual(
            semantic_scholar_id({"url": "https://arxiv.org/abs/2412.15115v2"}),
            "ARXIV:2412.15115",
        )

    def test_merges_citation_paths_and_recommendations(self):
        paper = {
            "paperId": "b" * 40,
            "title": "Related work",
            "authors": [{"name": "A. Author"}],
            "year": 2025,
            "abstract": "Relevant abstract.",
            "externalIds": {"DOI": "10.1000/related"},
            "url": "https://www.semanticscholar.org/paper/" + "b" * 40,
            "fieldsOfStudy": ["Computer Science"],
            "openAccessPdf": {"url": "https://example.test/paper.pdf"},
        }

        def response(request, _api_key="", _timeout=15):
            url = request.full_url if hasattr(request, "full_url") else request
            if "/references?" in url:
                return {"data": [{
                    "citedPaper": paper,
                    "contexts": ["Seed builds on this method."],
                    "intents": ["background"],
                    "isInfluential": True,
                }]}
            if "/citations?" in url:
                return {"data": [{"citingPaper": paper, "contexts": [], "intents": []}]}
            return {"recommendedPapers": [paper]}

        with patch("knowte.source_discovery._request_json", side_effect=response):
            result = discover_related_papers([{
                "id": "seed",
                "title": "Seed paper",
                "url": "https://arxiv.org/abs/2412.15115",
            }])

        self.assertEqual(result["requests"], 3)
        self.assertEqual(result["successful_requests"], 3)
        self.assertEqual(len(result["candidates"]), 1)
        candidate = result["candidates"][0]
        self.assertEqual(
            {link["kind"] for link in candidate["discovery_links"]},
            {"reference", "citation", "recommendation"},
        )
        self.assertIn("Referenced by a Seed", candidate["discovery_path"])
        self.assertIn("Cites a Seed", candidate["discovery_path"])


if __name__ == "__main__":
    unittest.main()
