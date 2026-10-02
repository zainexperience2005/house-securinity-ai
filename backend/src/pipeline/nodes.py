"""LangGraph node implementations for one scrutiny pass.

Each ``n_*`` function takes state ``S`` and returns a partial update. Order
is enforced in ``graph.py``. Heavy I/O (PyMuPDF, OpenAI, Jev) lives here.
"""

import json
import os
import re
import statistics

import pymupdf as fitz
from typesafe_sdk import Choice

from src.auditors.bylaw_auditor import bylaw_check
from src.auditors.completeness_model import evaluate_document_completeness
from src.auditors.conflict_resolver import resolve_cross_page_conflicts
from src.auditors.evidence_verifier import (
    compute_combined_confidence,
    verify_spatial_numeric_evidence,
)
from src.auditors.revision_auditor import (
    filter_values_to_master_revision,
    resolve_authoritative_revisions,
)
from src.auditors.sheet_auditor import audit_sheet_numbering
from src.config.bylaws import STRUCTURAL_KEYS, VALUE_KEYS, get_bylaws_for_plot
from src.config.checklists import (
    ARCHITECTURAL_CHECKLIST,
    CERTIFICATE_CHECKLIST,
    CHECKLIST,
    DOC_TYPES,
    STATUS,
    STRUCTURAL_CHECKLIST,
)
from src.config.settings import settings
from src.core.client import jev_call
from src.core.duplicates import detect_duplicate_pages
from src.core.orientation import png
from src.core.pdf_parser import extract_cad_vector_geometry, hidden_text, pack
from src.core.security import scrub
from src.vision.crop_selector import find_intelligent_sheet_crops, nearby
from src.vision.extractor import run_vision_extraction_batch


