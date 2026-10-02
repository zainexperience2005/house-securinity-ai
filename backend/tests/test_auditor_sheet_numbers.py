"""Unit tests for sheet numbering auditor."""

import unittest

from src.auditors.sheet_auditor import audit_sheet_numbering


class TestAuditorSheetNumbers(unittest.TestCase):
    def test_sheet_audit_detects_gap_in_sequence(self):
        """Missing sheet A-02 between A-01 and A-03 is flagged."""
        pages = [
            {"n": 1, "text": "DRAWING A-01 SITE PLAN", "heads": []},
            {"n": 2, "text": "DRAWING A-03 GROUND FLOOR PLAN", "heads": []},
            {"n": 3, "text": "DRAWING S-01 FOUNDATION PLAN", "heads": []},
        ]
        audit = audit_sheet_numbering(pages)
        self.assertFalse(audit["is_sequence_valid"])
        self.assertIn("A-02", audit["missing_sheets"])

    def test_sheet_audit_contiguous_sequence(self):
        """Contiguous sheet numbering has no missing sheets."""
        pages = [
            {"n": 1, "text": "SHEET A-01 SITE PLAN", "heads": []},
            {"n": 2, "text": "SHEET A-02 FLOOR PLAN", "heads": []},
            {"n": 3, "text": "SHEET A-03 SECTIONS", "heads": []},
        ]
        audit = audit_sheet_numbering(pages)
        self.assertTrue(audit["is_sequence_valid"])
        self.assertEqual(len(audit["missing_sheets"]), 0)


if __name__ == "__main__":
    unittest.main()
