"""Unit tests for duplicate page detection."""

import unittest

from src.core.duplicates import detect_duplicate_pages


class TestCoreDuplicates(unittest.TestCase):
    def test_detect_duplicate_pages_found(self):
        """Identical text and vector geometry across pages triggers duplicate warning."""
        pages = [
            {
                "n": 1,
                "text": "STANDARD GENERAL SPECIFICATIONS",
                "vector_cad": {
                    "lines": 10,
                    "rectangles": 4,
                    "curves": 0,
                    "closed_polygons": 2,
                    "total_vector_paths": 16,
                },
            },
            {
                "n": 2,
                "text": "STANDARD GENERAL SPECIFICATIONS",
                "vector_cad": {
                    "lines": 10,
                    "rectangles": 4,
                    "curves": 0,
                    "closed_polygons": 2,
                    "total_vector_paths": 16,
                },
            },
        ]
        res = detect_duplicate_pages(None, pages)
        self.assertTrue(res["has_duplicates"])
        self.assertEqual(len(res["duplicates"]), 1)
        self.assertEqual(res["duplicates"][0]["duplicate_page"], 2)
        self.assertEqual(res["duplicates"][0]["original_page"], 1)

    def test_detect_duplicate_pages_none(self):
        """Distinct pages produce no duplicate warnings."""
        pages = [
            {
                "n": 1,
                "text": "SITE PLAN",
                "vector_cad": {"lines": 5, "rectangles": 1, "curves": 0, "closed_polygons": 1, "total_vector_paths": 7},
            },
            {
                "n": 2,
                "text": "ROOF PLAN",
                "vector_cad": {
                    "lines": 12,
                    "rectangles": 6,
                    "curves": 2,
                    "closed_polygons": 4,
                    "total_vector_paths": 24,
                },
            },
        ]
        res = detect_duplicate_pages(None, pages)
        self.assertFalse(res["has_duplicates"])
        self.assertEqual(len(res["duplicates"]), 0)


if __name__ == "__main__":
    unittest.main()
