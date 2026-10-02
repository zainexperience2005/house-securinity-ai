"""Unit tests for submission completeness auditor."""

import unittest

from src.auditors.completeness_model import evaluate_document_completeness


class TestAuditorCompleteness(unittest.TestCase):
    def test_completeness_complete_submission(self):
        """Submission containing all mandatory architectural and structural disciplines is COMPLETE."""
        dt_summary = {"has_architectural": True, "has_structural": True, "has_stability_certificate": True}
        checks = {
            "site_plan": {"status": "PASS", "page": 1},
            "floor_plans": {"status": "PASS", "page": 2},
            "sections_elevations": {"status": "PASS", "page": 3},
            "foundation_plan": {"status": "PASS", "page": 4},
            "column_schedule": {"status": "PASS", "page": 4},
            "stability_cert": {"status": "PASS", "page": 5},
        }
        pages = [{"n": i, "text": f"Page {i}", "heads": []} for i in range(1, 6)]
        sheet_audit = {"has_numbering": True, "missing_sheets": []}

        res = evaluate_document_completeness(dt_summary, checks, pages, sheet_audit)
        self.assertEqual(res["completeness_status"], "COMPLETE")
        self.assertEqual(res["completeness_score_pct"], 100.0)
        self.assertEqual(len(res["missing_components"]), 0)

    def test_completeness_missing_stability_certificate(self):
        """Missing stability certificate results in PARTIALLY_COMPLETE status."""
        dt_summary = {"has_architectural": True, "has_structural": True, "has_stability_certificate": False}
        checks = {
            "site_plan": {"status": "PASS", "page": 1},
            "floor_plans": {"status": "PASS", "page": 2},
            "sections_elevations": {"status": "PASS", "page": 3},
            "foundation_plan": {"status": "PASS", "page": 4},
            "column_schedule": {"status": "PASS", "page": 4},
        }
        pages = [{"n": i, "text": f"Page {i}", "heads": []} for i in range(1, 5)]
        sheet_audit = {"has_numbering": True, "missing_sheets": []}

        res = evaluate_document_completeness(dt_summary, checks, pages, sheet_audit)
        self.assertEqual(res["completeness_status"], "PARTIALLY_COMPLETE")
        self.assertTrue(any("Stability Certificate" in m["name"] for m in res["missing_components"]))


if __name__ == "__main__":
    unittest.main()
