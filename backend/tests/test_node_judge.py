"""Unit tests for n_judge node in House Scrutiny pipeline."""

import unittest
from unittest.mock import patch

from src.pipeline.nodes import n_judge


class TestNodeJudge(unittest.TestCase):
    @patch("src.pipeline.nodes.jev_call")
    def test_n_judge_architectural_only_checklist(self, mock_jev):
        """When only architectural plans are submitted, only architectural checklist items are queried."""
        mock_jev.return_value = (
            {
                "site_plan": {"choice": "PASS", "confidence": 0.95, "reason": "Clearly demarcated on page 1"},
                "front_setback": {"choice": "PASS", "confidence": 0.92, "reason": "10ft setback meets minimum 5ft"},
            },
            {"input_tokens": 300, "output_tokens": 80},
        )
        state = {
            "doc_type": {
                "has_architectural": True,
                "has_structural": False,
                "has_stability_certificate": False,
                "architectural_pages": [1],
                "page_types": {1: {"choice": "architectural_drawing"}},
            },
            "extraction": {
                "observations": [{"check_id": "site_plan", "seen": "yes", "evidence": "Site plan drawn", "page": 1}],
                "values": [{"key": "front_setback_ft", "value": 10.0}],
                "structural_values": [],
                "certificate_details": None,
            },
            "pages": [{"n": 1, "text": "ARCHITECTURAL SITE PLAN"}],
        }
        res = n_judge(state)
        self.assertIn("checks", res)
        self.assertIn("active_checklist", res)
        self.assertIn("site_plan", res["checks"])
        self.assertEqual(res["checks"]["site_plan"]["choice"], "PASS")
        self.assertEqual(res["jev_judge_usage"]["input_tokens"], 300)

    @patch("src.pipeline.nodes.jev_call")
    def test_n_judge_includes_structural_and_certificate(self, mock_jev):
        """When structural and certificate are present, their checklists are included in the audit."""
        mock_jev.return_value = (
            {
                "foundation_plan": {"choice": "PASS", "confidence": 0.9},
                "stability_cert": {"choice": "PASS", "confidence": 0.9},
            },
            {"input_tokens": 400, "output_tokens": 100},
        )
        state = {
            "doc_type": {
                "has_architectural": True,
                "has_structural": True,
                "has_stability_certificate": True,
                "architectural_pages": [1],
                "structural_pages": [2],
                "certificate_pages": [3],
                "page_types": {},
            },
            "extraction": {
                "observations": [],
                "values": [],
                "structural_values": [{"key": "concrete_grade_psi", "value": 3000}],
                "certificate_details": {"certificate_present": True},
            },
            "pages": [{"n": 1, "text": "P1"}, {"n": 2, "text": "P2"}, {"n": 3, "text": "P3"}],
        }
        res = n_judge(state)
        checklist = res["active_checklist"]
        # Must include both structural and certificate checklist items
        self.assertIn("foundation_plan", checklist)
        self.assertIn("stability_cert", checklist)


if __name__ == "__main__":
    unittest.main()
