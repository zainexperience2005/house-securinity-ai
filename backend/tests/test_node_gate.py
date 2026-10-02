"""Unit tests for n_gate node in House Scrutiny pipeline."""

import unittest
from unittest.mock import patch

from src.pipeline.nodes import n_gate


class TestNodeGate(unittest.TestCase):
    def test_n_gate_empty_pages(self):
        """Empty page list immediately resolves to UNSUPPORTED_DOCUMENT."""
        state = {"pages": []}
        res = n_gate(state)
        self.assertEqual(res["document_eligibility"], "UNSUPPORTED_DOCUMENT")
        self.assertFalse(res["doc_type"]["has_architectural"])
        self.assertFalse(res["doc_type"]["has_structural"])

    @patch("src.pipeline.nodes.jev_call")
    def test_n_gate_eligible_architectural(self, mock_jev):
        """Architectural drawing classification marks submission as ELIGIBLE."""
        mock_jev.return_value = (
            {"page_1_type": {"choice": "architectural_drawing", "confidence": 0.96}},
            {"input_tokens": 100, "output_tokens": 20},
        )
        state = {
            "pages": [
                {
                    "n": 1,
                    "text": "GROUND FLOOR PLAN",
                    "heads": [("GROUND FLOOR PLAN", 16, (0, 0, 100, 20))],
                    "hints": [],
                }
            ],
            "meta": {},
        }
        res = n_gate(state)
        self.assertEqual(res["document_eligibility"], "ELIGIBLE")
        self.assertTrue(res["doc_type"]["has_architectural"])
        self.assertEqual(res["doc_type"]["architectural_pages"], [1])

    @patch("src.pipeline.nodes.jev_call")
    def test_n_gate_eligible_structural(self, mock_jev):
        """Structural drawing classification marks submission as ELIGIBLE."""
        mock_jev.return_value = (
            {"page_1_type": {"choice": "structural_drawing", "confidence": 0.94}},
            {"input_tokens": 100, "output_tokens": 20},
        )
        state = {"pages": [{"n": 1, "text": "COLUMN SCHEDULE & BEAM REBAR", "heads": [], "hints": []}], "meta": {}}
        res = n_gate(state)
        self.assertEqual(res["document_eligibility"], "ELIGIBLE")
        self.assertTrue(res["doc_type"]["has_structural"])
        self.assertEqual(res["doc_type"]["structural_pages"], [1])

    @patch("src.pipeline.nodes.jev_call")
    def test_n_gate_ineligible_other_document(self, mock_jev):
        """Non-drawing files (invoices, resumes, general text) mark document UNSUPPORTED_DOCUMENT."""
        mock_jev.return_value = (
            {"page_1_type": {"choice": "other", "confidence": 0.90}},
            {"input_tokens": 80, "output_tokens": 15},
        )
        state = {"pages": [{"n": 1, "text": "TAX INVOICE AND PAYMENT RECEIPT", "heads": [], "hints": []}], "meta": {}}
        res = n_gate(state)
        self.assertEqual(res["document_eligibility"], "UNSUPPORTED_DOCUMENT")
        self.assertFalse(res["doc_type"]["has_architectural"])
        self.assertFalse(res["doc_type"]["has_structural"])

    @patch("src.pipeline.nodes.jev_call")
    def test_n_gate_classification_error_handling(self, mock_jev):
        """When Jev returns an error, status becomes CLASSIFICATION_UNAVAILABLE."""
        mock_jev.return_value = (
            {"page_1_type": {"choice": "other", "confidence": 0.0, "error": "Upstream service timeout"}},
            {"input_tokens": 0, "output_tokens": 0},
        )
        state = {"pages": [{"n": 1, "text": "SOME CONTENT", "heads": [], "hints": []}], "meta": {}}
        res = n_gate(state)
        self.assertEqual(res["document_eligibility"], "CLASSIFICATION_UNAVAILABLE")
        self.assertIsNotNone(res["doc_type"]["classification_error"])


if __name__ == "__main__":
    unittest.main()
