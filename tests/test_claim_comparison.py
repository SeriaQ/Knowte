import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from knowte.knowledge import create_claim, find_claim_comparison_context


class ClaimComparisonTests(unittest.TestCase):
    def test_round_robin_deduplicates_and_reports_truncation(self):
        a, b, c, d = [{"claim_id": name} for name in "abcd"]
        evidence = [{"quote": "text", "source_id": str(i)} for i in range(3)]
        with patch("knowte.knowledge._related_claim_rankings", return_value=[[a, b, c], [a, d], []]):
            selected, report = find_claim_comparison_context(evidence, limit=2)
        self.assertEqual([item["claim_id"] for item in selected], ["a", "d"])
        self.assertEqual(report["candidate_count"], 4)
        self.assertEqual(report["covered_evidence_count"], 2)
        self.assertEqual(report["matched_evidence_count"], 2)
        self.assertTrue(report["truncated"])

    def test_per_evidence_retrieval_exceeds_twenty_without_filling_unrelated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "knowledge.db"
            expected = []
            for i in range(25):
                expected.append(create_claim({"statement": f"algorithm{i} mechanism{i}",
                    "basis": "background", "intentionally_ungrounded": True}, path)["id"])
            create_claim({"statement": "Unrelated astronomy", "basis": "background", "intentionally_ungrounded": True}, path)
            evidence = [{"quote": f"algorithm{i}", "source_id": f"source{i}"} for i in range(25)]
            selected, report = find_claim_comparison_context(evidence, limit=100, path=path)
            self.assertEqual({item["claim_id"] for item in selected}, set(expected))
            self.assertEqual(report["covered_evidence_count"], 25)
            self.assertFalse(report["truncated"])
