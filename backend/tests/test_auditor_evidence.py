"""Unit tests for spatial numeric evidence verifier and confidence scoring."""

import unittest

from src.auditors.evidence_verifier import (
    compute_combined_confidence,
    verify_spatial_numeric_evidence,
)


class TestAuditorEvidence(unittest.TestCase):
    def test_verify_spatial_numeric_evidence_vector_text_match(self):
        """Value present in raw page text achieves VECTOR_TEXT_AND_VISION tier."""
        pages = [{"n": 1, "text": "GROUND FLOOR PLAN\nCLEAR FRONT SETBACK: 10'-0\"\nREAR: 5'-0\"", "hints": []}]
        res = verify_spatial_numeric_evidence(
            val_key="front_setback_ft", val_num=10.0, raw_evidence="10'-0\" FRONT SETBACK", page_num=1, pages_list=pages
        )
        self.assertEqual(res["tier"], "VECTOR_TEXT_AND_VISION")
        self.assertEqual(res["multiplier"], 1.0)
        self.assertTrue(res["verified"])

    def test_verify_spatial_numeric_evidence_inferred(self):
        """Value absent from both text and hints falls back to UNVERIFIED_OR_DISCREPANCY tier."""
        pages = [{"n": 1, "text": "GROUND FLOOR PLAN WITH NO BOUNDARY WALL DATA", "hints": []}]
        res = verify_spatial_numeric_evidence(
            val_key="boundary_wall_height_ft", val_num=7.0, raw_evidence="Wall height 7ft", page_num=1, pages_list=pages
        )
        self.assertEqual(res["tier"], "UNVERIFIED_OR_DISCREPANCY")
        self.assertFalse(res["verified"])
        self.assertEqual(res["multiplier"], 0.45)

    def test_compute_combined_confidence(self):
        """Combined confidence blends AI confidence and source multiplier."""
        score_high = compute_combined_confidence(
            decision_conf=0.95, probabilities={}, source_multiplier=1.0, obs_seen="yes", has_evidence=True
        )
        score_low = compute_combined_confidence(
            decision_conf=0.50, probabilities={}, source_multiplier=0.45, obs_seen="unclear", has_evidence=False
        )
        self.assertGreater(score_high, score_low)
        self.assertLessEqual(score_high, 1.0)
        self.assertGreaterEqual(score_low, 0.0)


if __name__ == "__main__":
    unittest.main()
