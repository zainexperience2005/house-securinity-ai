"""Duplicate-sheet detection using text, CAD path counts, and a gray thumbnail.

Used after ingest so identical copies of the same drawing do not inflate
completeness or create false cross-page conflicts.
"""

import hashlib
import re

import pymupdf as fitz


def detect_duplicate_pages(doc, pages_list):
    """Detects duplicate or identical pages within the submission via multi-signal hashing:
    1. SHA-256 hash of normalized text layer.
    2. CAD vector path geometry signature (lines, rects, curves, polygons).
    3. Perceptual 64x64 pixmap thumbnail MD5 digest.
    """
    fingerprints = []
    for idx, p in enumerate(pages_list):
        p_num = p.get("n", idx + 1)
        # Normalize whitespace so printer reflows do not defeat the text hash.
        raw_text = re.sub(r"\s+", " ", p.get("text", "")).strip().lower()
        text_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest() if len(raw_text) > 15 else None

        cad = p.get("vector_cad", {})
        cad_sig = f"{cad.get('lines', 0)}_{cad.get('rectangles', 0)}_{cad.get('curves', 0)}_{cad.get('closed_polygons', 0)}_{cad.get('total_vector_paths', 0)}"

        pix_hash = None
        if doc and p_num - 1 < len(doc):
            try:
                pg = doc[p_num - 1]
                w = max(1.0, pg.rect.width)
                h = max(1.0, pg.rect.height)
                # Tiny grayscale pixmap: cheap perceptual hash for scanned duplicates.
                thumb = pg.get_pixmap(matrix=fitz.Matrix(64.0 / w, 64.0 / h), colorspace=fitz.csGRAY)
                pix_hash = hashlib.md5(thumb.samples).hexdigest()
            except Exception:
                pass

        fingerprints.append(
            {"page": p_num, "text_hash": text_hash, "cad_sig": cad_sig, "pix_hash": pix_hash, "text_len": len(raw_text)}
        )

    duplicates = []
    seen_pairs = set()

    for i in range(len(fingerprints)):
        for j in range(i + 1, len(fingerprints)):
            fp_i = fingerprints[i]
            fp_j = fingerprints[j]
            p_i = fp_i["page"]
            p_j = fp_j["page"]

            is_dup = False
            dup_type = None

            if fp_i["text_hash"] and fp_i["text_hash"] == fp_j["text_hash"] and fp_i["cad_sig"] == fp_j["cad_sig"]:
                is_dup = True
                dup_type = "EXACT_TEXT_AND_VECTOR_DUPLICATE"
            elif (
                fp_i["pix_hash"]
                and fp_i["pix_hash"] == fp_j["pix_hash"]
                and fp_i["cad_sig"] == fp_j["cad_sig"]
                and fp_i["cad_sig"] != "0_0_0_0_0"
            ):
                is_dup = True
                dup_type = "EXACT_VISUAL_AND_CAD_DUPLICATE"
            elif fp_i["pix_hash"] and fp_i["pix_hash"] == fp_j["pix_hash"] and fp_i["text_len"] == 0:
                is_dup = True
                dup_type = "EXACT_RASTER_SCAN_DUPLICATE"

            if is_dup:
                pair_key = (p_i, p_j)
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    duplicates.append(
                        {
                            "original_page": p_i,
                            "duplicate_page": p_j,
                            "duplicate_type": dup_type,
                            "similarity": "100% IDENTICAL",
                            "note": f"Page {p_j} is an exact duplicate of Page {p_i}",
                        }
                    )

    return {
        "has_duplicates": len(duplicates) > 0,
        "duplicate_count": len(duplicates),
        "duplicates": duplicates,
        "duplicate_pages": [d["duplicate_page"] for d in duplicates],
    }
