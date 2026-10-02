"""Corroborate vision numbers against the PDF text layer and blend confidences.

Tiers (VECTOR_TEXT_AND_VISION → UNVERIFIED) scale Jev confidence so a
vision-only claim cannot look as certain as a text-backed one.
"""

import re


def verify_spatial_numeric_evidence(val_key, val_num, raw_evidence, page_num, pages_list):
    """Contextual and spatial evidence verification engine using a multi-tiered evidence hierarchy.

    Evidence Hierarchy Tiers:
    1. VECTOR_TEXT_AND_VISION (Level 1, Multiplier: 1.0)
    2. OCR_AND_VISION (Level 2, Multiplier: 0.88)
    3. VISION_ONLY (Level 3, Multiplier: 0.72)
    4. UNVERIFIED_OR_DISCREPANCY (Level 4, Multiplier: 0.45)
    """
    if val_num is None and not raw_evidence:
        return {
            "tier": "NO_VALUE",
            "status": "not_extracted",
            "multiplier": 0.5,
            "bbox": None,
            "context_span": "",
            "verified": False,
        }

    target_page = None
    for p in pages_list:
        if p.get("n") == page_num:
            target_page = p
            break

    if not target_page and pages_list:
        target_page = pages_list[0]

    page_text = target_page.get("text", "") if target_page else ""
    page_words = target_page.get("hints", []) if target_page else []
    has_text = bool(page_text.strip())

    if not has_text:
        return {
            "tier": "VISION_ONLY",
            "status": "vision_only",
            "multiplier": 0.72,
            "bbox": None,
            "context_span": f"Visual extraction from raster drawing (p.{page_num})",
            "verified": True,
        }

    toks = re.findall(r"\d+(?:\.\d+)?", raw_evidence) if raw_evidence else []
    if val_num is not None:
        toks.append(str(val_num))
        try:
            if float(val_num).is_integer():
                toks.append(str(int(val_num)))
        except Exception:
            pass

    key_words = [
        w
        for w in val_key.lower().replace("_", " ").split()
        if len(w) > 3 and w not in ("ft", "pct", "gallons", "psi", "stated", "detail")
    ]

    # 1. Check exact raw evidence snippet in page text
    if raw_evidence and raw_evidence.strip().lower() in page_text.lower():
        return {
            "tier": "VECTOR_TEXT_AND_VISION",
            "status": "text_verified",
            "multiplier": 1.0,
            "bbox": None,
            "context_span": raw_evidence.strip(),
            "verified": True,
        }

    # 2. Check contextual sentence/block containing both keyword token and numeric token
    lines = page_text.splitlines()
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        line_lower = line_clean.lower()
        has_kw = any(kw in line_lower for kw in key_words) if key_words else True
        has_num = any(t in line_clean for t in toks) if toks else False
        if has_kw and has_num:
            return {
                "tier": "VECTOR_TEXT_AND_VISION",
                "status": "text_verified",
                "multiplier": 1.0,
                "bbox": None,
                "context_span": line_clean[:180],
                "verified": True,
            }

    # 3. Check nearby spatial hints
    for h in page_words:
        h_lower = h.lower()
        if any(kw in h_lower for kw in key_words) and any(t in h for t in toks):
            return {
                "tier": "OCR_AND_VISION",
                "status": "text_verified",
                "multiplier": 0.88,
                "bbox": None,
                "context_span": h[:180],
                "verified": True,
            }

    # 4. If tokens found somewhere on page
    if toks and any(t in page_text for t in toks):
        return {
            "tier": "OCR_AND_VISION",
            "status": "text_verified",
            "multiplier": 0.80,
            "bbox": None,
            "context_span": f"Numeric token '{toks[0]}' found in page text layer",
            "verified": True,
        }

    # 5. Mismatch / Discrepancy
    return {
        "tier": "UNVERIFIED_OR_DISCREPANCY",
        "status": "unverified_vs_text",
        "multiplier": 0.45,
        "bbox": None,
        "context_span": f"Evidence '{raw_evidence}' not corroborated by page text layer",
        "verified": False,
    }


def compute_combined_confidence(decision_conf, probabilities, source_multiplier, obs_seen="yes", has_evidence=True):
    """Calculates combined confidence score taking into account decision certainty,
    extraction evidence hierarchy, and visual observation clarity.

    Formula:
    C_combined = C_decision * M_source * M_observation
    """
    try:
        dec = float(decision_conf if decision_conf is not None else 0.5)
    except Exception:
        dec = 0.5

    obs_mult = 1.0 if obs_seen == "yes" else (0.65 if obs_seen == "unclear" else 0.40)
    ev_mult = 1.0 if has_evidence else 0.60

    combined = dec * float(source_multiplier) * obs_mult * ev_mult
    return round(max(0.05, min(1.0, combined)), 2)
