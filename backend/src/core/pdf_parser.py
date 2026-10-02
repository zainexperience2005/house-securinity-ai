"""Low-level PDF helpers: hidden text, CAD path stats, and sandboxed text packing.

``pack`` wraps page text in XML tags so the model treats it as data, not
instructions. Character caps keep the prompt under typical context limits.
"""

import json

import pymupdf as fitz


def hidden_text(pg):
    """Inspects text spans in a page to detect hidden or obfuscated text signals:

    Types of hidden text signals detected:
    1. Invisible render mode: rendering mode set to invisible (type 3).
    2. White-on-white / monochromatic: text color set to pure RGB (1.0, 1.0, 1.0).
    3. Tiny / Micro-font: font size smaller than 2.5 points or negative.
    4. Transparent / Low-opacity: alpha opacity set below 0.1.
    5. Off-page coordinates: text bounding box lies outside the page mediabox/cropbox.
    6. Clipped / Degenerate bounding box: width < 1.0pt or height < 1.0pt.
    """
    out = []
    try:
        for sp in pg.get_texttrace():
            t = "".join(chr(c[0]) for c in sp.get("chars", [])).strip()
            if not t:
                continue
            bbox = sp.get("bbox", [0, 0, 0, 0])
            r = fitz.Rect(bbox)
            # Multiple signals can fire together (e.g. white + tiny font).
            why = [
                w
                for w, bad in (
                    ("invisible_render_mode", sp.get("type") == 3),
                    ("white_text", tuple(sp.get("color") or ()) == (1.0, 1.0, 1.0)),
                    ("micro_font", sp.get("size", 9) < 2.5),
                    ("low_opacity", sp.get("opacity", 1.0) < 0.1),
                    ("off_page", not pg.rect.intersects(r)),
                    ("degenerate_bbox", r.width < 1.0 or r.height < 1.0),
                )
                if bad
            ]
            if why:
                out.append(
                    {
                        "text": t[:200],
                        "reasons": why,
                        "bbox": [round(v, 1) for v in bbox],
                        "signal_strength": "HIGH" if len(why) > 1 or "invisible_render_mode" in why else "MEDIUM",
                    }
                )
    except Exception:
        pass
    return out[:50]


def extract_cad_vector_geometry(pg):
    """Extracts true CAD & vector drawing geometry elements from a sheet:
    - Path counts by type: lines, rects, curves, polylines
    - Vector bounding boxes and dimensional markers
    - Stroke & fill layer properties
    """
    try:
        drawings = pg.get_drawings()
    except Exception:
        drawings = []

    line_count = 0
    rect_count = 0
    curve_count = 0
    closed_polys = 0
    stroke_colors = set()
    fill_colors = set()

    for d in drawings:
        items = d.get("items", [])
        if d.get("fill"):
            closed_polys += 1
            if isinstance(d["fill"], (tuple, list)):
                fill_colors.add(tuple(round(c, 2) for c in d["fill"]))
        if d.get("color"):
            if isinstance(d["color"], (tuple, list)):
                stroke_colors.add(tuple(round(c, 2) for c in d["color"]))

        for it in items:
            it_type = it[0]
            if it_type == "l":  # line
                line_count += 1
            elif it_type == "re":  # rectangle
                rect_count += 1
            elif it_type in ("c", "qu"):  # bezier curve / quad
                curve_count += 1

    return {
        "total_vector_paths": len(drawings),
        "lines": line_count,
        "rectangles": rect_count,
        "curves": curve_count,
        "closed_polygons": closed_polys,
        "has_vector_cad": len(drawings) > 10,  # Heuristic: sparse lines ≠ CAD plan.
        "unique_stroke_colors": len(stroke_colors),
        "unique_fill_colors": len(fill_colors),
    }


def pack(s, cap=20000, page_numbers=None):
    """Serialize selected pages into an inert XML envelope for the vision prompt.

    Args:
        s: Pipeline state containing ``pages``.
        cap: Hard character cap after join (truncates the whole envelope).
        page_numbers: If set, only those 1-based page numbers are included
            (architectural vs structural isolation).
    """
    allowed_pages = set(page_numbers) if page_numbers is not None else None
    out = ['<untrusted_document_data source="pdf_submission">']
    for p in s.get("pages", []):
        p_num = p["n"]
        if allowed_pages is not None and p_num not in allowed_pages:
            continue
        txt = p["text"].strip()
        out.append(f'<page number="{p_num}">')
        if txt:
            out.append(f"<text_content>\n{txt[:6000]}\n</text_content>")
        for k in ("annots", "widgets", "hidden", "hints", "links", "vector_cad"):
            if p.get(k):
                out.append(f'<{k} page="{p_num}">{json.dumps(p[k], separators=(",", ":"))[:2500]}</{k}>')
        out.append("</page>")
    out.append("</untrusted_document_data>")
    return "\n".join(out)[:cap]
