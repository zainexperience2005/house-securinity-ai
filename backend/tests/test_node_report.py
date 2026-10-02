"""Unit tests for n_report node in House Scrutiny pipeline."""

import unittest

from src.pipeline.nodes import n_report


class TestNodeReport(unittest.TestCase):
    def test_n_report_all_pass_ready_for_signoff(self):
        """When all checks pass, completeness is 100%, and bylaws comply, verdict is READY_FOR_HUMAN_SIGNOFF."""
        state = {
            "doc_type": {
                "has_architectural": True,
                "has_structural": True,
                "has_stability_certificate": True,
                "primary_type": "architectural_drawing",
                "confidence": 0.95,
            },
            "pages": [
                {"n": 1, "text": "SITE PLAN A-01", "heads": []},
                {"n": 2, "text": "FLOOR PLANS A-02", "heads": []},
                {"n": 3, "text": "SECTIONS ELEVATIONS A-03", "heads": []},
                {"n": 4, "text": "FOUNDATION & COLUMNS S-01", "heads": []},
                {"n": 5, "text": "STABILITY CERTIFICATE", "heads": []},
            ],
            "active_checklist": {
                "site_plan": "Site/block plan",
                "floor_plans": "Floor plans",
                "sections_elevations": "Sections & elevations",
                "foundation_plan": "Foundation layout",
                "column_schedule": "Column schedule",
                "stability_cert": "Stability certificate",
            },
            "extraction": {
                "values": [
                    {"key": "plot_area_marla", "value": 10.0, "page": 1, "evidence": "10 Marla"},
                    {"key": "front_setback_ft", "value": 12.0, "page": 1, "evidence": "12 ft"},
                    {"key": "rear_setback_ft", "value": 7.0, "page": 1, "evidence": "7 ft"},
                    {"key": "total_height_ft", "value": 30.0, "page": 3, "evidence": "30 ft"},
                    {"key": "ground_coverage_pct", "value": 60.0, "page": 2, "evidence": "60%"},
                ],
                "structural_values": [{"key": "concrete_grade_psi", "value": 3000, "page": 4}],
                "certificate_details": {
                    "certificate_present": True,
                    "engineer_name": "Engr. Ali",
                    "pec_registration_no": "12345",
                    "has_signature": True,
                },
                "observations": [
                    {"check_id": "site_plan", "seen": "yes", "page": 1, "evidence": "Site plan demarcated"},
                    {"check_id": "floor_plans", "seen": "yes", "page": 2, "evidence": "Floor plan layout"},
                    {"check_id": "sections_elevations", "seen": "yes", "page": 3, "evidence": "Building section"},
                    {"check_id": "foundation_plan", "seen": "yes", "page": 4, "evidence": "Foundation plan"},
                    {"check_id": "column_schedule", "seen": "yes", "page": 4, "evidence": "Column schedule"},
                    {"check_id": "stability_cert", "seen": "yes", "page": 5, "evidence": "Signed cert"},
                ],
                "flags": [],
                "revision": "Rev 1",
                "revisions_table": [],
            },
            "checks": {
                "site_plan": {"choice": "PASS", "confidence": 0.95, "probabilities": {"PASS": 0.95}},
                "floor_plans": {"choice": "PASS", "confidence": 0.95, "probabilities": {"PASS": 0.95}},
                "sections_elevations": {"choice": "PASS", "confidence": 0.95, "probabilities": {"PASS": 0.95}},
                "foundation_plan": {"choice": "PASS", "confidence": 0.95, "probabilities": {"PASS": 0.95}},
                "column_schedule": {"choice": "PASS", "confidence": 0.95, "probabilities": {"PASS": 0.95}},
                "stability_cert": {"choice": "PASS", "confidence": 0.95, "probabilities": {"PASS": 0.95}},
            },
            "authority": "DHA_Lahore",
            "openai_usage": {"input_tokens": 1000, "output_tokens": 200},
            "jev_gate_usage": {"input_tokens": 200, "output_tokens": 50},
            "jev_judge_usage": {"input_tokens": 300, "output_tokens": 60},
            "page_coverage": {
                1: {"status": "PROCESSED"},
                2: {"status": "PROCESSED"},
                3: {"status": "PROCESSED"},
                4: {"status": "PROCESSED"},
                5: {"status": "PROCESSED"},
            },
        }
        res = n_report(state)
        verdict = res["verdict"]
        self.assertEqual(verdict["overall"], "READY_FOR_HUMAN_SIGNOFF")
        self.assertIn("token_metrics", verdict)
        self.assertGreater(verdict["token_metrics"]["total"]["total_tokens"], 0)
        self.assertIn("bylaws", verdict)
        self.assertEqual(verdict["completeness_audit"]["completeness_status"], "COMPLETE")

    def test_n_report_bylaw_violation_triggers_correction_required(self):
        """When front setback violates minimum requirement, verdict must be CORRECTION_REQUIRED."""
        state = {
            "doc_type": {
                "has_architectural": True,
                "has_structural": False,
                "has_stability_certificate": False,
                "primary_type": "architectural_drawing",
            },
            "pages": [{"n": 1, "text": "SITE PLAN", "heads": []}],
            "extraction": {
                "values": [
                    {"key": "plot_area_marla", "value": 10.0, "page": 1},
                    {"key": "front_setback_ft", "value": 3.0, "page": 1},  # Min for 10M is 10.75 ft
                ],
                "structural_values": [],
                "certificate_details": None,
                "observations": [],
                "flags": [],
            },
            "checks": {"site_plan": {"choice": "PASS", "confidence": 0.95}},
            "authority": "DHA_Lahore",
        }
        res = n_report(state)
        verdict = res["verdict"]
        self.assertEqual(verdict["overall"], "CORRECTION_REQUIRED")
        self.assertIn("bylaws", verdict)
        self.assertTrue(any("VIOLATION" in str(v) for v in verdict["bylaws"].values()))


if __name__ == "__main__":
    unittest.main()
