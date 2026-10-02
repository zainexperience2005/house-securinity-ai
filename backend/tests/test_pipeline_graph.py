"""Unit tests for LangGraph pipeline build and conditional routing."""

import unittest
from unittest.mock import patch

from src.pipeline.graph import build


class TestPipelineGraph(unittest.TestCase):
    def test_pipeline_build_compiles(self):
        """Graph builds and compiles without configuration errors."""
        app = build()
        self.assertIsNotNone(app)

    @patch("src.pipeline.graph.n_ingest")
    @patch("src.pipeline.graph.n_reject")
    def test_pipeline_routes_to_reject_when_unreadable(self, mock_reject, mock_ingest):
        """Unreadable document skips gate, crop, extract, judge and routes directly to reject."""
        mock_ingest.return_value = {"unreadable": True, "flags": ["Corrupted PDF"], "pages": []}
        mock_reject.return_value = {"verdict": {"overall": "UNSUPPORTED_DOCUMENT", "message": "Corrupted"}}

        app = build()
        result = app.invoke({"pdf": "corrupt.pdf", "authority": "DHA_Lahore"})
        self.assertEqual(result["verdict"]["overall"], "UNSUPPORTED_DOCUMENT")
        mock_reject.assert_called_once()

    @patch("src.pipeline.graph.n_ingest")
    @patch("src.pipeline.graph.n_gate")
    @patch("src.pipeline.graph.n_reject")
    def test_pipeline_routes_to_reject_when_ineligible(self, mock_reject, mock_gate, mock_ingest):
        """Ineligible document (resume, invoice) routes from gate directly to reject."""
        mock_ingest.return_value = {"unreadable": False, "pages": [{"n": 1, "text": "RESUME"}]}
        mock_gate.return_value = {"document_eligibility": "UNSUPPORTED_DOCUMENT", "doc_type": {"choice": "other"}}
        mock_reject.return_value = {"verdict": {"overall": "UNSUPPORTED_DOCUMENT", "message": "Not a drawing"}}

        app = build()
        result = app.invoke({"pdf": "resume.pdf", "authority": "DHA_Lahore"})
        self.assertEqual(result["verdict"]["overall"], "UNSUPPORTED_DOCUMENT")
        mock_reject.assert_called_once()


if __name__ == "__main__":
    unittest.main()
