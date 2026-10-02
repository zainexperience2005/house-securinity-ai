"""Upright page rendering for vision: rotation detection and size-capped PNGs.

CAD PDFs often store rotation in the page flag or only in text direction
vectors. Vision crops must be upright and dimension-capped so OpenAI tile
counts stay predictable.
"""

import base64

import pymupdf as fitz


def get_page_effective_rotation(pg):
    """Determines effective rotation needed so the drawing page renders strictly upright (0 deg).

    Checks:
    1. Native PyMuPDF page rotation flag (0, 90, 180, 270).
    2. Text line direction vectors in block dicts if rotation metadata is 0.
    """
    rot = (pg.rotation or 0) % 360
    if rot != 0:
        return rot

    try:
        dict_data = pg.get_text("dict")
        dirs = []
        for b in dict_data.get("blocks", []):
            if b.get("type") == 0:
                for line in b.get("lines", []):
                    direction = line.get("dir")
                    if direction:
                        dirs.append((round(direction[0], 2), round(direction[1], 2)))
        if dirs:
            # dir (1,0) is left-to-right Latin; (0,1)/(0,-1) imply 90° pages.
            vert_down = sum(1 for d in dirs if d == (0.0, 1.0) or d == (0, 1))
            vert_up = sum(1 for d in dirs if d == (0.0, -1.0) or d == (0, -1))
            upside_down = sum(1 for d in dirs if d == (-1.0, 0.0) or d == (-1, 0))
            total = len(dirs)
            if vert_down > 0.6 * total:
                return 270
            elif vert_up > 0.6 * total:
                return 90
            elif upside_down > 0.6 * total:
                return 180
    except Exception:
        pass
    return 0


def png(pg, clip=None, side=1024):
    """Renders a page or clipped bounding box to an optimized, crisp PNG base64 string.

    Optimizations:
    - Normalizes coordinates and page orientation so every sheet is rendered strictly upright (0 deg).
    - Explicitly calculates scale matrix (fitz.Matrix) to strictly bound the longest
      dimension to `side` pixels, guaranteeing deterministic image sizing and OpenAI tile budgeting.
    - Clamps scaling between 0.5x and 3.0x to avoid memory explosions on giant CAD sheets
      or extreme blur on small crops.
    """
    r = (clip or pg.rect).normalize()
    if r.is_empty or r.width <= 0 or r.height <= 0:
        r = pg.rect.normalize()

    max_dim = max(r.width, r.height)
    if max_dim <= 0:
        scale = 1.0
    else:
        scale = side / max_dim
        scale = max(0.5, min(3.0, scale))

    matrix = fitz.Matrix(scale, scale)
    eff_rot = get_page_effective_rotation(pg)
    # Native page.rotation is applied by PyMuPDF; extra prerotate is only for
    # text-inferred rotation when the page flag is still 0.
    if pg.rotation == 0 and eff_rot != 0:
        matrix.prerotate(eff_rot)

    pix = pg.get_pixmap(clip=r, matrix=matrix, alpha=False)
    return base64.b64encode(pix.tobytes("png")).decode("utf-8")