def n_ingest(s):
    """Open the PDF, extract text/CAD/layers, scrub injection, hash duplicates.

    Sets ``unreadable`` when the file is missing, encrypted, empty, corrupt,
    or has no text, images, or vector CAD at all.
    """
    pdf_path = s.get("pdf", "")
    flags, pages, emb, layers = [], [], [], []
    security_audit = []
    meta = {}
    cad_summary = {
        "total_vector_paths": 0,
        "lines": 0,
        "rectangles": 0,
        "curves": 0,
        "closed_polygons": 0,
        "has_vector_cad": False,
    }

    if not pdf_path or not os.path.exists(pdf_path):
        flags.append(f"PDF file not found or inaccessible at path: '{pdf_path}'")
        return {
            "pages": [],
            "meta": {},
            "embedded": [],
            "layers": [],
            "flags": flags,
            "security_audit": [],
            "cad_geometry": cad_summary,
            "duplicates_audit": {"has_duplicates": False, "duplicates": []},
            "unreadable": True,
        }

    try:
        with fitz.open(pdf_path) as doc:
            if doc.needs_pass:
                flags.append(
                    "PDF is password-protected / encrypted and cannot be scrutinized without the decryption password."
                )
                return {
                    "pages": [],
                    "meta": {},
                    "embedded": [],
                    "layers": [],
                    "flags": flags,
                    "security_audit": [],
                    "cad_geometry": cad_summary,
                    "duplicates_audit": {"has_duplicates": False, "duplicates": []},
                    "unreadable": True,
                }

            if doc.is_closed or doc.page_count == 0:
                flags.append("PDF contains 0 pages or is an empty document.")
                return {
                    "pages": [],
                    "meta": {},
                    "embedded": [],
                    "layers": [],
                    "flags": flags,
                    "security_audit": [],
                    "cad_geometry": cad_summary,
                    "duplicates_audit": {"has_duplicates": False, "duplicates": []},
                    "unreadable": True,
                }

            meta = {
                k: scrub(v, flags, f"metadata.{k}", page_num=0, security_log=security_audit)
                for k, v in (doc.metadata or {}).items()
                if v
            }
            try:
                # Embedded files are listed but not opened (malware / extra payload risk).
                emb = [{"name": n, "size": doc.embfile_info(n).get("size")} for n in doc.embfile_names()]
            except Exception:
                emb = []

            try:
                layers = [{"name": lyr["text"], "on": lyr["on"]} for lyr in doc.layer_ui_configs()]
            except Exception:
                layers = []

            if emb:
                flags.append(f"embedded files present (not read): {[e['name'] for e in emb]}")
            if any(not lyr["on"] for lyr in layers):
                flags.append(f"hidden (OFF) layers: {[lyr['name'] for lyr in layers if not lyr['on']]}")

            for i, pg in enumerate(doc, 1):
                try:
                    words = pg.get_text("words")
                except Exception:
                    words = []

                try:
                    spans = [
                        sp
                        for b in pg.get_text("dict")["blocks"]
                        if b["type"] == 0
                        for line in b["lines"]
                        for sp in line["spans"]
                        if sp["text"].strip()
                    ]
                except Exception:
                    spans = []

                med = statistics.median([sp["size"] for sp in spans]) if spans else 0
                # Headings: uppercase, larger than median, used later for sheet typing.
                heads = sorted(
                    {
                        (sp["text"].strip(), round(sp["size"], 1), tuple(round(v) for v in sp["bbox"]))
                        for sp in spans
                        if med
                        and sp["size"] >= 1.25 * med
                        and sp["text"].strip().isupper()
                        and 5 <= len(sp["text"].strip()) <= 70
                    },
                    key=lambda h: -h[1],
                )[:10]

                try:
                    annots = [
                        {
                            "type": a.type[1],
                            "text": scrub(
                                a.info.get("content"),
                                flags,
                                f"annotation p{i}",
                                page_num=i,
                                security_log=security_audit,
                            ).strip(),
                        }
                        for a in (pg.annots() or [])
                        if a.type[1] != "Link"
                    ][:50]
                except Exception:
                    annots = []

                try:
                    widgets = [
                        {
                            "name": w.field_name,
                            "type": w.field_type_string,
                            "value": scrub(
                                w.field_value, flags, f"form field p{i}", page_num=i, security_log=security_audit
                            ),
                        }
                        for w in (pg.widgets() or [])
                    ][:50]
                except Exception:
                    widgets = []

                hidden = [
                    {**h, "text": scrub(h["text"], flags, f"hidden text p{i}", page_num=i, security_log=security_audit)}
                    for h in hidden_text(pg)
                ]
                if hidden:
                    flags.append(
                        f"page {i}: {len(hidden)} hidden/invisible text run(s) (signals: invisible/white/tiny/off-page/clipped)"
                    )

                try:
                    images = pg.get_images()
                except Exception:
                    images = []

                cad_vec = extract_cad_vector_geometry(pg)
                cad_summary["total_vector_paths"] += cad_vec["total_vector_paths"]
                cad_summary["lines"] += cad_vec["lines"]
                cad_summary["rectangles"] += cad_vec["rectangles"]
                cad_summary["curves"] += cad_vec["curves"]
                cad_summary["closed_polygons"] += cad_vec["closed_polygons"]
                if cad_vec["has_vector_cad"]:
                    cad_summary["has_vector_cad"] = True

                if not words and images and not cad_vec["has_vector_cad"]:
                    flags.append(f"page {i}: raster scanned image only - no digital text or vector CAD layers")

                try:
                    raw_text = pg.get_text("text")
                except Exception:
                    raw_text = ""

                try:
                    links = [lnk["uri"] for lnk in pg.get_links() if lnk.get("uri")]
                except Exception:
                    links = []

                pages.append(
                    {
                        "n": i,
                        "text": scrub(raw_text, flags, f"page {i}", page_num=i, security_log=security_audit),
                        "annots": annots,
                        "widgets": widgets,
                        "hidden": hidden,
                        "heads": heads,
                        "hints": nearby(words),
                        "links": links,
                        "images": len(images),
                        "vector_cad": cad_vec,
                    }
                )

            duplicates_audit = detect_duplicate_pages(doc, pages)
            if duplicates_audit.get("has_duplicates"):
                for d in duplicates_audit.get("duplicates", []):
                    flags.append(
                        f"DUPLICATE PAGE DETECTED: Page {d['duplicate_page']} is identical to Page {d['original_page']} ({d['duplicate_type']})"
                    )

    except fitz.FileDataError as e:
        flags.append(f"PDF FileDataError: File is corrupt or not a valid PDF format ({e!s})")
        return {
            "pages": [],
            "meta": {},
            "embedded": [],
            "layers": [],
            "flags": flags,
            "security_audit": [],
            "cad_geometry": cad_summary,
            "duplicates_audit": {"has_duplicates": False, "duplicates": []},
            "unreadable": True,
        }
    except Exception as e:
        flags.append(f"PDF Ingestion Error: Failed to parse document ({e!s})")
        return {
            "pages": [],
            "meta": {},
            "embedded": [],
            "layers": [],
            "flags": flags,
            "security_audit": [],
            "cad_geometry": cad_summary,
            "duplicates_audit": {"has_duplicates": False, "duplicates": []},
            "unreadable": True,
        }

    unreadable = not any(
        p["text"].strip() or p["images"] or p["annots"] or p["vector_cad"]["has_vector_cad"] for p in pages
    )
    if unreadable:
        flags.append("Document is blank or completely unreadable (no text, images, or vector CAD elements found).")

    return {
        "pages": pages,
        "meta": meta,
        "embedded": emb,
        "layers": layers,
        "flags": flags,
        "security_audit": security_audit,
        "cad_geometry": cad_summary,
        "duplicates_audit": duplicates_audit
        if "duplicates_audit" in locals()
        else {"has_duplicates": False, "duplicates": []},
        "unreadable": unreadable,
    }


