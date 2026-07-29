import unittest
from unittest.mock import MagicMock, patch

from knowte.ai import AIError
from knowte.intelligent import intelligent_search


class IntelligentSearchTests(unittest.TestCase):
    def test_verification_stops_after_reaching_intelligent_result_target(self):
        candidates = [
            {
                "id": f"paper-{index}",
                "title": f"Paper {index}",
                "abstract": "Relevant.",
                "source": "OpenAlex",
                "result_type": "paper",
            }
            for index in range(10)
        ]
        client = MagicMock()
        with patch(
            "knowte.intelligent._client_from_config",
            return_value=client,
        ), patch(
            "knowte.intelligent._expand_queries",
            return_value=[],
        ), patch(
            "knowte.intelligent._verify",
            side_effect=lambda _client, _query, _areas, batch: batch,
        ) as verify, patch(
            "knowte.intelligent.search_papers",
            return_value=candidates,
        ) as retrieve:
            result = intelligent_search(
                "relevant research",
                {
                    "ai_base_url": "https://ai.test/v1",
                    "ai_chat_model": "chat",
                    "max_papers": "40",
                    "ai_verify_batch_size": "2",
                    "ai_verify_concurrency": "1",
                },
                2,
                ["openalex"],
                [],
                None,
                None,
            )

        self.assertEqual(result["count"], 2)
        self.assertEqual(retrieve.call_args.kwargs["limit"], 40)
        self.assertEqual(verify.call_count, 1)
        self.assertEqual(result["stages"]["verify"]["requests"], 1)

    def test_academic_expands_ranks_and_verifies_while_web_skips_embedding(self):
        academic = {
            "id": "paper-1",
            "title": "Planning transfer",
            "authors": "A",
            "year": 2024,
            "abstract": "Transfers planning to robotics.",
            "url": "https://paper.test",
            "keywords": [],
            "source": "OpenAlex",
            "result_type": "paper",
        }
        web = {
            "id": "web-1",
            "title": "Robotics report",
            "authors": "Web",
            "year": 2025,
            "abstract": "A report.",
            "url": "https://web.test",
            "keywords": [],
            "source": "Web",
            "result_type": "web",
        }

        def search(query, **kwargs):
            return [web] if kwargs["backends"] == ["websearch"] else [academic]

        ranked = [{**academic, "semantic_score": 0.9}]
        verified = [
            {
                **ranked[0],
                "verification_score": 0.95,
                "match_reason": "Matches the transfer intent.",
                "discovery_path": "Expanded academic recall → semantic ranking → LLM verify",
            },
            {
                **web,
                "verification_score": 0.8,
                "match_reason": "Supports the real-world application.",
                "discovery_path": "Web recall → LLM verify",
            },
        ]
        with patch(
            "knowte.intelligent._client_from_config",
            return_value=MagicMock(),
        ), patch(
            "knowte.intelligent._expand_queries",
            return_value=["planning transfer robotics"],
        ), patch(
            "knowte.intelligent._rank_academic",
            return_value=(ranked, 1, 0),
        ) as rank, patch(
            "knowte.intelligent._verify",
            return_value=verified,
        ) as verify, patch(
            "knowte.intelligent.search_papers",
            side_effect=search,
        ) as retrieve:
            result = intelligent_search(
                "AlphaGo planning outside games",
                {
                    "ai_base_url": "https://ai.test/v1",
                    "ai_chat_model": "chat",
                    "ai_embedding_model": "embed",
                    "searxng_url": "http://127.0.0.1:8888/search",
                },
                20,
                ["openalex", "websearch"],
                ["ai.rl"],
                2015,
                None,
            )

        self.assertEqual(result["count"], 2)
        self.assertEqual(
            result["request_budget"],
            {
                "retrieval": 3,
                "academic_retrieval": 2,
                "web_retrieval": 1,
                "chat": 2,
                "embedding": 1,
            },
        )
        self.assertEqual(retrieve.call_count, 3)
        self.assertTrue(
            all(call.kwargs["strict_match"] is False for call in retrieve.call_args_list)
        )
        ranked_candidates = rank.call_args.args[2]
        self.assertTrue(
            all(candidate["result_type"] == "paper" for candidate in ranked_candidates)
        )
        verified_candidates = verify.call_args.args[3]
        self.assertEqual(
            {candidate["result_type"] for candidate in verified_candidates},
            {"paper", "web"},
        )

    def test_web_only_requires_chat_but_not_embedding_configuration(self):
        web = {
            "id": "web-1",
            "title": "Web result",
            "authors": "Web",
            "year": 0,
            "abstract": "Relevant snippet.",
            "url": "https://web.test",
            "keywords": [],
            "source": "Web",
            "result_type": "web",
        }
        with patch(
            "knowte.intelligent._client_from_config",
            return_value=MagicMock(),
        ) as client_factory, patch(
            "knowte.intelligent.search_papers",
            return_value=[web],
        ), patch(
            "knowte.intelligent._verify",
            return_value=[
                {
                    **web,
                    "match_reason": "Verified.",
                    "discovery_path": "Web recall → LLM verify",
                }
            ],
        ):
            result = intelligent_search(
                "current robotics deployment",
                {
                    "ai_base_url": "https://ai.test/v1",
                    "ai_chat_model": "chat",
                    "searxng_url": "http://127.0.0.1:8888/search",
                },
                20,
                ["websearch"],
                [],
                None,
                None,
            )

        client_factory.assert_called_once()
        self.assertFalse(client_factory.call_args.kwargs["require_embedding"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["request_budget"]["embedding"], 0)

    def test_academic_search_can_continue_without_embedding_model(self):
        academic = {
            "id": "paper-1",
            "title": "Planning transfer",
            "authors": "A",
            "year": 2024,
            "abstract": "Transfers planning to robotics.",
            "url": "https://paper.test",
            "keywords": [],
            "source": "OpenAlex",
            "result_type": "paper",
        }
        client = MagicMock()
        client.embedding_model = ""
        client.usage_snapshot.return_value = {
            "chat_requests": 2,
            "chat_tokens": 30,
            "embedding_requests": 0,
            "embedding_tokens": 0,
        }
        with patch(
            "knowte.intelligent._client_from_config",
            return_value=client,
        ), patch(
            "knowte.intelligent._expand_queries",
            return_value=[],
        ), patch(
            "knowte.intelligent._rank_academic",
        ) as rank, patch(
            "knowte.intelligent._verify",
            return_value=[academic],
        ), patch(
            "knowte.intelligent.search_papers",
            return_value=[academic],
        ):
            result = intelligent_search(
                "planning transfer",
                {
                    "ai_base_url": "http://192.168.1.12:8000/v1",
                    "ai_chat_model": "local-model",
                },
                20,
                ["openalex"],
                [],
                None,
                None,
            )

        rank.assert_not_called()
        self.assertIn("embedding_unconfigured", result["warnings"])
        self.assertEqual(result["stages"]["embed"]["status"], "skipped")
        self.assertEqual(result["_ai_usage"]["chat_tokens"], 30)

    def test_verification_fallback_does_not_claim_embedding_when_not_used(self):
        academic = {
            "id": "paper-1",
            "title": "Planning transfer",
            "authors": "A",
            "year": 2024,
            "abstract": "Transfers planning to robotics.",
            "url": "https://paper.test",
            "keywords": [],
            "source": "OpenAlex",
            "result_type": "paper",
        }
        client = MagicMock()
        client.embedding_model = ""
        client.usage_snapshot.return_value = {
            "chat_requests": 1,
            "chat_tokens": 20,
            "embedding_requests": 0,
            "embedding_tokens": 0,
        }
        with patch(
            "knowte.intelligent._client_from_config",
            return_value=client,
        ), patch(
            "knowte.intelligent._expand_queries",
            return_value=[],
        ), patch(
            "knowte.intelligent._verify",
            side_effect=AIError("timeout", "AI service did not respond within 45 seconds."),
        ), patch(
            "knowte.intelligent.search_papers",
            return_value=[academic],
        ):
            result = intelligent_search(
                "planning transfer",
                {
                    "ai_base_url": "http://192.168.1.12:8000/v1",
                    "ai_chat_model": "local-model",
                },
                20,
                ["openalex"],
                [],
                None,
                None,
            )

        fallback = result["results"][0]
        self.assertIn("failed (timeout)", fallback["match_reason"])
        self.assertIn("academic recall", fallback["match_reason"])
        self.assertNotIn("embedding ranking", fallback["match_reason"])
        self.assertEqual(result["stages"]["verify"]["error"], "timeout")
        self.assertIn("45 seconds", result["stages"]["verify"]["message"])

    def test_verification_batches_keep_successes_when_one_batch_fails(self):
        candidates = [
            {
                "id": f"paper-{index}",
                "title": f"Paper {index}",
                "abstract": "Candidate",
                "result_type": "paper",
                "source": "OpenAlex",
            }
            for index in range(5)
        ]
        client = MagicMock()
        client.embedding_model = ""
        client.usage_snapshot.return_value = {
            "chat_requests": 3,
            "chat_tokens": 100,
            "embedding_requests": 0,
            "embedding_tokens": 0,
        }

        def verify(_client, _query, _areas, batch):
            if any(item["id"] == "paper-2" for item in batch):
                raise AIError("timeout", "batch timed out")
            return [
                {
                    **item,
                    "verification_score": 0.9,
                    "match_reason": "Verified.",
                }
                for item in batch
            ]

        with patch(
            "knowte.intelligent._client_from_config",
            return_value=client,
        ), patch(
            "knowte.intelligent._expand_queries",
            return_value=[],
        ), patch(
            "knowte.intelligent._verify",
            side_effect=verify,
        ) as verify_mock, patch(
            "knowte.intelligent.search_papers",
            return_value=candidates,
        ):
            result = intelligent_search(
                "planning transfer",
                {
                    "ai_base_url": "http://192.168.1.12:8000/v1",
                    "ai_chat_model": "local-model",
                    "ai_verify_batch_size": "2",
                    "ai_verify_concurrency": "2",
                },
                20,
                ["openalex"],
                [],
                None,
                None,
            )

        self.assertEqual(verify_mock.call_count, 3)
        self.assertEqual(result["stages"]["verify"]["requests"], 3)
        self.assertEqual(result["stages"]["verify"]["completed_batches"], 2)
        self.assertEqual(result["stages"]["verify"]["failed_batches"], 1)
        self.assertEqual(result["count"], 5)
        self.assertEqual(
            sum("Verified." == item["match_reason"] for item in result["results"]),
            3,
        )


if __name__ == "__main__":
    unittest.main()
