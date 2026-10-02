"""Unit tests for PDF parsing and vector CAD geometry extraction."""

import unittest

import pymupdf

from src.core.pdf_parser import (
    extract_cad_vector_geometry,
    hidden_text,
    pack,
)


class TestCorePdfParser(unittest.TestCase):
    def test_extract_cad_vector_geometry(self):
        """Vector CAD paths (lines, rects) are correctly counted in page geometry summary."""
        doc = pymupdf.open()
        pg = doc.new_page(width=500, height=500)
        # Draw > 10 paths to trigger CAD heuristic
        for i in range(12):
            pg.draw_line((10, i * 20), (100, i * 20))
        geom = extract_cad_vector_geometry(pg)
        doc.close()

        self.assertTrue(geom["has_vector_cad"])
        self.assertGreaterEqual(geom["lines"], 10)
        self.assertGreater(geom["total_vector_paths"], 10)

    def test_hidden_text_detection(self):
        """White text on white background is detected by hidden_text heuristic."""
        doc = pymupdf.open()
        pg = doc.new_page(width=500, height=500)
        pg.insert_text((50, 50), "SECRET INJECTION TEXT", color=(1.0, 1.0, 1.0))
        hidden_runs = hidden_text(pg)
        doc.close()

        self.assertGreaterEqual(len(hidden_runs), 1)
        self.assertEqual(hidden_runs[0]["text"], "SECRET INJECTION TEXT")

    def test_pack_text_aggregation_and_limits(self):
        """pack aggregates page texts and respects cap limit and page filters."""
        state = {
            "pages": [
                {"n": 1, "text": "PAGE ONE ARCHITECTURAL CONTENT"},
                {"n": 2, "text": "PAGE TWO STRUCTURAL CONTENT"},
            ]
        }
        # Filter page 1 only
        p1_only = pack(state, cap=1000, page_numbers=[1])
        self.assertIn("PAGE ONE", p1_only)
        self.assertNotIn("PAGE TWO", p1_only)

        # Truncate length
        truncated = pack(state, cap=25)
        self.assertLessEqual(len(truncated), 25)


if __name__ == "__main__":
    unittest.main()
