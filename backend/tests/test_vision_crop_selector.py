"""Unit tests for intelligent crop selector and title block detection."""

import unittest

import pymupdf

from src.vision.crop_selector import find_intelligent_sheet_crops, nearby
from src.vision.title_block import detect_title_block_regions


class TestVisionCropSelector(unittest.TestCase):
    def test_nearby_words_clustering(self):
        """nearby collects words located within the radius R as formatted directional strings."""
        # Word format: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
        words = [
            (100, 100, 150, 115, "SETBACK", 0, 0, 0),
            (155, 100, 200, 115, "10FT", 0, 0, 1),
            (800, 800, 850, 815, "FARAWAY", 1, 0, 0),
        ]
        hints = nearby(words, R=100)
        self.assertGreater(len(hints), 0)
        self.assertIsInstance(hints[0], str)
        self.assertIn("SETBACK", hints[0])

    def test_find_intelligent_sheet_crops_and_title_block(self):
        """find_intelligent_sheet_crops generates crop bounding boxes around title block and key keywords."""
        doc = pymupdf.open()
        pg = doc.new_page(width=1000, height=800)
        pg.insert_text((50, 50), "GROUND FLOOR PLAN SCALE 1:100", fontsize=16)
        pg.insert_text((750, 700), "DHA LAHORE RESIDENCE TITLE BLOCK REVISION 1", fontsize=12)
        pg.draw_rect(pymupdf.Rect(700, 650, 950, 780))

        crops = find_intelligent_sheet_crops(pg, "architectural_drawing")
        doc.close()

        self.assertGreater(len(crops), 0)
        labels = [c[0] for c in crops]
        self.assertTrue(any("title" in lbl.lower() or "floor" in lbl.lower() for lbl in labels))

    def test_detect_title_block_regions(self):
        """detect_title_block_regions detects title blocks along perimeter."""
        doc = pymupdf.open()
        pg = doc.new_page(width=800, height=600)
        pg.insert_text((650, 500), "PROJECT: VILLA DRAWING NO A-1 REVISION 0", fontsize=10)
        words = pg.get_text("words")
        regions = detect_title_block_regions(pg, words)
        doc.close()

        self.assertGreater(len(regions), 0)


if __name__ == "__main__":
    unittest.main()
