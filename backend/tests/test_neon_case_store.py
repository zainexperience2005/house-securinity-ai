"""Unit tests for Neon DB review case storage and in-memory page rendering."""

import unittest

import pymupdf

from src.core.case_store import (
    add_review,
    create_case,
    get_case,
    list_cases,
    list_reviews,
    render_case_page,
)
from src.memory.database import get_db_connection


class TestNeonCaseStore(unittest.TestCase):
    def setUp(self):
        self.test_case_ids = []

    def tearDown(self):
        # Clean up any test cases and reviews from Neon DB
        if self.test_case_ids:
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        for cid in self.test_case_ids:
                            cur.execute("DELETE FROM reviews WHERE case_id = %s", (cid,))
                            cur.execute("DELETE FROM cases WHERE case_id = %s", (cid,))
                    conn.commit()
            except Exception:
                pass

    def _sample_pdf_bytes(self, text="SAMPLE NEON TEST DRAWING"):
        doc = pymupdf.open()
        pg = doc.new_page(width=400, height=300)
        pg.insert_text((50, 50), text)
        b = doc.tobytes()
        doc.close()
        return b

    def test_neon_create_get_and_list_case(self):
        """Case is stored directly in Neon DB without local files."""
        pdf_bytes = self._sample_pdf_bytes("GROUND FLOOR ARCHITECTURAL PLAN")
        verdict = {"overall": "CORRECTION_REQUIRED", "checks": {"bylaw": "PASS"}}
        case_id = create_case([("architectural_plan.pdf", pdf_bytes)], verdict, "DHA_Lahore")
        self.test_case_ids.append(case_id)

        # Verify case retrieval
        case = get_case(case_id)
        self.assertIsNotNone(case)
        self.assertEqual(case["case_id"], case_id)
        self.assertEqual(case["authority"], "DHA_Lahore")
        self.assertEqual(case["filenames"], ["architectural_plan.pdf"])
        self.assertEqual(case["verdict"]["overall"], "CORRECTION_REQUIRED")

        # Verify case in list_cases
        cases = list_cases(limit=10)
        found = any(c["case_id"] == case_id for c in cases)
        self.assertTrue(found)

    def test_neon_add_and_list_reviews(self):
        """Reviews are stored and retrieved from Neon DB."""
        pdf_bytes = self._sample_pdf_bytes("STRUCTURAL ELEVATION")
        verdict = {"overall": "PENDING_HUMAN_REVIEW"}
        case_id = create_case([("structural_plan.pdf", pdf_bytes)], verdict, "CDA_Islamabad")
        self.test_case_ids.append(case_id)

        review = add_review(case_id, "Senior Chief Auditor", "APPROVED", "All load bearing beams verified.")
        self.assertEqual(review["reviewer_name"], "Senior Chief Auditor")
        self.assertEqual(review["decision"], "APPROVED")
        self.assertEqual(review["case_id"], case_id)

        reviews = list_reviews(case_id)
        self.assertGreaterEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["note"], "All load bearing beams verified.")

    def test_neon_render_page_from_memory(self):
        """render_case_page renders PNG bytes directly from Neon DB bytes without disk files."""
        pdf_bytes = self._sample_pdf_bytes("SITE AND BOUNDARY PLAN")
        case_id = create_case([("site_boundary.pdf", pdf_bytes)], {"overall": "PASS"}, "LDA")
        self.test_case_ids.append(case_id)

        png_bytes = render_case_page(case_id, 1)
        self.assertTrue(png_bytes.startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