def n_gate(s):
    """Classify each page with Jev (arch / struct / cert / other) and set eligibility.

    ELIGIBLE requires at least one architectural or structural page.
    CLASSIFICATION_UNAVAILABLE is a Jev outage, not a document-type reject.
    """
    pages = s.get("pages", [])
    if not pages:
        return {
            "doc_type": {
                "choice": "other",
                "confidence": 0.0,
                "probabilities": {},
                "has_architectural": False,
                "has_structural": False,
                "has_stability_certificate": False,
                "architectural_pages": [],
                "structural_pages": [],
                "certificate_pages": [],
                "other_pages": [],
                "page_types": {},
            },
            "document_eligibility": "UNSUPPORTED_DOCUMENT",
            "jev_gate_usage": {"input_tokens": 0, "output_tokens": 0},
        }

    pages_state = {
        f"page_{p['n']}": {
            "page_number": p["n"],
            "headings": [h[0] for h in p.get("heads", [])],
            "text": p.get("text", "")[:4000],
            "hints": p.get("hints", [])[:15],
            "images_count": p.get("images", 0),
            "has_forms": bool(p.get("widgets")),
            "has_vector_cad": p.get("vector_cad", {}).get("has_vector_cad", False),
        }
        for p in pages
    }
    state = {"metadata": s.get("meta", {}), "total_pages": len(pages), "pages": pages_state}

    questions = {
        f"page_{p['n']}_type": Choice(
            criteria=DOC_TYPES,
            instructions=f"What kind of document or drawing sheet is Page {p['n']} of this submission? "
            f"Judge from pages['page_{p['n']}'] (headings, text, vector CAD and contents).",
        )
        for p in pages
    }

    answers, usage = jev_call(state, questions)

    page_types = {}
    arch_pages, struct_pages, cert_pages, other_pages = [], [], [], []

    for p in pages:
        pn = p["n"]
        ans = answers.get(f"page_{pn}_type", {})
        choice = ans.get("choice", "other")
        # A zero-confidence safe fallback from Jev must remain zero; using
        # ``or 0.5`` would silently convert an outage into false certainty.
        conf = float(ans.get("confidence", 0.0))
        probs = ans.get("probabilities", {})

        page_types[pn] = {"page": pn, "choice": choice, "confidence": conf, "probabilities": probs}

        if choice == "architectural_drawing":
            arch_pages.append(pn)
        elif choice == "structural_drawing":
            struct_pages.append(pn)
        elif choice == "stability_certificate":
            cert_pages.append(pn)
        else:
            other_pages.append(pn)

    primary_type = (
        "architectural_drawing"
        if arch_pages
        else "structural_drawing"
        if struct_pages
        else "stability_certificate"
        if cert_pages
        else "other"
    )

    primary_conf = (
        statistics.mean([page_types[p]["confidence"] for p in arch_pages])
        if arch_pages
        else statistics.mean([page_types[p]["confidence"] for p in struct_pages])
        if struct_pages
        else statistics.mean([page_types[p]["confidence"] for p in cert_pages])
        if cert_pages
        else 0.5
    )

    classification_errors = [str(answer.get("error")) for answer in answers.values() if answer.get("error")]
    if classification_errors:
        eligibility = "CLASSIFICATION_UNAVAILABLE"
    elif arch_pages or struct_pages:
        eligibility = "ELIGIBLE"
    else:
        eligibility = "UNSUPPORTED_DOCUMENT"

    doc_type_summary = {
        "choice": primary_type,
        "primary_type": primary_type,
        "confidence": round(primary_conf, 2),
        "has_architectural": bool(arch_pages),
        "has_structural": bool(struct_pages),
        "has_stability_certificate": bool(cert_pages),
        "architectural_pages": arch_pages,
        "structural_pages": struct_pages,
        "certificate_pages": cert_pages,
        "other_pages": other_pages,
        "page_types": page_types,
        "classification_error": classification_errors[0] if classification_errors else None,
    }

    return {"doc_type": doc_type_summary, "document_eligibility": eligibility, "jev_gate_usage": usage}


def n_reject(s):
    """Return a compact terminal result for files that must not enter the audit flow."""
    doc_type = s.get("doc_type") or {}
    eligibility = s.get("document_eligibility") or "UNSUPPORTED_DOCUMENT"
    pages = s.get("pages") or []

    if eligibility == "CLASSIFICATION_UNAVAILABLE":
        overall = "CLASSIFICATION_UNAVAILABLE"
        message = (
            "The document type could not be verified because the classification service was unavailable. Please retry."
        )
    elif s.get("unreadable"):
        overall = "UNSUPPORTED_DOCUMENT"
        message = "The uploaded PDF is blank, unreadable, password-protected, or not a usable engineering drawing."
    elif doc_type.get("has_stability_certificate"):
        overall = "UNSUPPORTED_DOCUMENT"
        message = "A stability certificate is supporting evidence only. Upload it together with at least one architectural or structural drawing."
    else:
        overall = "UNSUPPORTED_DOCUMENT"
        message = "This PDF is not an architectural or structural drawing submission. Upload plans, sections, elevations, or structural detail drawings instead."

    return {
        "verdict": {
            "overall": overall,
            "message": message,
            "doc_type": doc_type,
            "page_coverage": {
                "total_pages": len(pages),
                "processed_pages": [],
                "coverage_complete": False,
            },
            "checks": {},
            "values": {},
            "review_flags": list(s.get("flags") or []),
            "rejection": {
                "code": overall,
                "eligible_for_scrutiny": False,
                "detected_page_types": doc_type.get("page_types", {}),
            },
        }
    }


