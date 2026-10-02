"""Unit tests for cross-page dimension conflict resolver."""

import unittest

from src.auditors.conflict_resolver import resolve_cross_page_conflicts


class TestAuditorConflicts(unittest.TestCase):
    def test_cross_page_conflict_detected(self):
        """Discrepancies exceeding tolerance produce CONFLICT status and flags."""
        values = [
            {"key": "front_setback_ft", "value": 10.0, "page": 1, "evidence": "10ft on Site Plan"},
            {"key": "front_setback_ft", "value": 7.5, "page": 2, "evidence": "7.5ft on Floor Plan"},
        ]
        pages = [{"n": 1, "text": ""}, {"n": 2, "text": ""}]
        resolved, flags = resolve_cross_page_conflicts(values, pages)

        item = resolved.get("front_setback_ft")
        self.assertIsNotNone(item)
        self.assertTrue(item["is_conflict"])
        self.assertEqual(item["status"], "CONFLICT")
        self.assertEqual(len(flags), 1)
        self.assertIn("front_setback_ft", flags[0])

    def test_cross_page_no_conflict_when_values_match(self):
        """Identical values across sheets resolve cleanly without conflict flags."""
        values = [
            {"key": "total_height_ft", "value": 35.0, "page": 2, "evidence": "35ft on section"},
            {"key": "total_height_ft", "value": 35.0, "page": 3, "evidence": "35ft on elevation"},
        ]
        pages = [{"n": 2, "text": ""}, {"n": 3, "text": ""}]
        resolved, flags = resolve_cross_page_conflicts(values, pages)

        item = resolved.get("total_height_ft")
        self.assertIsNotNone(item)
        self.assertFalse(item["is_conflict"])
        self.assertEqual(len(flags), 0)


if __name__ == "__main__":
    unittest.main()
