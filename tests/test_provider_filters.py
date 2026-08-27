import json
import unittest
from unittest.mock import MagicMock, patch

from knowte.providers import websearch
from knowte.providers.arxiv import search_arxiv
from knowte.providers.openalex import _fetch_openalex, search_openalex
from knowte.providers.semanticscholar import _fetch_semanticscholar
from knowte.providers.websearch import search_web
from knowte.models import Paper
from knowte import search as search_module
from knowte.search import _allocate_quotas, _source_weights, search_papers


class ProviderYearFilterTests(unittest.TestCase):
    def setUp(self):
        websearch._PAGE_CACHE.clear()
        search_module._ACADEMIC_CACHE.clear()

    def test_source_weight_matrix_and_equal_academic_split(self):
        self.assertEqual(
            _allocate_quotas(
                10,
                _source_weights(
                    ["arxiv", "openalex", "semanticscholar"], True
                ),
            ),
            {"arxiv": 3, "openalex": 3, "semanticscholar": 3, "websearch": 1},
        )
        self.assertEqual(
            _allocate_quotas(
                10, _source_weights(["arxiv", "openalex"], True)
            ),
            {"arxiv": 4, "openalex": 4, "websearch": 2},
        )
        self.assertEqual(
            _allocate_quotas(10, _source_weights(["arxiv"], True)),
            {"arxiv": 7, "websearch": 3},
        )
        self.assertEqual(
            _allocate_quotas(
                10,
                _source_weights(
                    ["arxiv", "openalex", "semanticscholar"], False
                ),
            ),
            {"arxiv": 4, "openalex": 3, "semanticscholar": 3},
        )

    def test_web_provider_reports_unavailable_service(self):
        diagnostics = {}
        with patch(
            "knowte.providers.websearch.urlopen", side_effect=OSError
        ) as urlopen:
            results = search_web(
                "alpha",
                base_url="https://searx.example.test/search",
                diagnostics=diagnostics,
            )

        self.assertEqual(results, [])
        self.assertEqual(diagnostics["error"], "unavailable")
        self.assertEqual(diagnostics["fetched"], 0)
        request = urlopen.call_args.args[0]
        self.assertNotIn("language=", request.full_url)

    def test_web_provider_includes_non_empty_language(self):
        with patch("knowte.providers.websearch.urlopen", side_effect=OSError) as urlopen:
            search_web(
                "alpha",
                base_url="https://searx.example.test/search",
                language="en-US",
            )

        request = urlopen.call_args.args[0]
        self.assertIn("language=en-US", request.full_url)

    def test_web_pages_use_actual_response_counts_and_cache_previous_pages(self):
        def response(items):
            context = MagicMock()
            context.__enter__.return_value.read.return_value = json.dumps(
                {"results": items}
            ).encode("utf-8")
            return context

        page_items = {
            1: [
                {"title": f"Alpha page one {index}", "url": f"https://one/{index}"}
                for index in range(3)
            ],
            2: [{"title": "Alpha page two", "url": "https://two/1"}],
            3: [],
        }

        def open_page(request, timeout=10):
            page = int(request.full_url.split("pageno=")[1].split("&")[0])
            return response(page_items[page])

        diagnostics = {}
        with patch(
            "knowte.providers.websearch.urlopen", side_effect=open_page
        ) as urlopen:
            first = search_web(
                "alpha",
                limit=None,
                base_url="https://searx.example.test/search",
                pages=2,
                diagnostics=diagnostics,
            )
            second = search_web(
                "alpha",
                limit=None,
                base_url="https://searx.example.test/search",
                pages=3,
            )

        self.assertEqual(len(first), 4)
        self.assertEqual([page["returned"] for page in diagnostics["pages"]], [3, 1])
        self.assertEqual(len(second), 4)
        self.assertEqual(urlopen.call_count, 3)

    def test_web_cache_can_be_read_when_external_requests_are_disallowed(self):
        context = MagicMock()
        context.__enter__.return_value.read.return_value = json.dumps(
            {
                "results": [
                    {"title": "Alpha cached result", "url": "https://example.test/a"}
                ]
            }
        ).encode("utf-8")

        with patch("knowte.providers.websearch.urlopen", return_value=context) as urlopen:
            search_web(
                "alpha",
                limit=None,
                base_url="https://searx.example.test/search",
            )
            diagnostics = {}
            cached = search_web(
                "alpha",
                limit=None,
                base_url="https://searx.example.test/search",
                allow_external=False,
                diagnostics=diagnostics,
            )

        self.assertEqual(len(cached), 1)
        self.assertEqual(urlopen.call_count, 1)
        self.assertEqual(diagnostics["external_requests"], 0)
        self.assertEqual(diagnostics["cache_hits"], 1)

    def test_empty_web_response_is_not_cached(self):
        context = MagicMock()
        context.__enter__.return_value.read.return_value = json.dumps(
            {"results": []}
        ).encode("utf-8")

        with patch(
            "knowte.providers.websearch.urlopen", return_value=context
        ) as urlopen:
            first_diagnostics = {}
            second_diagnostics = {}
            first = search_web(
                "alpha",
                limit=None,
                base_url="https://searx.example.test/search",
                diagnostics=first_diagnostics,
            )
            second = search_web(
                "alpha",
                limit=None,
                base_url="https://searx.example.test/search",
                diagnostics=second_diagnostics,
            )

        self.assertEqual(first, [])
        self.assertEqual(second, [])
        self.assertEqual(urlopen.call_count, 2)
        self.assertTrue(first_diagnostics["empty_response"])
        self.assertEqual(second_diagnostics["cache_hits"], 0)

    def test_web_results_can_be_exempted_from_year_filter(self):
        undated_web_result = Paper(
            id="https://example.test/alpha",
            title="Alpha web result",
            authors="Web",
            year=0,
            abstract="Alpha summary",
            url="https://example.test/alpha",
            keywords=[],
            source="Web",
        )
        with patch("knowte.search.search_web", return_value=[undated_web_result]):
            strict = search_papers(
                "alpha",
                backends=["websearch"],
                searxng_url="http://127.0.0.1:8888/search",
                year_from=2015,
                year_to=2018,
            )
            exempt = search_papers(
                "alpha",
                backends=["websearch"],
                searxng_url="http://127.0.0.1:8888/search",
                year_from=2015,
                year_to=2018,
                web_ignore_year_filter=True,
            )

        self.assertEqual(strict, [])
        self.assertEqual([result["id"] for result in exempt], [undated_web_result.id])

    def test_web_results_trust_searxng_relevance_instead_of_requiring_every_word(self):
        result = Paper(
            id="https://example.test/alphago",
            title="AlphaGo combines reinforcement learning and tree search",
            authors="Web", year=2016,
            abstract="An overview of the system architecture.",
            url="https://example.test/alphago", keywords=[], source="Web",
        )
        with patch("knowte.search.search_web", return_value=[result]):
            selected = search_papers(
                "How does AlphaGo combine reinforcement learning with tree search",
                backends=["websearch"],
                searxng_url="http://127.0.0.1:8888/search",
            )
        self.assertEqual([item["id"] for item in selected], [result.id])

    def test_arxiv_receives_year_range_and_capped_limit(self):
        with patch("knowte.providers.arxiv.urlopen", side_effect=OSError) as urlopen:
            search_arxiv("alpha", limit=300, year_from=2010, year_to=2018)

        url = urlopen.call_args.args[0]
        self.assertIn("max_results=100", url)
        self.assertIn("submittedDate:%5B201001010000+TO+201812312359%5D", url)

    def test_openalex_receives_date_filters_and_capped_limit(self):
        with patch("knowte.providers.openalex.urlopen", side_effect=OSError) as urlopen:
            _fetch_openalex(
                "alpha",
                email=None,
                limit=300,
                year_from=2010,
                year_to=2018,
            )

        url = urlopen.call_args.args[0]
        self.assertIn("per_page=100", url)
        self.assertIn("from_publication_date%3A2010-01-01", url)
        self.assertIn("to_publication_date%3A2018-12-31", url)

    def test_semantic_scholar_receives_year_range_and_capped_limit(self):
        with patch(
            "knowte.providers.semanticscholar.urlopen", side_effect=OSError
        ) as urlopen:
            _fetch_semanticscholar(
                "alpha",
                limit=300,
                year_from=2010,
                year_to=2018,
            )

        request = urlopen.call_args.args[0]
        self.assertIn("limit=100", request.full_url)
        self.assertIn("year=2010-2018", request.full_url)

    def test_openalex_area_search_uses_area_terms_in_query(self):
        with patch(
            "knowte.providers.openalex._fetch_openalex", return_value=[]
        ) as fetch:
            search_openalex(
                "alpha",
                email=None,
                concepts=["Artificial intelligence", "Machine learning"],
                query_boosts=["artificial intelligence"],
                year_to=2018,
            )

        queries = [call.args[0] for call in fetch.call_args_list]
        concepts = [call.args[3] for call in fetch.call_args_list]
        self.assertEqual(
            queries,
            ["alpha Artificial intelligence", "alpha Machine learning"],
        )
        self.assertEqual(concepts, [None, None])

    @patch("knowte.search.search_semanticscholar", return_value=[])
    @patch("knowte.search.search_openalex", return_value=[])
    @patch("knowte.search.search_arxiv", return_value=[])
    def test_search_passes_years_to_paper_providers(
        self, arxiv, openalex, semanticscholar
    ):
        search_papers(
            "alpha",
            limit=100,
            areas=["ai.general"],
            backends=["arxiv", "openalex", "semanticscholar"],
            year_to=2018,
        )

        arxiv.assert_called_once_with(
            "alpha", limit=100, categories=["cs.AI"], year_from=None, year_to=2018
        )
        self.assertEqual(openalex.call_args.kwargs["year_to"], 2018)
        self.assertEqual(semanticscholar.call_args.kwargs["year_to"], 2018)

    def test_mixed_sources_follow_three_three_three_one_allocation(self):
        def papers(prefix, source, count):
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
                for index in range(count)
            ]

        diagnostics = {}
        with patch("knowte.search.search_arxiv", return_value=papers("a", "arXiv", 10)), patch(
            "knowte.search.search_openalex",
            return_value=papers("o", "OpenAlex", 10),
        ), patch(
            "knowte.search.search_semanticscholar",
            return_value=papers("s", "Semantic Scholar", 10),
        ), patch(
            "knowte.search.search_web", return_value=papers("w", "brave", 10)
        ):
            results = search_papers(
                "alpha",
                limit=10,
                backends=["arxiv", "openalex", "semanticscholar", "websearch"],
                searxng_url="http://127.0.0.1:8888/search",
                web_ignore_year_filter=True,
                diagnostics=diagnostics,
            )

        self.assertEqual(len(results), 10)
        self.assertEqual(
            diagnostics["allocation"]["selected"],
            {"arxiv": 3, "openalex": 3, "semanticscholar": 3, "websearch": 1},
        )

    def test_find_more_reuses_academic_candidates_without_external_request(self):
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

        first_diagnostics = {}
        second_diagnostics = {}
        with patch(
            "knowte.search.search_arxiv", return_value=papers("a", "arXiv")
        ) as arxiv, patch(
            "knowte.search.search_openalex", return_value=papers("o", "OpenAlex")
        ) as openalex, patch(
            "knowte.search.search_semanticscholar",
            return_value=papers("s", "Semantic Scholar"),
        ) as semanticscholar:
            first = search_papers(
                "alpha",
                limit=60,
                backends=["arxiv", "openalex", "semanticscholar"],
                diagnostics=first_diagnostics,
            )
            second = search_papers(
                "alpha",
                limit=120,
                backends=["arxiv", "openalex", "semanticscholar"],
                allow_paper_external=False,
                diagnostics=second_diagnostics,
            )

        self.assertEqual(len(first), 60)
        self.assertEqual(len(second), 120)
        arxiv.assert_called_once()
        openalex.assert_called_once()
        semanticscholar.assert_called_once()
        self.assertTrue(first_diagnostics["academic"]["external_request"])
        self.assertTrue(second_diagnostics["academic"]["cache_hit"])
        self.assertFalse(second_diagnostics["academic"]["external_request"])

    def test_academic_cache_miss_respects_external_request_limit(self):
        diagnostics = {}
        with patch("knowte.search.search_arxiv") as arxiv:
            results = search_papers(
                "uncached alpha",
                limit=20,
                backends=["arxiv"],
                allow_paper_external=False,
                diagnostics=diagnostics,
            )

        self.assertEqual(results, [])
        arxiv.assert_not_called()
        self.assertTrue(diagnostics["academic"]["rate_limited"])

    def test_academic_results_fill_short_web_quota(self):
        academic = [
            Paper(
                id=f"a-{index}",
                title=f"Alpha academic {index}",
                authors="Author",
                year=2020,
                abstract="alpha",
                url=f"https://example.test/a/{index}",
                keywords=[],
                source="arXiv",
            )
            for index in range(10)
        ]
        web = [
            Paper(
                id="w-1",
                title="Alpha web",
                authors="Web",
                year=0,
                abstract="alpha",
                url="https://example.test/web",
                keywords=[],
                source="brave",
            )
        ]
        diagnostics = {}
        with patch("knowte.search.search_arxiv", return_value=academic), patch(
            "knowte.search.search_web", return_value=web
        ):
            results = search_papers(
                "alpha",
                limit=10,
                backends=["arxiv", "websearch"],
                searxng_url="http://127.0.0.1:8888/search",
                web_ignore_year_filter=True,
                diagnostics=diagnostics,
            )

        self.assertEqual(len(results), 10)
        self.assertEqual(diagnostics["allocation"]["quotas"]["websearch"], 3)
        self.assertEqual(diagnostics["allocation"]["selected"]["websearch"], 1)
        self.assertEqual(diagnostics["allocation"]["selected"]["arxiv"], 9)

    def test_duplicate_academic_records_merge_paper_pdf_and_doi_links(self):
        arxiv = Paper(
            id="arxiv-1",
            title="Alpha shared paper",
            authors="Author",
            year=2020,
            abstract="alpha",
            url="https://arxiv.org/abs/1",
            keywords=[],
            source="arXiv",
            paper_url="https://arxiv.org/abs/1",
            pdf_url="https://arxiv.org/pdf/1",
        )
        openalex = Paper(
            id="openalex-1",
            title="Alpha shared paper",
            authors="Author",
            year=2020,
            abstract="alpha",
            url="https://openalex.org/W1",
            keywords=[],
            source="OpenAlex",
            paper_url="https://publisher.example/paper",
            doi_url="https://doi.org/10.1000/example",
        )
        with patch("knowte.search.search_arxiv", return_value=[arxiv]), patch(
            "knowte.search.search_openalex", return_value=[openalex]
        ):
            results = search_papers(
                "alpha",
                limit=20,
                backends=["arxiv", "openalex"],
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["paper_url"], "https://arxiv.org/abs/1")
        self.assertEqual(results[0]["pdf_url"], "https://arxiv.org/pdf/1")
        self.assertEqual(
            results[0]["doi_url"], "https://doi.org/10.1000/example"
        )

    def test_web_only_ignores_academic_n_and_returns_actual_page_results(self):
        web = [
            Paper(
                id=f"w-{index}",
                title=f"Alpha web {index}",
                authors="Web",
                year=0,
                abstract="alpha",
                url=f"https://example.test/web/{index}",
                keywords=[],
                source="brave",
            )
            for index in range(7)
        ]
        with patch("knowte.search.search_web", return_value=web):
            results = search_papers(
                "alpha",
                limit=100,
                backends=["websearch"],
                searxng_url="http://127.0.0.1:8888/search",
                web_ignore_year_filter=True,
            )

        self.assertEqual(len(results), 7)


if __name__ == "__main__":
    unittest.main()