def n_crop(s):
    """Render a low-detail overview plus high-detail keyword/title-block crops per page."""
    shots = []
    page_coverage = {}
    page_types = s.get("doc_type", {}).get("page_types", {})

    try:
        with fitz.open(s["pdf"]) as doc:
            for p in s["pages"]:
                p_num = p["n"]
                if p_num - 1 >= len(doc):
                    continue
                pg = doc[p_num - 1]
                ptype = page_types.get(p_num, {}).get("choice", "other")
                page_shots_labels = []

                try:
                    overview_shot = {
                        "page": p_num,
                        "page_type": ptype,
                        "label": f"overview ({ptype})",
                        "detail": "low",
                        "b64": png(pg, None, 768),
                    }
                    shots.append(overview_shot)
                    page_shots_labels.append(overview_shot["label"])
                except Exception:
                    pass

                try:
                    clusters = find_intelligent_sheet_crops(pg, ptype)
                    for label, rect in clusters:
                        crop_rect = (rect & pg.rect).normalize()
                        if not crop_rect.is_empty and crop_rect.width > 25 and crop_rect.height > 25:
                            c_shot = {
                                "page": p_num,
                                "page_type": ptype,
                                "label": f"{label} ({ptype})",
                                "detail": "high",
                                "b64": png(pg, crop_rect, 768),
                            }
                            shots.append(c_shot)
                            page_shots_labels.append(c_shot["label"])
                except Exception:
                    pass

                page_coverage[p_num] = {
                    "page_number": p_num,
                    "page_type": ptype,
                    "has_overview": bool(page_shots_labels),
                    "crops_count": len(page_shots_labels),
                    "crop_labels": page_shots_labels,
                    "status": "PROCESSED" if page_shots_labels else "ERROR",
                }
    except Exception:
        pass

    return {"shots": shots, "page_coverage": page_coverage}


def n_extract(s):
    """Three isolated vision passes: architectural values, structural params, certificate fields."""
    dt = s.get("doc_type", {})
    arch_pages = dt.get("architectural_pages", [])
    struct_pages = dt.get("structural_pages", [])
    cert_pages = dt.get("certificate_pages", [])

    shots = s.get("shots", [])
    active_model = s.get("active_model") or settings.openai_model
    # Keep architectural design-value extraction isolated from structural and
    # certificate text, as required by the submission-source hierarchy.
    # Checklist judging later receives the complete package separately.
    arch_doc_text = pack(s, page_numbers=arch_pages)
    struct_doc_text = pack(s, page_numbers=struct_pages)
    cert_doc_text = pack(s, page_numbers=cert_pages)

    values = []
    structural_values = []
    certificate_details = None
    observations = []
    flags = []
    revisions = []
    revisions_table = []
    total_openai_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    # Pass 1: Architectural Extraction
    arch_shots = [sh for sh in shots if sh["page"] in arch_pages or sh["page_type"] == "architectural_drawing"]
    if arch_shots or (not struct_pages and not cert_pages):
        target_shots = arch_shots if arch_shots else shots
        header = (
            f"TARGET: ARCHITECTURAL DRAWING EXTRACTION (Pages: {arch_pages})\n"
            f"Extract numeric design values: {json.dumps(VALUE_KEYS)}\n"
            f"Extract observations for Architectural items: {json.dumps(ARCHITECTURAL_CHECKLIST)}"
        )
        parsed_arch, u_arch = run_vision_extraction_batch(
            header,
            arch_doc_text if arch_pages else pack(s),
            target_shots,
            model_name=active_model,
        )
        values.extend(parsed_arch.get("values", []))
        observations.extend(
            [o for o in parsed_arch.get("observations", []) if o["check_id"] in ARCHITECTURAL_CHECKLIST]
        )
        flags.extend(parsed_arch.get("flags", []))
        if parsed_arch.get("revisions"):
            revisions.extend(parsed_arch["revisions"])
        if parsed_arch.get("revisions_table"):
            revisions_table.extend(parsed_arch["revisions_table"])
        for k in total_openai_usage:
            total_openai_usage[k] += u_arch.get(k, 0)

    # Pass 2: Structural Extraction
    struct_shots = [sh for sh in shots if sh["page"] in struct_pages or sh["page_type"] == "structural_drawing"]
    if struct_shots:
        header = (
            f"TARGET: STRUCTURAL ENGINEERING DRAWING EXTRACTION (Pages: {struct_pages})\n"
            f"Extract structural parameters: {json.dumps(STRUCTURAL_KEYS)}\n"
            f"Extract observations for Structural items: {json.dumps(STRUCTURAL_CHECKLIST)}"
        )
        parsed_struct, u_struct = run_vision_extraction_batch(
            header,
            struct_doc_text,
            struct_shots,
            model_name=active_model,
        )
        structural_values.extend(parsed_struct.get("structural_values", []))
        observations.extend([o for o in parsed_struct.get("observations", []) if o["check_id"] in STRUCTURAL_CHECKLIST])
        flags.extend(parsed_struct.get("flags", []))
        if parsed_struct.get("revisions"):
            revisions.extend(parsed_struct["revisions"])
        if parsed_struct.get("revisions_table"):
            revisions_table.extend(parsed_struct["revisions_table"])
        for k in total_openai_usage:
            total_openai_usage[k] += u_struct.get(k, 0)

    # Pass 3: Certificate Extraction
    cert_shots = [sh for sh in shots if sh["page"] in cert_pages or sh["page_type"] == "stability_certificate"]
    if cert_shots:
        header = (
            f"TARGET: STRUCTURAL STABILITY CERTIFICATE VALIDATION (Pages: {cert_pages})\n"
            f"Extract engineer name, PEC registration number, signature, seal, date, plot reference, and scope.\n"
            f"Extract observations for Certificate items: {json.dumps(CERTIFICATE_CHECKLIST)}"
        )
        parsed_cert, u_cert = run_vision_extraction_batch(
            header,
            cert_doc_text,
            cert_shots,
            model_name=active_model,
        )
        if parsed_cert.get("certificate_details"):
            certificate_details = parsed_cert["certificate_details"]
        observations.extend([o for o in parsed_cert.get("observations", []) if o["check_id"] in CERTIFICATE_CHECKLIST])
        flags.extend(parsed_cert.get("flags", []))
        for k in total_openai_usage:
            total_openai_usage[k] += u_cert.get(k, 0)

    parsed_final = {
        "values": values,
        "structural_values": structural_values,
        "certificate_details": certificate_details,
        "observations": observations,
        "flags": flags,
        "revision": revisions[0] if revisions else None,
        "revisions_table": revisions_table,
    }

    return {"extraction": parsed_final, "openai_usage": total_openai_usage}


