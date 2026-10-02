"""Unit tests for bylaw configurations and plot-size resolution."""

import unittest

from src.config.bylaws import get_bylaws_for_plot, load_bylaw_config


class TestBylaws(unittest.TestCase):
    def test_load_bylaw_config_schema(self):
        """Bylaw database contains required metadata and plot categories."""
        db = load_bylaw_config()
        self.assertIn("_meta", db)
        self.assertIn("default_by_plot_size", db)
        self.assertIn("5_marla", db["default_by_plot_size"])
        self.assertIn("1_kanal", db["default_by_plot_size"])

    def test_dha_5_marla_rules(self):
        """5 Marla plot under DHA Lahore should have 5ft front and 3ft rear setbacks."""
        bylaws, cat_key, cat_name = get_bylaws_for_plot(5.0, "DHA_Lahore")
        self.assertEqual(cat_key, "5_marla")
        self.assertEqual(bylaws["front_setback_ft"], ["min", 5.0])
        self.assertEqual(bylaws["rear_setback_ft"], ["min", 3.0])
        self.assertEqual(bylaws["ground_coverage_pct"], ["max", 75.0])

    def test_dha_10_marla_rules(self):
        """10 Marla plot under DHA Lahore should resolve 10_marla rules."""
        bylaws, cat_key, cat_name = get_bylaws_for_plot(10.0, "DHA_Lahore")
        self.assertEqual(cat_key, "10_marla")
        self.assertEqual(bylaws["front_setback_ft"][0], "min")
        self.assertGreater(bylaws["front_setback_ft"][1], 10.0)
        self.assertEqual(bylaws["total_height_ft"], ["max", 35.0])

    def test_lda_1_kanal_rules(self):
        """1 Kanal plot under LDA should resolve with 1_kanal category and 15ft front setback."""
        bylaws, cat_key, cat_name = get_bylaws_for_plot(20.0, "LDA_Lahore")
        self.assertEqual(cat_key, "1_kanal")
        self.assertEqual(bylaws["front_setback_ft"], ("min", 15.0))
        self.assertEqual(bylaws["total_height_ft"], ("max", 35.0))

    def test_fallback_unrecognized_authority(self):
        """Unrecognized authority falls back to standard plot size rules gracefully."""
        bylaws, cat_key, cat_name = get_bylaws_for_plot(5.0, "Unknown_Authority")
        self.assertEqual(cat_key, "5_marla")
        self.assertIn("front_setback_ft", bylaws)


if __name__ == "__main__":
    unittest.main()
