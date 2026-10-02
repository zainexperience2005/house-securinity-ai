"""Unit tests for n_extract node in House Scrutiny pipeline."""

import unittest
from unittest.mock import patch

from src.pipeline.nodes import n_extract


class TestNodeExtract(unittest.TestCase):
    @patch("src.pipeline.nodes.run_vision_extraction_batch")
    def test_n_extract_architectural_batch(self, mock_batch):
        """Architectural pass extracts values, observations, and usage."""
        mock_batch.return_value = (
            {
                "values": [{"key": "front_setback_ft", "value": 10.0, "evidence": "10 ft setback", "page": 1}],
                "structural_values": [],
                "certificate_details": None,
                "observations": [{"check_id": "site_plan", "seen": "yes", "evidence": "Site plan shown", "page": 1}],
                "flags": [],
                "revisions": ["Rev 1"],
                "revisions_table": [],
            },
            {"input_tokens": 500, "output_tokens": 150},
        )
        state = {
            "doc_type": {"architectural_pages": [1], "structural_pages": [], "certificate_pages": []},
            "shots": [
                {"page": 1, "page_type": "architectural_drawing", "b64": "dummy", "detail": "low", "label": "overview"}
            ],
            "pages": [{"n": 1, "text": "GROUND FLOOR PLAN"}],
            "authority": "DHA_Lahore",
        }
        res = n_extract(state)
        self.assertIn("extraction", res)
        self.assertIn("openai_usage", res)
        ext = res["extraction"]
        self.assertEqual(len(ext["values"]), 1)
        self.assertEqual(ext["values"][0]["key"], "front_setback_ft")
        self.assertEqual(ext["values"][0]["value"], 10.0)
        self.assertEqual(res["openai_usage"]["input_tokens"], 500)

    @patch("src.pipeline.nodes.run_vision_extraction_batch")
    def test_n_extract_structural_and_certificate_batch(self, mock_batch):
        """Structural and certificate batches extract structural params and engineer details."""

        def batch_side_effect(header, doc_text, shots, **kwargs):
            if "CERTIFICATE" in header:
                return (
                    {
                        "values": [],
                        "structural_values": [],
                        "certificate_details": {
                            "engineer_name": "Engr. Tariq Khan",
                            "pec_registration_no": "CIVIL/12345",
                            "has_signature": True,
                            "has_stamp": True,
                        },
                        "observations": [
                            {"check_id": "stability_cert", "seen": "yes", "evidence": "signed", "page": 3}
                        ],
                        "flags": [],
                        "revisions": [],
                        "revisions_table": [],
                    },
                    {"input_tokens": 200, "output_tokens": 50},
                )
            elif "STRUCTURAL" in header:
                return (
                    {
                        "values": [],
                        "structural_values": [
                            {"key": "concrete_grade_psi", "value": 3000.0, "evidence": "fc=3000 psi", "page": 2}
                        ],
                        "certificate_details": None,
                        "observations": [
                            {"check_id": "foundation_plan", "seen": "yes", "evidence": "foundation", "page": 2}
                        ],
                        "flags": [],
                        "revisions": [],
                        "revisions_table": [],
                    },
                    {"input_tokens": 400, "output_tokens": 100},
                )
            return (
                {"values": [], "structural_values": [], "certificate_details": None, "observations": [], "flags": []},
                {"input_tokens": 0, "output_tokens": 0},
            )

        mock_batch.side_effect = batch_side_effect

        state = {
            "doc_type": {"architectural_pages": [], "structural_pages": [2], "certificate_pages": [3]},
            "shots": [
                {"page": 2, "page_type": "structural_drawing", "b64": "dummy", "detail": "low", "label": "overview"},
                {"page": 3, "page_type": "stability_certificate", "b64": "dummy", "detail": "low", "label": "overview"},
            ],
            "pages": [{"n": 2, "text": "STRUCTURAL"}, {"n": 3, "text": "CERTIFICATE"}],
            "authority": "DHA_Lahore",
        }
        res = n_extract(state)
        ext = res["extraction"]
        self.assertEqual(len(ext["structural_values"]), 1)
        self.assertEqual(ext["structural_values"][0]["key"], "concrete_grade_psi")
        self.assertIsNotNone(ext["certificate_details"])
        self.assertEqual(ext["certificate_details"]["engineer_name"], "Engr. Tariq Khan")
        self.assertEqual(res["openai_usage"]["input_tokens"], 600)


if __name__ == "__main__":
    unittest.main()