def n_judge(s):
    """Jev checklist grading over observations, packed text, and extracted values."""
    ex = s["extraction"]
    dt = s.get("doc_type", {})

    has_arch = dt.get("has_architectural", False)
    has_struct = dt.get("has_structural", False)
    has_cert = dt.get("has_stability_certificate", False)

    active_checklist = {}
    if has_arch or (not has_struct and not has_cert):
        active_checklist.update(ARCHITECTURAL_CHECKLIST)
    if has_struct:
        active_checklist.update(STRUCTURAL_CHECKLIST)
    if has_cert:
        active_checklist.update(CERTIFICATE_CHECKLIST)

    state = {
        "document_composition": {
            "has_architectural_drawing": has_arch,
            "has_structural_drawing": has_struct,
            "has_stability_certificate": has_cert,
            "architectural_pages": dt.get("architectural_pages", []),
            "structural_pages": dt.get("structural_pages", []),
            "certificate_pages": dt.get("certificate_pages", []),
            "page_types": {f"page_{k}": v["choice"] for k, v in dt.get("page_types", {}).items()},
        },
        "observations": {
            o["check_id"]: {"seen": o["seen"], "evidence": o["evidence"], "page": o["page"]}
            for o in ex.get("observations", [])
        },
        "architectural_values": {v["key"]: v["value"] for v in ex.get("values", []) if v.get("value") is not None},
        "structural_values": {
            v["key"]: v["value"] for v in ex.get("structural_values", []) if v.get("value") is not None
        },
        "certificate_details": ex.get("certificate_details") or {},
        "text": pack(s, 15000),
    }

    qs = {
        cid: Choice(
            criteria=STATUS,
            instructions=f"Does the submission clearly satisfy this requirement: {need}? "
            f"Judge from observations['{cid}'], document_composition, architectural_values, structural_values, certificate_details and text. "
            "Missing/wrong/illegible = CORRECTION_REQUIRED; unconfirmable = PENDING.",
        )
        for cid, need in active_checklist.items()
    }

    answers, usage = jev_call(state, qs)
    return {"checks": answers, "jev_judge_usage": usage, "active_checklist": active_checklist}


