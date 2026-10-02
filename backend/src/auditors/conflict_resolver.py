"""Flag the same design parameter with different numbers on different sheets.

Values within 0.05 are treated as the same measurement. Distinct values become
CONFLICT so bylaw_check will not pick one side silently.
"""

from .evidence_verifier import verify_spatial_numeric_evidence


def resolve_cross_page_conflicts(raw_values_list, pages_list):
    """Detects and resolves conflicting extracted values for the same parameter across different pages.

    If Page 2 reports front_setback_ft = 10 ft and Page 6 reports front_setback_ft = 8 ft:
    - Sets parameter status = 'CONFLICT'
    - Retains all conflicting sources with their page numbers, evidences, and context spans
    - Adds an explicit conflict warning for human auditor review
    """
    grouped = {}
    for v in raw_values_list:
        v_dict = v if isinstance(v, dict) else (v.model_dump() if hasattr(v, "model_dump") else {})
        k = v_dict.get("key")
        val = v_dict.get("value")
        if not k or val is None:
            continue
        grouped.setdefault(k, []).append(v_dict)

    resolved_values = {}
    conflict_flags = []

    for k, items in grouped.items():
        if len(items) == 1:
            it = items[0]
            val = it.get("value")
            ev = it.get("evidence", "").strip()
            pg = it.get("page") or 1
            ver_res = verify_spatial_numeric_evidence(k, val, ev, pg, pages_list)
            resolved_values[k] = {
                **it,
                "status": ver_res["status"],
                "evidence_tier": ver_res["tier"],
                "context_span": ver_res["context_span"] or ev,
                "tier_multiplier": ver_res["multiplier"],
                "is_conflict": False,
                "conflicting_sources": [],
            }
        else:
            distinct_vals = []
            for it in items:
                try:
                    v_num = float(it.get("value"))
                except Exception:
                    continue
                # 0.05 unit tolerance absorbs CAD rounding / unit conversion noise.
                if not any(abs(v_num - dv["value"]) < 0.05 for dv in distinct_vals):
                    distinct_vals.append(
                        {
                            "value": v_num,
                            "page": it.get("page") or 1,
                            "evidence": it.get("evidence", ""),
                            "context_span": it.get("context_span") or it.get("evidence", ""),
                        }
                    )

            if len(distinct_vals) > 1:
                sources_str = " vs ".join(
                    [f"Page {dv['page']} ({dv['value']} ft/units, ev: '{dv['evidence']}')" for dv in distinct_vals]
                )
                conflict_msg = f"CROSS-PAGE CONFLICT: '{k}' has conflicting values across sheets: {sources_str}"
                conflict_flags.append(conflict_msg)

                base_item = items[0]
                resolved_values[k] = {
                    **base_item,
                    "value": distinct_vals[0]["value"],
                    "status": "CONFLICT",
                    "evidence_tier": "CROSS_PAGE_CONFLICT",
                    "tier_multiplier": 0.40,
                    "is_conflict": True,
                    "conflicting_sources": distinct_vals,
                    "context_span": f"Conflicting multi-page values: {sources_str}",
                    "conflict_summary": conflict_msg,
                }
            else:
                it = items[0]
                val = it.get("value")
                ev = it.get("evidence", "").strip()
                pg = it.get("page") or 1
                ver_res = verify_spatial_numeric_evidence(k, val, ev, pg, pages_list)
                resolved_values[k] = {
                    **it,
                    "status": ver_res["status"],
                    "evidence_tier": ver_res["tier"],
                    "context_span": ver_res["context_span"] or ev,
                    "tier_multiplier": ver_res["multiplier"],
                    "is_conflict": False,
                    "conflicting_sources": [],
                }

    return resolved_values, conflict_flags
