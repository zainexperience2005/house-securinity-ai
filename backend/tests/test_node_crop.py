"""Unit tests for n_crop node in House Scrutiny pipeline."""

import tempfile
import unittest
from pathlib import Path

import pymupdf

from src.pipeline.nodes import n_crop


class TestNodeCrop(unittest.TestCase):
    def test_n_crop_generates_overview_and_crops(self):
        """n_crop renders base64 overview images and high-detail crop shots."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "sample_plan.pdf"
            doc = pymupdf.open()
            pg = doc.new_page(width=800, height=1000)
            pg.insert_text((50, 50), "SITE PLAN & FRONT ELEVATION", fontsize=18)
            pg.insert_text((600, 900), "TITLE BLOCK: DHA LAHORE RESIDENCE REV 1", fontsize=12)
            pg.draw_rect(pymupdf.Rect(580, 880, 780, 980))
            doc.save(str(pdf_path))
            doc.close()

            state = {
                "pdf": str(pdf_path),
                "pages": [{"n": 1, "text": "SITE PLAN & FRONT ELEVATION TITLE BLOCK"}],
                "doc_type": {"page_types": {1: {"choice": "architectural_drawing"}}},
            }
            res = n_crop(state)
            self.assertIn("shots", res)
            self.assertIn("page_coverage", res)
            shots = res["shots"]
            self.assertGreater(len(shots), 0)
            # Must include at least an overview
            self.assertTrue(any(s["detail"] == "low" for s in shots))
            # Page coverage audit must record page 1 as PROCESSED
            self.assertEqual(res["page_coverage"][1]["status"], "PROCESSED")
            self.assertEqual(res["page_coverage"][1]["page_type"], "architectural_drawing")

    def test_n_crop_missing_file_fails_gracefully(self):
        """Missing PDF file should not crash n_crop and return empty shots."""
        state = {"pdf": "non_existent_file.pdf", "pages": [{"n": 1}], "doc_type": {}}
        res = n_crop(state)
        self.assertEqual(res["shots"], [])
        self.assertEqual(res["page_coverage"], {})


if __name__ == "__main__":
    unittest.main()
