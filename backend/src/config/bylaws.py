"""Society bylaw thresholds and plot-size rule resolution.

``BYLAWS`` is a fallback tuple map (operator, limit) used when ``bylaw.json``
is missing. ``VALUE_KEYS`` / ``STRUCTURAL_KEYS`` are extraction hints for
vision prompts, not the numeric limits themselves. Live limits come from
``get_bylaws_for_plot`` which prefers authority-specific plots, then
``default_by_plot_size`` in ``bylaw.json``.
"""

import json
import os

# Society bylaw thresholds: (operation: 'min' or 'max', limit_value)
BYLAWS = {
    "front_setback_ft": ("min", None),
    "rear_setback_ft": ("min", None),
    "left_setback_ft": ("min", None),
    "right_setback_ft": ("min", None),
    "total_height_ft": ("max", None),
    "ground_coverage_pct": ("max", None),
    "storeys": ("max", None),
    "plinth_height_ft": ("min", None),
    "boundary_wall_height_ft": ("max", None),
    "projection_ft": ("max", None),
}

VALUE_KEYS = {
    "plot_area_marla": "plot area in marla (convert only an explicit plot category/area)",
    "front_setback_ft": "front setback, feet",
    "rear_setback_ft": "rear setback, feet",
    "left_setback_ft": "left side setback, feet",
    "right_setback_ft": "right side setback, feet",
    "total_height_ft": "explicit overall building height, feet",
    "storeys": "ground + complete habitable floors",
    "ground_coverage_pct": "stated %, or explicit ground-floor covered area / explicit plot area",
    "plinth_height_ft": "explicit PLINTH label only, feet",
    "basement": "1 if explicit basement plan/label else 0",
    "parking_bays": "labelled car porch/parking/garage bays",
    "boundary_wall_height_ft": "overall boundary wall height, feet",
    "ugwt_gallons": "underground water tank capacity, gallons (L x W x H x 7.48 from explicit internal dims, or labelled)",
    "ohwt_gallons": "overhead water tank capacity, gallons",
    "septic_length_ft": "septic inner length, feet",
    "septic_width_ft": "septic inner width, feet",
    "septic_depth_ft": "septic inner usable depth, feet",
    "trees": "count of clear tree symbols inside plot",
    "projection_ft": "explicit floor-specific chajja/canopy/projection, feet",
}

STRUCTURAL_KEYS = {
    "slab_thickness_in": "explicit slab thickness, inches (e.g. 5, 6)",
    "foundation_depth_ft": "explicit foundation excavation / depth below NSL, feet",
    "concrete_grade_psi": "specified concrete compressive strength fc' in psi (e.g. 3000, 4000) or MPa",
    "steel_grade_psi": "specified steel yield strength fy in psi (e.g. 60000 for Grade 60, 40000 for Grade 40)",
    "column_schedule_present": "1 if column schedule with cross-sections and rebar is present else 0",
    "beam_schedule_present": "1 if beam schedule with sizes, rebar and stirrups is present else 0",
    "slab_rebar_detail_present": "1 if slab reinforcement layout / schedule is present else 0",
    "structural_notes_present": "1 if general structural notes/specifications are present else 0",
    "seismic_zone_stated": "1 if seismic zone / design code (e.g. Zone 2A/2B) is stated else 0",
}


def load_bylaw_config():
    """Load repo-root ``bylaw.json``. Returns None if the file is missing or invalid."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    p = os.path.join(base_dir, "bylaw.json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


BYLAW_DATABASE = load_bylaw_config()


def get_bylaws_for_plot(plot_marla=None, authority="DHA_Lahore"):
    """Resolve the rule set for a plot size and housing authority.

    Plot category is chosen by marla bands (3 / 5 / 7 / 8 / 10 marla, 1 and 2
    kanal). Authority-specific ``plots`` override generic defaults.

    Returns:
        tuple: (rules_dict keyed by parameter, plot_category_key, display_name)
    """
    if not BYLAW_DATABASE:
        return BYLAWS, "custom", "Default Society Bylaws"

    auth_dict = BYLAW_DATABASE.get("authorities_specific") or {}
    auth_data = auth_dict.get(authority) or auth_dict.get("DHA_Lahore") or {}
    auth_plots = auth_data.get("plots") or {}
    defaults = BYLAW_DATABASE.get("default_by_plot_size") or {}

    pkey = "5_marla"
    if plot_marla is not None:
        try:
            m = float(plot_marla)
            # Inclusive upper bounds: e.g. 6.0 marla still maps to 5_marla category.
            if m <= 3.5:
                pkey = "3_marla"
            elif m <= 6.0:
                pkey = "5_marla"
            elif m <= 7.5:
                pkey = "7_marla"
            elif m <= 9.0:
                pkey = "8_marla"
            elif m <= 15.0:
                pkey = "10_marla"
            elif m <= 25.0:
                pkey = "1_kanal"
            else:
                pkey = "2_kanal"
        except Exception:
            pkey = "5_marla"

    disp_name = (defaults.get(pkey) or {}).get("display_name", f"{pkey.replace('_', ' ').title()}")

    if pkey in auth_plots:
        return auth_plots[pkey], pkey, disp_name

    if pkey in defaults:
        return {k: (v["op"], v["limit"]) for k, v in defaults[pkey]["rules"].items()}, pkey, disp_name

    return BYLAWS, pkey, disp_name
