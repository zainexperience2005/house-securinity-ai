"""Numeric bylaw comparison (min/max limits) with conflict and missing-plan handling.

This step is not LLM-based: extracted numbers are compared to ``get_bylaws_for_plot``.
Without an architectural sheet, setback/FAR checks return ARCHITECTURAL_DRAWING_REQUIRED.
"""

from src.config.bylaws import get_bylaws_for_plot


def bylaw_check(v, custom_bylaws=None, authority="DHA_Lahore", has_architectural=True):
    """Compare extracted values ``v`` to society min/max rules.

    ``v`` entries may be plain numbers or dicts with ``value`` / ``is_conflict``.
    """
    if not has_architectural:
        # For purely structural drawing submissions lacking architectural sheets, zoning setbacks/FAR require architectural plans
        if custom_bylaws is not None:
            rules = custom_bylaws
        else:
            rules, _, _ = get_bylaws_for_plot(None, authority=authority)
        return dict.fromkeys(rules.keys(), "ARCHITECTURAL_DRAWING_REQUIRED")

    plot_marla = v.get("plot_area_marla")
    if isinstance(plot_marla, dict):
        plot_marla = plot_marla.get("value")

    if custom_bylaws is not None:
        rules = custom_bylaws
    else:
        rules, _, _ = get_bylaws_for_plot(plot_marla, authority=authority)

    out = {}
    for k, val in rules.items():
        if isinstance(val, (list, tuple)):
            op, lim = val[0], val[1]
        elif isinstance(val, dict):
            op, lim = val.get("op"), val.get("limit")
        else:
            op, lim = "min", None

        v_entry = v.get(k)
        if isinstance(v_entry, dict):
            if v_entry.get("is_conflict"):
                sources = v_entry.get("conflicting_sources", [])
                src_str = ", ".join([f"P{s.get('page')}:{s.get('value')}" for s in sources])
                out[k] = f"CONFLICT ({src_str})"
                continue
            x = v_entry.get("value")
        else:
            x = v_entry

        out[k] = (
            "NOT_CONFIGURED"
            if lim is None
            else "NO_VALUE"
            if x is None
            else "OK"
            if (x >= lim if op == "min" else x <= lim)
            else f"VIOLATION ({x} vs {op} {lim})"
        )
    return out
