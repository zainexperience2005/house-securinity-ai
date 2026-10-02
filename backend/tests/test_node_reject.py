"""Unit tests for n_reject node in House Scrutiny pipeline."""

import unittest

from src.pipeline.nodes import n_reject


class TestNodeReject(unittest.TestCase):
    def test_n_reject_unreadable_pdf(self):
        """Unreadable PDF generates clean rejection message and zeroed metrics."""
        state = {"unreadable": True, "flags": ["PDF is password-protected."], "pages": [], "doc_type": {}}
        res = n_reject(state)
        verdict = res["verdict"]
        self.assertEqual(verdict["overall"], "UNSUPPORTED_DOCUMENT")
        self.assertIn("blank, unreadable", verdict["message"])
        self.assertIn("PDF is password-protected.", verdict["review_flags"])
        self.assertEqual(verdict["rejection"]["code"], "UNSUPPORTED_DOCUMENT")

    def test_n_reject_classification_unavailable(self):
        """Classification failure outputs CLASSIFICATION_UNAVAILABLE status."""
        state = {
            "document_eligibility": "CLASSIFICATION_UNAVAILABLE",
            "doc_type": {"choice": "other", "classification_error": "timeout"},
            "pages": [{"n": 1}],
            "flags": [],
        }
        res = n_reject(state)
        verdict = res["verdict"]
        self.assertEqual(verdict["overall"], "CLASSIFICATION_UNAVAILABLE")
        self.assertIn("classification service was unavailable", verdict["message"])

    def test_n_reject_certificate_only_submission(self):
        """Submitting only a stability certificate without plans triggers helpful guidance."""
        state = {
            "document_eligibility": "UNSUPPORTED_DOCUMENT",
            "doc_type": {
                "choice": "stability_certificate",
                "has_stability_certificate": True,
                "has_architectural": False,
                "has_structural": False,
                "page_types": {1: {"choice": "stability_certificate"}},
            },
            "pages": [{"n": 1}],
            "flags": [],
        }
        res = n_reject(state)
        verdict = res["verdict"]
        self.assertEqual(verdict["overall"], "UNSUPPORTED_DOCUMENT")
        self.assertIn("stability certificate is supporting evidence only", verdict["message"])

    def test_n_reject_general_non_engineering_file(self):
        """General unsupported file (resume, invoice) prompts for plans/sections."""
        state = {
            "document_eligibility": "UNSUPPORTED_DOCUMENT",
            "doc_type": {"choice": "other", "has_architectural": False, "has_structural": False},
            "pages": [{"n": 1}],
            "flags": [],
        }
        res = n_reject(state)
        verdict = res["verdict"]
        self.assertEqual(verdict["overall"], "UNSUPPORTED_DOCUMENT")
        self.assertIn("not an architectural or structural drawing", verdict["message"])
        self.assertEqual(verdict["page_coverage"]["coverage_complete"], False)


if __name__ == "__main__":
    unittest.main()
