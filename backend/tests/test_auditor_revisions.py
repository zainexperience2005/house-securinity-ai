"""Unit tests for revision auditor and authoritative revision resolution."""

import unittest

from src.auditors.revision_auditor import (
    filter_values_to_master_revision,
    resolve_authoritative_revisions,
)


class TestAuditorRevisions(unittest.TestCase):
    def test_resolve_authoritative_revisions_single(self):
        """Single sheet revision is selected as master revision."""
        audit = resolve_authoritative_revisions(
            revisions_table=[{"revision_id": "REV 1", "description": "Initial Issue", "date": "2026-01-01", "page": 1}],
            doc_revisions=["REV 1"],
            pages_list=[{"n": 1, "text": "REV 1"}],
        )
        self.assertIn("1", audit["master_revision"])
        self.assertTrue(audit["is_consistent"])

    def test_resolve_authoritative_revisions_alphanumeric_sequence(self):
        """Highest revision in sequence (e.g. REV 2 over REV 1) is chosen as master."""
        audit = resolve_authoritative_revisions(
            revisions_table=[], doc_revisions=["REV 0", "REV 1", "REV 2"], pages_list=[{"n": 1, "text": ""}]
        )
        self.assertIn("2", audit["master_revision"])

    def test_filter_values_to_master_revision_discards_superseded(self):
        """Design values belonging to older superseded revisions are filtered out."""
        raw_values = [
            {"key": "front_setback_ft", "value": 8.0, "page": 1},
            {"key": "front_setback_ft", "value": 10.0, "page": 2},
        ]
        rev_audit = {
            "master_revision": "REV 2",
            "revision_history": [
                {"revision_id": "REV 1", "page": 1},
                {"revision_id": "REV 2", "page": 2},
            ],
        }
        filtered, flags = filter_values_to_master_revision(raw_values, rev_audit)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["page"], 2)
        self.assertEqual(filtered[0]["value"], 10.0)
        self.assertEqual(len(flags), 1)


if __name__ == "__main__":
    unittest.main()
