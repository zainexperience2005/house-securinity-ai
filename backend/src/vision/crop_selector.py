"""Keyword clustering for high-resolution vision crops.

Full-sheet overviews are cheap but illegible for small CAD dimensions.
Crops are built around HINT_KEYS, merged when they overlap, and capped by
MAX_CROPS_PER_PAGE. Certificates use letterhead + signature bands instead.
"""

import math

import pymupdf as fitz

from src.config.prompts import HINT_KEYS
from src.config.settings import MAX_CROPS_PER_PAGE

from .title_block import detect_title_block_regions


def nearby(words, R=180):
    """Finds neighboring text around keywords with directional bearings and spatial proximity.

    Associates dimension numbers with contextual labels:
    - Inline (same horizontal baseline, following or preceding the keyword)
    - Below (dimension beneath beam/room label)
    - Above (dimension above plinth/foundation marker)
    - Distance-weighted ranking to prevent linking unrelated numbers across drawing panels.
    """
    hits = []
    seen = set()
    for w in words:
        w_text = w[4].upper()
        if any(k in w_text for k in HINT_KEYS):
            cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2

            candidates = []
            for x in words:
                if x == w:
                    continue
                nx_cx, nx_cy = (x[0] + x[2]) / 2, (x[1] + x[3]) / 2
                dx = nx_cx - cx
                dy = nx_cy - cy
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < R:
                    # CAD dimensions sit on the same baseline as labels or
                    # immediately above/below; diagonals are weaker associations.
                    if abs(dy) <= 12 and dx > 0:
                        rel = "inline_right"
                    elif abs(dy) <= 12 and dx < 0:
                        rel = "inline_left"
                    elif dy > 0 and abs(dx) < 60:
                        rel = "below"
                    elif dy < 0 and abs(dx) < 60:
                        rel = "above"
                    elif dx > 0:
                        rel = "diagonal_right"
                    else:
                        rel = "diagonal_left"

                    candidates.append(
                        (dist, rel, x[4], [round(x[0], 1), round(x[1], 1), round(x[2], 1), round(x[3], 1)])
                    )

            if candidates:
                candidates.sort(key=lambda c: c[0])
                grouped = {}
                for _dist, rel, text, _bbox in candidates[:8]:
                    grouped.setdefault(rel, []).append(text)

                parts = [f"{rel}: {' '.join(toks)}" for rel, toks in grouped.items()]
                entry = f"{w[4]} -> [{' | '.join(parts)}]"
                if entry not in seen:
                    seen.add(entry)
                    hits.append(entry)

    return hits[:60]


def find_intelligent_sheet_crops(pg, ptype="architectural_drawing"):
    """Finds high-value dimension, title-block & schedule clusters using keyword anchors and spatial proximity.

    Workflow:
    1. Dynamically detects title blocks across multiple positions (bottom-right, right-margin, bottom-strip, top, left).
    2. Finds keyword anchors on the page (e.g. SETBACK, OPEN, PLINTH, COLUMN, BEAM, REBAR, PEC, SIGNATURE).
    3. Identifies surrounding dimension numbers and annotations within a spatial radius.
    4. Computes bounding boxes enclosing semantic clusters.
    5. Merges overlapping crop boxes and bounds to max crops per page.
    """
    W, H = pg.rect.width, pg.rect.height
    try:
        words = pg.get_text("words")
    except Exception:
        words = []

    clusters = []

    # If stability certificate, capture the letterhead (top 35%) and signature block (bottom 40%)
    if ptype == "stability_certificate":
        clusters.append(("Certificate Letterhead & Authority", fitz.Rect(0, 0, W, H * 0.35).normalize()))
        clusters.append(("Engineer Stamp & Signature Block", fitz.Rect(0, H * 0.55, W, H).normalize()))
        return clusters[:MAX_CROPS_PER_PAGE]

    # 1. Dynamic Title Block & Seal detection (multi-panel & multi-position aware)
    tb_crops = detect_title_block_regions(pg, words)
    clusters.extend(tb_crops[:2])

    # 2. Spatial clustering around semantic drawing keywords
    for w in words:
        w_text = w[4].upper()
        if any(k in w_text for k in HINT_KEYS):
            cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2

            near_words = [
                fitz.Rect(nw[0], nw[1], nw[2], nw[3])
                for nw in words
                if abs((nw[0] + nw[2]) / 2 - cx) < 220 and abs((nw[1] + nw[3]) / 2 - cy) < 180
            ]

            if near_words:
                cluster_box = near_words[0]
                for nb in near_words[1:]:
                    cluster_box |= nb
                cluster_box = fitz.Rect(
                    max(0, cluster_box.x0 - 25),
                    max(0, cluster_box.y0 - 25),
                    min(W, cluster_box.x1 + 25),
                    min(H, cluster_box.y1 + 25),
                ).normalize()

                if not cluster_box.is_empty and cluster_box.width > 60 and cluster_box.height > 60:
                    clusters.append((f"Cluster near {w[4]}", cluster_box))

    # 3. Merge overlapping cluster boxes
    merged = []
    for label, r in clusters:
        overlapped = False
        for i, (m_label, m_r) in enumerate(merged):
            intersection = (r & m_r).normalize()
            if not intersection.is_empty and (intersection.get_area() > 0.35 * min(r.get_area(), m_r.get_area())):
                merged[i] = (f"{m_label} + {label}", (m_r | r).normalize())
                overlapped = True
                break
        if not overlapped:
            merged.append((label, r))

    # 4. Fallbacks for scanned images
    if len(merged) < 2:
        merged.append(("Site Plan & Setbacks Region", fitz.Rect(0, 0, W * 0.75, H * 0.75).normalize()))
        merged.append(("Schedules & Area Table", fitz.Rect(W * 0.50, 0, W, H * 0.75).normalize()))

    return merged[:MAX_CROPS_PER_PAGE]