def n_report(s):
    """Deterministic auditors + combined confidence + overall verdict and cost metrics."""
    ex = s.get("extraction") or {
        "values": [],
        "structural_values": [],
        "certificate_details": None,
        "observations": [],
        "flags": [],
        "revision": None,
        "revisions_table": [],
    }
    dt = s.get("doc_type") or {}
    pages_list = s.get("pages", [])
    has_arch = dt.get("has_architectural", False)
    has_struct = dt.get("has_structural", False)
    has_cert = dt.get("has_stability_certificate", False)

    review = list(s.get("flags", [])) + ex.get("flags", [])
    if not has_arch and not s.get("unreadable"):
        review.append(
            "No architectural drawing sheet identified: architectural design values not extracted, bylaw checks skipped"
        )
    if not has_struct and not s.get("unreadable"):
        review.append("No structural engineering drawing sheet identified in submission")
    if not has_cert and not s.get("unreadable"):
        review.append("No structural stability certificate found in submission")

    # 1. Deterministic Sheet Revision Resolution & Consistency Audit
    rev_raw_list = []
    if ex.get("revision"):
        rev_raw_list.append(ex["revision"])
    rev_raw_list.extend(ex.get("revisions", []))

    rev_audit = resolve_authoritative_revisions(ex.get("revisions_table", []), rev_raw_list, pages_list)
    if rev_audit.get("conflict_flags"):
        review.extend(rev_audit["conflict_flags"])

    # 2. Sheet-Numbering & Discipline Consistency Audit
    sheet_audit = audit_sheet_numbering(pages_list)
    if sheet_audit.get("sequence_issues"):
        review.extend(sheet_audit["sequence_issues"])
    if sheet_audit.get("duplicate_sheets"):
        review.extend(sheet_audit["duplicate_sheets"])

    # 3. Cross-Page Conflict Resolution & Spatial Numeric Verification (Architectural)
    raw_arch = [v for v in ex.get("values", []) if v.get("value") is not None]
    revision_scoped_arch, revision_filter_flags = filter_values_to_master_revision(raw_arch, rev_audit)
    if revision_filter_flags:
        review.extend(revision_filter_flags)
    values, arch_conflict_flags = resolve_cross_page_conflicts(revision_scoped_arch if has_arch else [], pages_list)
    if arch_conflict_flags:
        review.extend(arch_conflict_flags)

    # 4. Cross-Page Conflict Resolution & Structural Engineering Analysis
    raw_struct = [sv for sv in ex.get("structural_values", []) if sv.get("value") is not None]
    struct_values, struct_conflict_flags = resolve_cross_page_conflicts(raw_struct if has_struct else [], pages_list)
    if struct_conflict_flags:
        review.extend(struct_conflict_flags)

    concrete_psi = (struct_values.get("concrete_grade_psi") or {}).get("value")
    steel_psi = (struct_values.get("steel_grade_psi") or {}).get("value")
    slab_thk = (struct_values.get("slab_thickness_in") or {}).get("value")
    fnd_depth = (struct_values.get("foundation_depth_ft") or {}).get("value")

    if concrete_psi is not None and concrete_psi < 2500:
        review.append(
            f"STRUCTURAL DEFICIENCY: Concrete compressive strength fc'={concrete_psi} psi is below standard residential minimum (3000 psi)"
        )
    if steel_psi is not None and steel_psi < 40000:
        review.append(
            f"STRUCTURAL DEFICIENCY: Steel yield strength fy={steel_psi} psi is below standard minimum (40,000 / 60,000 psi)"
        )
    if slab_thk is not None and slab_thk < 4.0:
        review.append(f"STRUCTURAL DEFICIENCY: Slab thickness={slab_thk} in is below minimum allowable 4.0-5.0 inches")

    structural_audit = {
        "sheets_present": has_struct,
        "structural_pages": dt.get("structural_pages", []),
        "parameters": struct_values,
        "concrete_grade_psi": concrete_psi,
        "steel_grade_psi": steel_psi,
        "slab_thickness_in": slab_thk,
        "foundation_depth_ft": fnd_depth,
        "column_schedule": bool((struct_values.get("column_schedule_present") or {}).get("value")),
        "beam_schedule": bool((struct_values.get("beam_schedule_present") or {}).get("value")),
        "slab_rebar_detail": bool((struct_values.get("slab_rebar_detail_present") or {}).get("value")),
        "structural_notes": bool((struct_values.get("structural_notes_present") or {}).get("value")),
        "seismic_zone_stated": bool((struct_values.get("seismic_zone_stated") or {}).get("value")),
    }

    # 5. Stability Certificate Validation & PEC Registration Verification
    cert_raw = ex.get("certificate_details") or {}
    pec_no = cert_raw.get("pec_registration_no") or ""
    has_pec = bool(
        re.search(r"(CIVIL|STRUCT|PEC|PE|RE)[\s\/\-\:]*\d+", pec_no, re.IGNORECASE) or (pec_no and len(pec_no) >= 4)
    )

    certificate_audit = {
        "certificate_present": has_cert,
        "certificate_pages": dt.get("certificate_pages", []),
        "engineer_name": cert_raw.get("engineer_name"),
        "pec_registration_no": pec_no,
        "pec_valid_format": has_pec,
        "cert_number": cert_raw.get("cert_number"),
        "cert_date": cert_raw.get("cert_date"),
        "plot_reference": cert_raw.get("plot_reference"),
        "owner_name": cert_raw.get("owner_name"),
        "has_signature": cert_raw.get("has_signature"),
        "has_stamp": cert_raw.get("has_stamp"),
        "scope": cert_raw.get("scope"),
        "soil_report_referenced": cert_raw.get("soil_report_referenced"),
        "is_verified": bool(has_cert and has_pec and cert_raw.get("has_signature")),
    }

    if has_cert and not has_pec:
        review.append("STABILITY CERTIFICATE FLAG: PEC registration number missing or invalid format on certificate")
    if has_cert and cert_raw.get("has_signature") is False:
        review.append("STABILITY CERTIFICATE FLAG: Structural engineer signature missing on certificate")

    # 6. Bylaw compliance check
    plot_marla = (values.get("plot_area_marla") or {}).get("value")
    auth = s.get("authority", "DHA_Lahore")
    bylaw_rules, pkey, pdisp = get_bylaws_for_plot(plot_marla, authority=auth)
    bl = bylaw_check(values, custom_bylaws=bylaw_rules, authority=auth, has_architectural=has_arch)

    # 7. Combined Confidence Model & Full Source-Level Evidence Chain
    obs = {o["check_id"]: o for o in ex.get("observations", [])}
    active_chk = s.get("active_checklist") or CHECKLIST
    checks = {}
    evidence_chain = {}

    active_model_id = s.get("active_model") or settings.openai_model
    try:
        from src.memory.models_store import get_model

        db_model = get_model(active_model_id)
    except Exception:
        db_model = None

    if db_model:
        in_rate = float(db_model["input_price_per_1m"])
        out_rate = float(db_model["output_price_per_1m"])
        model_name = db_model["model_name"]
        model_provider = db_model["provider"]
        model_display_name = f"{model_provider} - {model_name} ({active_model_id})"
    else:
        in_rate = settings.input_price_per_1m
        out_rate = settings.output_price_per_1m
        model_name = active_model_id
        model_provider = "OpenAI"
        model_display_name = active_model_id

    for cid, need in active_chk.items():
        a = (s.get("checks") or {}).get(cid, {})
        pr, st = a.get("probabilities") or {}, a.get("choice", "PENDING")
        o = obs.get(
            cid,
            {
                "seen": "unclear",
                "evidence": "",
                "page": None,
                "bbox": None,
                "crop_label": None,
                "context_snippet": None,
            },
        )

        ev_text = o.get("evidence", "")
        ev_pg = o.get("page") or 1
        obs_ver = (
            verify_spatial_numeric_evidence(cid, None, ev_text, ev_pg, pages_list)
            if ev_text
            else {
                "tier": "NO_EVIDENCE",
                "status": "no_evidence",
                "multiplier": 0.5,
                "context_span": "",
                "verified": False,
            }
        )

        if st == "PASS" and (o.get("seen") != "yes" or pr.get("PASS", 0) < 0.75):
            st = "PENDING"
        # The supplied review specification permits CORRECTION_REQUIRED only
        # for a clearly missing/wrong/illegible item. An unclear observation
        # is a request for clarification, not a rejection.
        if st == "CORRECTION_REQUIRED" and o.get("seen") != "no":
            st = "PENDING"
        if st == "NOT_APPLICABLE" and pr.get("NOT_APPLICABLE", 0) < 0.9:
            st = "PENDING"

        note = (
            ""
            if st in ("PASS", "NOT_APPLICABLE")
            else (
                f"{need}. Seen: {ev_text or 'nothing legible found'} (page {ev_pg}). Add/clarify on the submitted sheet."
            )
        )

        jev_conf = a.get("confidence")
        if jev_conf is None:
            jev_conf = pr.get(st, 0.5) if pr else 0.5

        comb_conf = compute_combined_confidence(
            decision_conf=jev_conf,
            probabilities=pr,
            source_multiplier=obs_ver["multiplier"],
            obs_seen=o.get("seen", "unclear"),
            has_evidence=bool(ev_text.strip()),
        )

        checks[cid] = {
            "status": st,
            "confidence": comb_conf,
            "decision_confidence": float(jev_conf or 0.0),
            "evidence_tier": obs_ver["tier"],
            "note": note,
            "evidence": ev_text,
            "page": ev_pg,
            "bbox": o.get("bbox"),
            "context_span": obs_ver["context_span"] or ev_text,
        }

        rule_str = str(bylaw_rules.get(cid) if cid in bylaw_rules else need)
        evidence_chain[cid] = {
            "check_id": cid,
            "requirement": need,
            "final_status": st,
            "combined_confidence": comb_conf,
            "decision_confidence": float(jev_conf or 0.0),
            "evidence_tier": obs_ver["tier"],
            "evidence_text": ev_text or "No explicit text evidence found",
            "context_span": obs_ver["context_span"] or ev_text or "-",
            "page_number": ev_pg,
            "bounding_box": o.get("bbox"),
            "crop_label": o.get("crop_label") or f"Page {ev_pg} Overview",
            "extraction_source": f"Multimodal Vision ({model_display_name}) + Spatial Text Verification",
            "decision_engine": "TypeSafe Jev (System One / Jev Model)",
            "rule_applied": rule_str,
            "decision_rationale": note if note else "Requirement confirmed present and compliant in drawing.",
        }

    # 8. Document Completeness Model
    completeness_audit = evaluate_document_completeness(dt, checks, pages_list, sheet_audit)
    if completeness_audit.get("completeness_flags"):
        review.extend(completeness_audit["completeness_flags"])

    sts = {c["status"] for c in checks.values()}
    has_conflicts = bool(
        arch_conflict_flags or struct_conflict_flags or any("CONFLICT" in str(bl_val) for bl_val in bl.values())
    )

    overall = (
        "CORRECTION_REQUIRED"
        if s.get("unreadable")
        or "CORRECTION_REQUIRED" in sts
        or any(x.startswith("VIOLATION") for x in bl.values())
        or has_conflicts
        or not completeness_audit.get("is_complete")
        else "PENDING_HUMAN_REVIEW"
        if "PENDING" in sts or review
        else "READY_FOR_HUMAN_SIGNOFF"
    )
    # READY_FOR_HUMAN_SIGNOFF still requires an engineer; it is not auto-approval.

    # Billing calculation
    jev_gate = s.get("jev_gate_usage", {})
    jev_judge = s.get("jev_judge_usage", {})
    jev_in = jev_gate.get("input_tokens", 0) + jev_judge.get("input_tokens", 0)
    jev_out = jev_gate.get("output_tokens", 0) + jev_judge.get("output_tokens", 0)
    jev_cost = round(jev_in * (0.042 / 1_000_000), 6)

    op_usage = s.get("openai_usage", {})
    op_in = op_usage.get("input_tokens", 0)
    op_out = op_usage.get("output_tokens", 0)

    op_in_token_price = in_rate / 1_000_000.0
    op_out_token_price = out_rate / 1_000_000.0
    op_rate_str = f"${in_rate:.2f}/1M in &bull; ${out_rate:.2f}/1M out"
    op_cost = round((op_in * op_in_token_price) + (op_out * op_out_token_price), 6)

    total_cost = round(op_cost + jev_cost, 6)
    total_tokens = op_in + op_out + jev_in + jev_out

    metrics = {
        "openai": {
            "model": model_display_name,
            "model_id": active_model_id,
            "provider": model_provider,
            "rate": op_rate_str,
            "input_tokens": op_in,
            "output_tokens": op_out,
            "total_tokens": op_in + op_out,
            "cost_usd": f"${op_cost:.5f}",
            "cost_float": op_cost,
        },
        "jev": {
            "model": "jev-latest (TypeSafe)",
            "rate": "$0.042 / 1M input tokens (output free)",
            "input_tokens": jev_in,
            "output_tokens": jev_out,
            "total_tokens": jev_in + jev_out,
            "cost_usd": f"${jev_cost:.6f}",
            "cost_float": jev_cost,
        },
        "total": {"total_tokens": total_tokens, "total_cost_usd": f"${total_cost:.5f}", "total_cost_float": total_cost},
        "input_tokens": op_in + jev_in,
        "output_tokens": op_out + jev_out,
        "total_tokens": total_tokens,
        "estimated_cost_usd": f"${total_cost:.5f}",
    }

    # 9. Page Coverage Audit
    page_cov = s.get("page_coverage", {})
    total_pages_count = len(pages_list)
    covered_pages_count = len(page_cov)
    coverage_summary = {
        "total_pages": total_pages_count,
        "processed_pages": sorted(page_cov.keys()),
        "coverage_complete": bool(covered_pages_count == total_pages_count and total_pages_count > 0),
        "page_details": page_cov,
    }

    return {
        "verdict": {
            "overall": overall,
            "doc_type": s.get("doc_type"),
            "page_breakdown": dt.get("page_types", {}),
            "page_coverage": coverage_summary,
            "sheet_numbering_audit": sheet_audit,
            "completeness_audit": completeness_audit,
            "duplicates_audit": s.get("duplicates_audit") or {"has_duplicates": False, "duplicates": []},
            "cross_page_conflicts": arch_conflict_flags + struct_conflict_flags,
            "revision": rev_audit.get("master_revision", "Rev 0"),
            "revisions_audit": rev_audit,
            "evidence_chain": evidence_chain,
            "unreadable": bool(s.get("unreadable")),
            "token_metrics": metrics,
            "checks": checks,
            "values": values,
            "structural_analysis": structural_audit,
            "certificate_audit": certificate_audit,
            "bylaws": bl if has_arch else {"status": "ARCHITECTURAL_DRAWING_REQUIRED"},
            "bylaw_profile": {
                "status": "ACTIVE" if has_arch else "ARCHITECTURAL_DRAWING_REQUIRED",
                "notice": "Architectural rules applied"
                if has_arch
                else "Submission lacks Architectural Site/Floor Plan sheets required for setback/FAR/height compliance.",
                "plot_category": pkey if has_arch else "N/A (Structural Submission)",
                "display_name": pdisp if has_arch else "Structural Submission Only",
                "rules": bylaw_rules if has_arch else {},
            },
            "review_flags": review,
            "security_audit": s.get("security_audit", []),
            "cad_geometry": s.get("cad_geometry", {}),
            "layers": s.get("layers"),
            "embedded_files": s.get("embedded"),
            "metadata": s.get("meta"),
            "active_model": active_model_id,
            "model_provider": model_provider,
        }
    }
