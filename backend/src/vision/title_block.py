"""Find title-block / stamp regions on mixed ANSI/ISO sheet layouts.

Keyword hits are scored per page zone. If OCR is empty, landscape vs portrait
geometric fallbacks still send a plausible panel to vision.
"""

import pymupdf as fitz

from src.config.prompts import TITLE_BLOCK_KEYS


def detect_title_block_regions(pg, words):
    """Dynamically detects title blocks and signature/stamp panels across various sheet layouts.

    Supports:
    - Bottom-right corner panels
    - Right vertical panel/margin (standard ANSI/ISO architectural & engineering sheets)
    - Bottom horizontal strip/banner
    - Top header/banner
    - Left vertical panel/margin
    - Scanned/non-OCR drawings via layout-adaptive geometric candidates
    """
    W, H = pg.rect.width, pg.rect.height

    tb_matches = []
    for w in words:
        w_text = w[4].upper()
        if any(k in w_text for k in TITLE_BLOCK_KEYS):
            tb_matches.append(fitz.Rect(w[0], w[1], w[2], w[3]))

    zones = {
        "Bottom-Right Title Block & Seals": fitz.Rect(W * 0.50, H * 0.60, W, H).normalize(),
        "Right-Margin Title Block & Info Panel": fitz.Rect(W * 0.72, 0, W, H).normalize(),
        "Bottom-Strip Title Block & Schedules": fitz.Rect(0, H * 0.70, W, H).normalize(),
        "Top-Banner Title & Project Header": fitz.Rect(0, 0, W, H * 0.28).normalize(),
        "Left-Margin Title & Stamp Panel": fitz.Rect(0, 0, W * 0.28, H).normalize(),
    }

    found_crops = []

    if tb_matches:
        # Rank zones by how many title-block keywords they contain.
        zone_hits = {
            z_name: [r for r in tb_matches if z_rect.contains(r) or not (z_rect & r).is_empty]
            for z_name, z_rect in zones.items()
        }
        sorted_zones = sorted(zone_hits.items(), key=lambda x: len(x[1]), reverse=True)

        for z_name, hits in sorted_zones:
            if len(hits) >= 2:
                box = hits[0]
                for hb in hits[1:]:
                    box |= hb
                expanded_box = fitz.Rect(
                    max(0, box.x0 - 35), max(0, box.y0 - 35), min(W, box.x1 + 35), min(H, box.y1 + 35)
                ).normalize()

                if expanded_box.width > 80 and expanded_box.height > 60:
                    found_crops.append((f"Detected {z_name}", expanded_box))

    if not found_crops:
        if W > H:  # Landscape
            found_crops.append(("Right-Margin Title Block", zones["Right-Margin Title Block & Info Panel"]))
            found_crops.append(("Bottom-Right Title Block & Seals", zones["Bottom-Right Title Block & Seals"]))
        else:  # Portrait
            found_crops.append(("Bottom-Strip Title Block & Seals", zones["Bottom-Strip Title Block & Schedules"]))
            found_crops.append(("Bottom-Right Title Block", zones["Bottom-Right Title Block & Seals"]))

    return found_crops
