"""Unit tests for PDF scrutiny report generator."""

import io
import unittest

import pymupdf

from src.reporting.pdf_report import create_scrutiny_pdf_report


class TestReportingPdf(unittest.TestCase):
    def test_create_scrutiny_pdf_report_valid_pdf(self):
        """create_scrutiny_pdf_report produces a valid readable PDF byte stream."""
        verdict = {
            "overall": "CORRECTION_REQUIRED",
            "doc_type": {"choice": "architectural_drawing", "confidence": 0.95},
            "page_breakdown": {1: {"choice": "architectural_drawing", "confidence": 0.95}},
            "page_coverage": {"total_pages": 2, "processed_pages": [1, 2], "coverage_complete": True},
            "sheet_numbering_audit": {"has_numbering": True, "missing_sheets": []},
            "completeness_audit": {
                "completeness_status": "COMPLETE",
                "completeness_score_pct": 100,
                "missing_components": [],
            },
            "duplicates_audit": {"has_duplicates": False, "duplicates": []},
            "cross_page_conflicts": [],
            "revision": "Rev 1",
            "revisions_audit": {"master_revision": "Rev 1", "is_consistent": True, "revision_history": []},
            "checks": {
                "site_plan": {
                    "status": "PASS",
                    "page": 1,
                    "reason": "Present",
                    "evidence": "Site plan shown",
                    "confidence": 0.95,
                },
                "front_setback": {
                    "status": "CORRECTION_REQUIRED",
                    "page": 1,
                    "note": "Setback 4.5ft < min 5ft",
                    "confidence": 0.92,
                },
            },
            "values": {
                "front_setback_ft": {"value": 4.5, "unit": "ft", "evidence": "4'-6\"", "page": 1, "status": "VERIFIED"}
            },
            "structural_analysis": {"sheets_present": False},
            "certificate_audit": {"certificate_present": False},
            "bylaws": {"front_setback_ft": "VIOLATION: 4.5ft < min 5.0ft"},
            "review_flags": [],
            "processing_seconds": 12.3,
            "token_metrics": {
                "openai": {
                    "model": "gpt-4o",
                    "input_tokens": 1000,
                    "output_tokens": 200,
                    "total_tokens": 1200,
                    "cost_usd": "$0.00500",
                },
                "jev": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120, "cost_usd": "$0.00001"},
                "total": {"total_tokens": 1320, "total_cost_usd": "$0.00501"},
            },
        }
        buf = create_scrutiny_pdf_report(verdict, filename="UnitDrawing.pdf")
        self.assertIsInstance(buf, io.BytesIO)
        pdf_bytes = buf.getvalue()
        self.assertGreater(len(pdf_bytes), 1000)

        # Parse with PyMuPDF to assert structural validity
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        self.assertGreaterEqual(len(doc), 1)
        full_text = "".join(page.get_text() for page in doc)
        self.assertIn("Engineer Action Register", full_text)
        self.assertIn("OpenAI Vision", full_text)
        self.assertIn("TypeSafe Jev", full_text)
        doc.close()


if __name__ == "__main__":
    unittest.main()
