"""Completeness of a statutory six-part housing submission package."""


def evaluate_document_completeness(doc_type_summary, checks, pages_list, sheet_audit):
    """Evaluates submission package completeness against standard statutory submission requirements.

    Mandatory submission components for complete approval:
    1. Site / Block Plan (site_plan)
    2. Architectural Floor Plans (floor_plans)
    3. Elevations & Sections (sections_elevations)
    4. Structural Layout / Foundation Plan (foundation_plan)
    5. Structural Details / Schedules & Notes (column_schedule, beam_schedule, structural_notes)
    6. Structural Stability Certificate (stability_cert)
    """
    has_arch = (doc_type_summary or {}).get("has_architectural", False)
    has_struct = (doc_type_summary or {}).get("has_structural", False)
    has_cert = (doc_type_summary or {}).get("has_stability_certificate", False)

    master_expected = [
        {"id": "site_plan", "name": "Site / Block Plan", "discipline": "Architectural", "mandatory": True},
        {"id": "floor_plans", "name": "Architectural Floor Plans", "discipline": "Architectural", "mandatory": True},
        {
            "id": "sections_elevations",
            "name": "Building Sections & Elevations",
            "discipline": "Architectural",
            "mandatory": True,
        },
        {
            "id": "foundation_plan",
            "name": "Structural Foundation & Layout Plan",
            "discipline": "Structural",
            "mandatory": True,
        },
        {
            "id": "structural_details",
            "name": "Structural Schedules & General Notes",
            "discipline": "Structural",
            "mandatory": True,
        },
        {
            "id": "stability_certificate",
            "name": "Structural Stability Certificate (Signed & Stamped)",
            "discipline": "Certification",
            "mandatory": True,
        },
    ]

    submitted = []
    missing = []

    # 1. Site Plan
    sp_chk = (checks or {}).get("site_plan", {})
    # PASS or PENDING both count as "submitted": PENDING means present but unconfirmed.
    if has_arch and sp_chk.get("status") in ("PASS", "PENDING"):
        submitted.append(
            {"id": "site_plan", "name": "Site / Block Plan", "status": "SUBMITTED", "page": sp_chk.get("page")}
        )
    else:
        missing.append(
            {
                "id": "site_plan",
                "name": "Site / Block Plan",
                "severity": "HIGH",
                "reason": "Missing or illegible site/block plan",
            }
        )

    # 2. Floor Plans
    fp_chk = (checks or {}).get("floor_plans", {})
    if has_arch and fp_chk.get("status") in ("PASS", "PENDING"):
        submitted.append(
            {
                "id": "floor_plans",
                "name": "Architectural Floor Plans",
                "status": "SUBMITTED",
                "page": fp_chk.get("page"),
            }
        )
    else:
        missing.append(
            {
                "id": "floor_plans",
                "name": "Architectural Floor Plans",
                "severity": "CRITICAL",
                "reason": "Missing architectural floor plans",
            }
        )

    # 3. Sections & Elevations
    se_chk = (checks or {}).get("sections_elevations", {})
    if has_arch and se_chk.get("status") in ("PASS", "PENDING"):
        submitted.append(
            {
                "id": "sections_elevations",
                "name": "Building Sections & Elevations",
                "status": "SUBMITTED",
                "page": se_chk.get("page"),
            }
        )
    else:
        missing.append(
            {
                "id": "sections_elevations",
                "name": "Building Sections & Elevations",
                "severity": "HIGH",
                "reason": "Missing building cross-section or exterior elevations",
            }
        )

    # 4. Structural Foundation Plan
    fnd_chk = (checks or {}).get("foundation_plan", {})
    if has_struct and fnd_chk.get("status") in ("PASS", "PENDING"):
        submitted.append(
            {
                "id": "foundation_plan",
                "name": "Structural Foundation & Layout Plan",
                "status": "SUBMITTED",
                "page": fnd_chk.get("page"),
            }
        )
    else:
        missing.append(
            {
                "id": "foundation_plan",
                "name": "Structural Foundation & Layout Plan",
                "severity": "HIGH",
                "reason": "Missing structural foundation layout drawing sheet",
            }
        )

    # 5. Structural Schedules & Notes
    col_chk = (checks or {}).get("column_schedule", {})
    notes_chk = (checks or {}).get("structural_notes", {})
    if has_struct and (col_chk.get("status") in ("PASS", "PENDING") or notes_chk.get("status") in ("PASS", "PENDING")):
        submitted.append(
            {
                "id": "structural_details",
                "name": "Structural Schedules & General Notes",
                "status": "SUBMITTED",
                "page": col_chk.get("page") or notes_chk.get("page"),
            }
        )
    else:
        missing.append(
            {
                "id": "structural_details",
                "name": "Structural Schedules & General Notes",
                "severity": "HIGH",
                "reason": "Missing column/beam schedules and structural design notes",
            }
        )

    # 6. Stability Certificate
    cert_chk = (checks or {}).get("stability_cert", {})
    if has_cert and cert_chk.get("status") in ("PASS", "PENDING"):
        submitted.append(
            {
                "id": "stability_certificate",
                "name": "Structural Stability Certificate",
                "status": "SUBMITTED",
                "page": cert_chk.get("page"),
            }
        )
    else:
        missing.append(
            {
                "id": "stability_certificate",
                "name": "Structural Stability Certificate",
                "severity": "CRITICAL",
                "reason": "Missing Structural Stability Certificate (PEC Engineer signed & stamped)",
            }
        )

    total_req = len(master_expected)
    sub_count = len(submitted)
    score_pct = round((sub_count / total_req) * 100, 1)

    comp_status = "COMPLETE" if score_pct == 100.0 else ("PARTIALLY_COMPLETE" if score_pct >= 50.0 else "INCOMPLETE")

    flags = [
        f"COMPLETENESS DEFICIENCY: Missing expected submission document '{m['name']}' ({m['reason']})" for m in missing
    ]

    return {
        "completeness_score_pct": score_pct,
        "completeness_status": comp_status,
        "is_complete": bool(score_pct == 100.0),
        "submitted_count": sub_count,
        "expected_count": total_req,
        "submitted_components": submitted,
        "missing_components": missing,
        "completeness_flags": flags,
    }
