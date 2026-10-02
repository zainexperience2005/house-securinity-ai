"""Unit tests for SQLite case store and human review persistence."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from src.core.case_store import (
    add_review,
    create_case,
    get_case,
    list_reviews,
    merge_pdf_documents,
    render_case_page,
)


class TestCoreCaseStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store_dir = Path(self.temp_dir.name) / "review_cases"
        self.db_path = self.store_dir / "cases.sqlite3"

        self.patch_store = patch("src.core.case_store.STORE_DIR", self.store_dir)
        self.patch_db = patch("src.core.case_store.DATABASE_PATH", self.db_path)
        self.patch_enabled = patch("src.core.case_store.is_storage_enabled", return_value=True)

        self.patch_store.start()
        self.patch_db.start()
        self.patch_enabled.start()

    def tearDown(self):
        self.patch_enabled.stop()
        self.patch_db.stop()
        self.patch_store.stop()
        self.temp_dir.cleanup()

    def _sample_pdf_bytes(self, text="SAMPLE DRAWING"):
        doc = pymupdf.open()
        pg = doc.new_page(width=400, height=300)
        pg.insert_text((50, 50), text)
        b = doc.tobytes()
        doc.close()
        return b

    def test_case_store_create_and_get(self):
        """Case can be created and retrieved with metadata and verdict intact."""
        pdf_bytes = self._sample_pdf_bytes("GROUND FLOOR PLAN")
        verdict = {"overall": "CORRECTION_REQUIRED", "checks": {}}
        case_id = create_case([("plan.pdf", pdf_bytes)], verdict, "DHA_Lahore")

        case = get_case(case_id)
        self.assertIsNotNone(case)
        self.assertEqual(case["case_id"], case_id)
        self.assertEqual(case["authority"], "DHA_Lahore")
        self.assertEqual(case["filenames"], ["plan.pdf"])
        self.assertEqual(case["verdict"]["overall"], "CORRECTION_REQUIRED")

    def test_case_store_add_and_list_reviews(self):
        """Engineer review decisions can be logged and listed."""
        pdf_bytes = self._sample_pdf_bytes("ELEVATION")
        case_id = create_case([("elevation.pdf", pdf_bytes)], {"overall": "PENDING_HUMAN_REVIEW"}, "LDA_Lahore")

        review = add_review(case_id, "Chief Auditor", "APPROVED", "All corrections addressed in Rev 2.")
        self.assertEqual(review["reviewer_name"], "Chief Auditor")
        self.assertEqual(review["decision"], "APPROVED")

        reviews = list_reviews(case_id)
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["note"], "All corrections addressed in Rev 2.")

    def test_case_store_render_page(self):
        """render_case_page returns valid PNG bytes."""
        pdf_bytes = self._sample_pdf_bytes("SITE PLAN")
        case_id = create_case([("site.pdf", pdf_bytes)], {"overall": "PASS"}, "DHA_Lahore")

        png_bytes = render_case_page(case_id, 1)
        self.assertTrue(png_bytes.startswith(b"\x89PNG"))

    def test_merge_pdf_documents(self):
        """Multiple PDF files are concatenated into a single multi-page PDF."""
        pdf1 = self._sample_pdf_bytes("PAGE 1")
        pdf2 = self._sample_pdf_bytes("PAGE 2")
        merged_bytes = merge_pdf_documents([("a.pdf", pdf1), ("b.pdf", pdf2)])

        doc = pymupdf.open(stream=merged_bytes, filetype="pdf")
        self.assertEqual(len(doc), 2)
        doc.close()


if __name__ == "__main__":
    unittest.main()
