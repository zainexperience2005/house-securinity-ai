"""ReportLab vector PDF audit certificate from a scrutiny verdict dict."""

import io
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def create_scrutiny_pdf_report(verdict_data: dict, filename: str = "Drawing") -> io.BytesIO:
    """Build a multi-section letter-size PDF (verdict, checklists, bylaws, flags).

    Returns an in-memory buffer positioned at the start for StreamingResponse.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)

    styles = getSampleStyleSheet()

    # Custom Palette
    PRIMARY = colors.HexColor("#1e293b")
    SECONDARY = colors.HexColor("#3b82f6")
    SUCCESS = colors.HexColor("#10b981")
    DANGER = colors.HexColor("#ef4444")
    WARNING = colors.HexColor("#f59e0b")
    MUTED = colors.HexColor("#64748b")
    LIGHT_BG = colors.HexColor("#f8fafc")
    BORDER_COLOR = colors.HexColor("#e2e8f0")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=PRIMARY,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=14, textColor=MUTED
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=PRIMARY,
        spaceBefore=12,
        spaceAfter=6,
    )
    cell_style = ParagraphStyle(
        "TableCell", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=PRIMARY
    )
    cell_bold = ParagraphStyle("TableCellBold", parent=cell_style, fontName="Helvetica-Bold")
    cell_note = ParagraphStyle(
        "TableCellNote",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )
    action_style = ParagraphStyle(
        "ActionNote", parent=cell_note, fontSize=8.5, leading=12, textColor=colors.HexColor("#7f1d1d")
    )

    def draw_footer(canvas, _doc):
        canvas.saveState()
        canvas.setStrokeColor(BORDER_COLOR)
        canvas.line(36, 26, letter[0] - 36, 26)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            36, 16, "House Scrutiny AI • Engineer review copy • Verify pending items against stamped drawings"
        )
        canvas.drawRightString(letter[0] - 36, 16, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    story = []

    # 1. Header
    story.append(Paragraph("HOUSE SCRUTINY REPORT", title_style))
    story.append(
        Paragraph(
            f"File: <b>{filename}</b> &nbsp;|&nbsp; Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=SECONDARY, spaceBefore=0, spaceAfter=12))

    # 2. Key Summary Card
    overall = verdict_data.get("overall", "UNKNOWN")
    raw_doc_type = verdict_data.get("doc_type")
    if isinstance(raw_doc_type, dict):
        doc_type = (
            str(raw_doc_type.get("choice") or raw_doc_type.get("primary_type") or "General Document")
            .replace("_", " ")
            .title()
        )
        conf = float(raw_doc_type.get("confidence") or 0.0)
    elif isinstance(raw_doc_type, str):
        doc_type = raw_doc_type.replace("_", " ").title()
        conf = 0.90
    else:
        doc_type = "General Document"
        conf = 0.0

    revision = verdict_data.get("revision") or "None Stated"
    token_metrics = verdict_data.get("token_metrics") or {}

    op_info = token_metrics.get("openai") or {}
    jev_info = token_metrics.get("jev") or {}
    tot_info = token_metrics.get("total") or {}

    op_cost = op_info.get("cost_usd", "N/A")
    jev_cost = jev_info.get("cost_usd", "N/A")
    total_cost = tot_info.get("total_cost_usd", token_metrics.get("estimated_cost_usd", "N/A"))
    total_toks = tot_info.get("total_tokens", token_metrics.get("total_tokens", "N/A"))
    processing_seconds = verdict_data.get("processing_seconds")
    process_time = f"{float(processing_seconds):.1f} seconds" if processing_seconds is not None else "Not recorded"

    verdict_color = (
        DANGER if overall == "CORRECTION_REQUIRED" else (SUCCESS if overall == "READY_FOR_HUMAN_SIGNOFF" else WARNING)
    )

    summary_data = [
        [
            Paragraph("<b>Overall Verdict:</b>", cell_bold),
            Paragraph(f"<font color='{verdict_color.hexval()}'><b>{overall}</b></font>", cell_bold),
            Paragraph("<b>Document Type:</b>", cell_bold),
            Paragraph(f"{doc_type} ({int(conf * 100)}% conf)", cell_style),
        ],
        [
            Paragraph("<b>Revision:</b>", cell_bold),
            Paragraph(str(revision), cell_style),
            Paragraph("<b>Total Cost & Tokens:</b>", cell_bold),
            Paragraph(
                f"<b>{total_cost}</b> ({total_toks:,} tokens)"
                if isinstance(total_toks, int)
                else f"<b>{total_cost}</b> ({total_toks} tok)",
                cell_style,
            ),
        ],
    ]
    summary_table = Table(summary_data, colWidths=[110, 160, 120, 150])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # Engineer-first performance and cost snapshot: surfaced before detailed tables.
    performance_data = [
        [
            Paragraph("<b>Processing Time</b>", cell_bold),
            Paragraph("<b>OpenAI Vision</b>", cell_bold),
            Paragraph("<b>TypeSafe Jev</b>", cell_bold),
            Paragraph("<b>Total Estimated Cost</b>", cell_bold),
        ],
        [
            Paragraph(process_time, cell_style),
            Paragraph(
                f"{xml_escape(str(op_info.get('model', 'OpenAI Vision')))}<br/><b>{xml_escape(str(op_cost))}</b> • {op_info.get('total_tokens', 0):,} tokens",
                cell_note,
            ),
            Paragraph(
                f"System One<br/><b>{xml_escape(str(jev_cost))}</b> • {jev_info.get('total_tokens', 0):,} tokens",
                cell_note,
            ),
            Paragraph(
                f"<b>{xml_escape(str(total_cost))}</b><br/>{total_toks:,} tokens"
                if isinstance(total_toks, int)
                else f"<b>{xml_escape(str(total_cost))}</b><br/>{xml_escape(str(total_toks))} tokens",
                cell_style,
            ),
        ],
    ]
    performance_table = Table(performance_data, colWidths=[130, 150, 130, 130])
    performance_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0f2fe")),
                ("BACKGROUND", (0, 1), (-1, 1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(performance_table)
    story.append(Spacer(1, 10))

    # Cost Breakdown Sub-Table
    cost_breakdown_data = [
        [
            Paragraph("<b>Engine / Provider</b>", cell_bold),
            Paragraph("<b>Billing Rate / Pricing Rule</b>", cell_bold),
            Paragraph("<b>Tokens (In / Out)</b>", cell_bold),
            Paragraph("<b>Cost (USD)</b>", cell_bold),
        ],
        [
            Paragraph("<b>OpenAI Vision</b> (" + str(op_info.get("model", "gpt-6-astra")) + ")", cell_style),
            Paragraph(str(op_info.get("rate", "$10.00/1M in &bull; $50.00/1M out")), cell_note),
            Paragraph(f"{op_info.get('input_tokens', 0):,} in / {op_info.get('output_tokens', 0):,} out", cell_style),
            Paragraph(f"<b>{op_cost}</b>", cell_style),
        ],
        [
            Paragraph("<b>TypeSafe Jev</b> (System One)", cell_style),
            Paragraph("$0.042/1M in &bull; Output Free ($0.00)", cell_note),
            Paragraph(f"{jev_info.get('input_tokens', 0):,} in / {jev_info.get('output_tokens', 0):,} out", cell_style),
            Paragraph(f"<b>{jev_cost}</b>", cell_style),
        ],
        [
            Paragraph("<b>Total Combined Audit Cost</b>", cell_bold),
            Paragraph("Deterministic + Neural Scrutiny", cell_note),
            Paragraph(
                f"<b>{total_toks:,} total</b>" if isinstance(total_toks, int) else f"<b>{total_toks}</b>", cell_bold
            ),
            Paragraph(f"<font color='{PRIMARY.hexval()}'><b>{total_cost}</b></font>", cell_bold),
        ],
    ]
    cost_table = Table(cost_breakdown_data, colWidths=[160, 160, 130, 90])
    cost_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
                ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(cost_table)
    story.append(Spacer(1, 10))

    # Put engineering actions before the detailed evidence tables so reviewers
    # can act without reading the full technical appendix first.
    action_rows = []
    checks_for_actions = verdict_data.get("checks") or {}
    for check_id, check_data in checks_for_actions.items():
        if not isinstance(check_data, dict) or check_data.get("status") != "CORRECTION_REQUIRED":
            continue
        action_rows.append(
            [
                Paragraph("<font color='#dc2626'><b>Correction</b></font>", cell_bold),
                Paragraph(xml_escape(check_id.replace("_", " ").title()), cell_bold),
                Paragraph(
                    xml_escape(str(check_data.get("note") or "Provide legible compliant evidence.")), action_style
                ),
                Paragraph(f"Page {check_data.get('page') or '-'}", cell_note),
            ]
        )

    for component in (verdict_data.get("completeness_audit") or {}).get("missing_components", []):
        if not isinstance(component, dict):
            continue
        action_rows.append(
            [
                Paragraph("<font color='#dc2626'><b>Missing</b></font>", cell_bold),
                Paragraph(xml_escape(str(component.get("name", "Required document"))), cell_bold),
                Paragraph(xml_escape(str(component.get("reason") or "Submit this statutory document.")), action_style),
                Paragraph("Package", cell_note),
            ]
        )

    for conflict in verdict_data.get("cross_page_conflicts") or []:
        conflict_text = conflict.get("summary") if isinstance(conflict, dict) else str(conflict)
        action_rows.append(
            [
                Paragraph("<font color='#d97706'><b>Review</b></font>", cell_bold),
                Paragraph("Cross-sheet conflict", cell_bold),
                Paragraph(xml_escape(conflict_text or "Reconcile conflicting sheet values."), action_style),
                Paragraph("Multiple pages", cell_note),
            ]
        )

    if action_rows:
        story.append(Paragraph("Engineer Action Register", section_heading))
        action_table = Table(
            [
                [
                    Paragraph("<b>Priority</b>", cell_bold),
                    Paragraph("<b>Item</b>", cell_bold),
                    Paragraph("<b>Required Action</b>", cell_bold),
                    Paragraph("<b>Source</b>", cell_bold),
                ]
            ]
            + action_rows,
            colWidths=[75, 130, 260, 75],
            repeatRows=1,
        )
        action_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fee2e2")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fff7ed")),
                    ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(action_table)
        story.append(Spacer(1, 12))

    # Page Breakdown Sub-Table
    page_breakdown = verdict_data.get("page_breakdown") or (verdict_data.get("doc_type") or {}).get("page_types") or {}
    if page_breakdown and isinstance(page_breakdown, dict):
        story.append(Paragraph("Submission Composition & Per-Page Gate Classification", section_heading))
        page_rows = [
            [
                Paragraph("<b>Page / Sheet</b>", cell_bold),
                Paragraph("<b>Classified Document Type</b>", cell_bold),
                Paragraph("<b>Confidence</b>", cell_bold),
                Paragraph("<b>Classification Notes</b>", cell_bold),
            ]
        ]
        for pn, pinfo in sorted(page_breakdown.items(), key=lambda x: int(x[0])):
            p_choice = pinfo.get("choice", "other").replace("_", " ").title()
            p_conf = pinfo.get("confidence", 0.0)
            p_conf_str = f"{int(p_conf * 100)}%" if p_conf is not None else "-"
            note_str = (
                "Architectural drawing sheet (extracts design parameters)"
                if "Architectural" in p_choice
                else (
                    "Structural engineering sheet"
                    if "Structural" in p_choice
                    else (
                        "Structural stability certificate"
                        if "Certificate" in p_choice
                        else "General submission document"
                    )
                )
            )
            page_rows.append(
                [
                    Paragraph(f"<b>Page {pn}</b>", cell_style),
                    Paragraph(f"<b>{p_choice}</b>", cell_style),
                    Paragraph(p_conf_str, cell_style),
                    Paragraph(note_str, cell_note),
                ]
            )
        page_table = Table(page_rows, colWidths=[80, 160, 80, 220])
        page_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(page_table)
        story.append(Spacer(1, 12))

    # 2.7 Document Completeness & Sheet Numbering Summary
    comp_audit = verdict_data.get("completeness_audit") or {}
    sheet_audit = verdict_data.get("sheet_numbering_audit") or {}
    if comp_audit or sheet_audit:
        story.append(Paragraph("Submission Package Completeness & Sheet Numbering Integrity", section_heading))
        comp_score = comp_audit.get("completeness_score_pct", 0)
        comp_st = comp_audit.get("completeness_status", "INCOMPLETE")
        is_seq = sheet_audit.get("is_sequence_valid", True)

        comp_summary_rows = [
            [
                Paragraph("<b>Metric / Check</b>", cell_bold),
                Paragraph("<b>Result / Score</b>", cell_bold),
                Paragraph("<b>Audit Details</b>", cell_bold),
            ],
            [
                Paragraph("<b>Package Completeness</b>", cell_style),
                Paragraph(f"<b>{comp_score}%</b> ({comp_st})", cell_style),
                Paragraph(
                    f"Submitted {comp_audit.get('submitted_count', 0)} of {comp_audit.get('expected_count', 6)} statutory components",
                    cell_note,
                ),
            ],
            [
                Paragraph("<b>Sheet Numbering Sequence</b>", cell_style),
                Paragraph(
                    "<font color='green'>Valid Sequence</font>"
                    if is_seq
                    else "<font color='red'>Gaps / Discrepancies</font>",
                    cell_style,
                ),
                Paragraph(
                    f"Disciplines: {', '.join(sheet_audit.get('disciplines_present', ['General']))} | Indexed: {sheet_audit.get('total_sheets_indexed', 0)} sheets",
                    cell_note,
                ),
            ],
        ]

        if comp_audit.get("missing_components"):
            miss_names = ", ".join([m["name"] for m in comp_audit["missing_components"]])
            comp_summary_rows.append(
                [
                    Paragraph("<b>Missing Expected Documents</b>", cell_style),
                    Paragraph("<font color='red'>Action Required</font>", cell_style),
                    Paragraph(f"Missing statutory documents: {miss_names}", cell_note),
                ]
            )

        comp_table = Table(comp_summary_rows, colWidths=[150, 130, 260])
        comp_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(comp_table)
        story.append(Spacer(1, 12))

    # 3. Checklist Audit Table
    story.append(Paragraph("1. Map Scrutiny Checklist Audit", section_heading))
    checks = verdict_data.get("checks", {})

    check_table_data = [
        [
            Paragraph("<b>Checklist Item</b>", cell_bold),
            Paragraph("<b>Status</b>", cell_bold),
            Paragraph("<b>Conf</b>", cell_bold),
            Paragraph("<b>Findings & Evidence Notes</b>", cell_bold),
        ]
    ]

    for cid, cdata in checks.items():
        st = cdata.get("status", "PENDING")
        c_conf = cdata.get("confidence")
        conf_str = f"{int(c_conf * 100)}%" if c_conf is not None else "-"
        note = cdata.get("note") or "Requirement confirmed compliant."
        title = cid.replace("_", " ").title()

        st_color = (
            SUCCESS
            if st == "PASS"
            else (DANGER if st == "CORRECTION_REQUIRED" else (MUTED if st == "NOT_APPLICABLE" else WARNING))
        )
        status_p = Paragraph(f"<font color='{st_color.hexval()}'><b>{st}</b></font>", cell_bold)

        check_table_data.append(
            [
                Paragraph(f"<b>{title}</b>", cell_style),
                status_p,
                Paragraph(conf_str, cell_style),
                Paragraph(note, cell_note),
            ]
        )

    check_table = Table(check_table_data, colWidths=[110, 105, 45, 280])
    check_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(check_table)
    story.append(Spacer(1, 14))

    # 4. Review Flags & Digital Scrutiny
    flags = verdict_data.get("review_flags", [])
    if flags:
        story.append(Paragraph("2. Deep Scrutiny & Review Flags", section_heading))
        flag_rows = []
        for fl in flags:
            flag_rows.append([Paragraph("&bull;", cell_bold), Paragraph(str(fl), cell_style)])
        flag_table = Table(flag_rows, colWidths=[20, 520])
        flag_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        story.append(flag_table)
        story.append(Spacer(1, 10))

    # 5. Extracted Design Values & Bylaws
    values = verdict_data.get("values", {})
    bylaws = verdict_data.get("bylaws", {})
    if bylaws.get("status") == "ARCHITECTURAL_DRAWING_REQUIRED" or (
        not values and not any(k != "status" for k in bylaws)
    ):
        story.append(Paragraph("3. Extracted Architectural Values & Bylaw Verification", section_heading))
        story.append(
            Paragraph(
                "<i>Architectural bylaw checks skipped: No architectural drawing sheets were identified in this submission package (structural/other drawings detected).</i>",
                cell_note,
            )
        )
        story.append(Spacer(1, 10))
    elif values or any(v != "NOT_CONFIGURED" and k != "status" for k, v in bylaws.items()):
        story.append(Paragraph("3. Extracted Architectural Values & Bylaw Verification", section_heading))
        val_rows = [
            [
                Paragraph("<b>Parameter</b>", cell_bold),
                Paragraph("<b>Extracted Value</b>", cell_bold),
                Paragraph("<b>Evidence</b>", cell_bold),
                Paragraph("<b>Bylaw Check</b>", cell_bold),
            ]
        ]
        all_keys = sorted({k for k in list(values.keys()) + list(bylaws.keys()) if k != "status"})
        for k in all_keys:
            v_info = values.get(k, {})
            val_num = v_info.get("value")
            ev = v_info.get("evidence", "-")
            bl = bylaws.get(k, "NOT_CONFIGURED")
            is_conf = bool(v_info.get("is_conflict")) or ("CONFLICT" in str(bl))

            val_display = str(val_num) if val_num is not None else "-"
            if is_conf:
                val_display = f"CONFLICT: {val_display}"
                ev = v_info.get("context_span") or ev
                bl_display = "<font color='#ef4444'><b>CROSS-PAGE CONFLICT</b></font>"
            else:
                bl_color = SUCCESS if bl == "OK" else (DANGER if "VIOLATION" in bl else MUTED)
                bl_display = f"<font color='{bl_color.hexval()}'>{bl}</font>"

            val_rows.append(
                [
                    Paragraph(k.replace("_", " ").title(), cell_style),
                    Paragraph(val_display, cell_style),
                    Paragraph(ev, cell_note),
                    Paragraph(bl_display, cell_style),
                ]
            )
        val_table = Table(val_rows, colWidths=[130, 80, 200, 130])
        val_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(val_table)
        story.append(Spacer(1, 10))

    # 6. Structural Engineering & Code Compliance Audit
    struct_audit = verdict_data.get("structural_analysis", {})
    if struct_audit.get("sheets_present") or struct_audit.get("parameters"):
        story.append(Paragraph("4. Structural Engineering & Code Compliance Audit", section_heading))

        # Check if multiple concrete grades were noted in review flags
        c_psi_val = struct_audit.get("concrete_grade_psi")
        multi_flags = [fl for fl in verdict_data.get("review_flags", []) if "MULTIPLE_CONCRETE" in fl]
        if c_psi_val:
            c_disp = f"{c_psi_val:,} psi"
            c_status_note = "Min 3000 psi (Pakistan Building Code / ACI 318)"
        elif multi_flags:
            c_disp = "3,000 / 4,000 psi"
            c_status_note = "Member-specific: 4000 psi columns, 3000 psi beams/slabs"
        else:
            c_disp = "Not Specified"
            c_status_note = "Min 3000 psi (Pakistan Building Code)"

        s_rows = [
            [
                Paragraph("<b>Structural Parameter / Specification</b>", cell_bold),
                Paragraph("<b>Extracted Value / Status</b>", cell_bold),
                Paragraph("<b>Standard Code Requirement</b>", cell_bold),
            ],
            [
                Paragraph("Concrete Compressive Strength (fc')", cell_style),
                Paragraph(c_disp, cell_style),
                Paragraph(c_status_note, cell_note),
            ],
            [
                Paragraph("Steel Yield Strength (fy)", cell_style),
                Paragraph(
                    f"{struct_audit.get('steel_grade_psi'):,} psi"
                    if struct_audit.get("steel_grade_psi")
                    else "Not Specified",
                    cell_style,
                ),
                Paragraph("Grade 60 (60,000 psi) ASTM A615", cell_note),
            ],
            [
                Paragraph("Slab Thickness", cell_style),
                Paragraph(
                    f"{struct_audit.get('slab_thickness_in')} inches"
                    if struct_audit.get("slab_thickness_in")
                    else "Not Specified",
                    cell_style,
                ),
                Paragraph("Min 4.5 - 5.0 inches (Deflection control)", cell_note),
            ],
            [
                Paragraph("Column Schedule & Rebar", cell_style),
                Paragraph(
                    "Detailed & Present" if struct_audit.get("column_schedule") else "Missing on Drawing", cell_style
                ),
                Paragraph("Mandatory Column Sizes & Tie Spacing", cell_note),
            ],
            [
                Paragraph("Beam Framing & Schedule", cell_style),
                Paragraph(
                    "Detailed & Present" if struct_audit.get("beam_schedule") else "Missing on Drawing", cell_style
                ),
                Paragraph("Mandatory Beam Depth & Stirrups", cell_note),
            ],
            [
                Paragraph("Slab Reinforcement Detailing", cell_style),
                Paragraph(
                    "Detailed & Present" if struct_audit.get("slab_rebar_detail") else "Missing on Drawing", cell_style
                ),
                Paragraph("Main & Distribution Rebar Layout", cell_note),
            ],
            [
                Paragraph("General Structural Notes", cell_style),
                Paragraph("Specified" if struct_audit.get("structural_notes") else "Missing", cell_style),
                Paragraph("Clear Covers & Development Lengths", cell_note),
            ],
        ]
        s_table = Table(s_rows, colWidths=[180, 160, 200])
        s_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(s_table)
        story.append(Spacer(1, 10))

    # 7. Structural Stability Certificate & PEC Credential Audit
    cert_audit = verdict_data.get("certificate_audit", {})
    if (
        cert_audit.get("certificate_present")
        or cert_audit.get("engineer_name")
        or cert_audit.get("pec_registration_no")
    ):
        story.append(Paragraph("5. Structural Stability Certificate & PEC Credential Audit", section_heading))
        c_rows = [
            [
                Paragraph("<b>Validation Check</b>", cell_bold),
                Paragraph("<b>Extracted Certificate Details</b>", cell_bold),
                Paragraph("<b>Verification Status</b>", cell_bold),
            ],
            [
                Paragraph("Registered Structural Engineer", cell_style),
                Paragraph(str(cert_audit.get("engineer_name") or "Not Legible"), cell_style),
                Paragraph("Identity on Document", cell_note),
            ],
            [
                Paragraph("PEC Registration Number", cell_style),
                Paragraph(str(cert_audit.get("pec_registration_no") or "Missing"), cell_style),
                Paragraph(
                    "<font color='green'>Valid PEC Format</font>"
                    if cert_audit.get("pec_valid_format")
                    else "<font color='red'>Invalid / Missing</font>",
                    cell_style,
                ),
            ],
            [
                Paragraph("Physical / Digital Signature", cell_style),
                Paragraph("Signed" if cert_audit.get("has_signature") else "Missing Signature", cell_style),
                Paragraph(
                    "<font color='green'>Verified</font>"
                    if cert_audit.get("has_signature")
                    else "<font color='red'>Unsigned</font>",
                    cell_style,
                ),
            ],
            [
                Paragraph("Official Engineer Seal / Stamp", cell_style),
                Paragraph("Affixed" if cert_audit.get("has_stamp") else "Missing Stamp", cell_style),
                Paragraph("Seal Check", cell_note),
            ],
            [
                Paragraph("Plot / Project Reference", cell_style),
                Paragraph(str(cert_audit.get("plot_reference") or "Not Stated"), cell_style),
                Paragraph("Plot Match", cell_note),
            ],
            [
                Paragraph("Issuance Date & Ref Number", cell_style),
                Paragraph(
                    f"Date: {cert_audit.get('cert_date') or '-'} | Ref: {cert_audit.get('cert_number') or '-'}",
                    cell_style,
                ),
                Paragraph("Validity Window", cell_note),
            ],
        ]
        c_table = Table(c_rows, colWidths=[180, 220, 140])
        c_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(c_table)
        story.append(Spacer(1, 10))

    # 8. Layers Summary
    layers = verdict_data.get("layers", [])
    if layers:
        layer_names = [lyr["name"] for lyr in layers if isinstance(lyr, dict) and "name" in lyr]
        layer_str = ", ".join(sorted(set(layer_names)))[:500]
        story.append(Paragraph("6. CAD & Vector Layers Detected", section_heading))
        story.append(
            Paragraph(f"<b>Total Layers:</b> {len(layers)} &nbsp;|&nbsp; <b>Layers:</b> {layer_str}...", cell_note)
        )
        story.append(Spacer(1, 10))

    # 9. Civil Engineering Audit Status Guide & Decision Rules
    story.append(Paragraph("7. Civil Engineering Audit Status Guide & Decision Rules", section_heading))
    story.append(
        Paragraph(
            "<i>Standardized grading system for residential building-control and structural scrutiny in Pakistan:</i>",
            cell_note,
        )
    )
    story.append(Spacer(1, 4))

    status_guide_data = [
        [
            Paragraph("<b>Scrutiny Status</b>", cell_bold),
            Paragraph("<b>Designation</b>", cell_bold),
            Paragraph("<b>Civil Engineering Meaning & Decision Rule</b>", cell_bold),
            Paragraph("<b>Required Action</b>", cell_bold),
        ],
        [
            Paragraph("<font color='#059669'><b>PASS</b></font>", cell_bold),
            Paragraph("Requirement Satisfied", cell_style),
            Paragraph(
                "The requested element, schedule, signature, or dimension is verified, explicitly present, legible, and compliant with relevant building control codes.",
                cell_note,
            ),
            Paragraph("Approved for records.", cell_note),
        ],
        [
            Paragraph("<font color='#dc2626'><b>CORRECTION REQUIRED</b></font>", cell_bold),
            Paragraph("Deficiency / Violation", cell_style),
            Paragraph(
                "The requested evidence is clearly missing, wrong, illegible, or incomplete. An explicit actionable note is attached citing the discrepancy.",
                cell_note,
            ),
            Paragraph("Drawing revision mandatory.", cell_note),
        ],
        [
            Paragraph("<font color='#d97706'><b>PENDING</b></font>", cell_bold),
            Paragraph("Unconfirmed / Ambiguous", cell_style),
            Paragraph(
                "The submission may be sufficient, but the required evidence cannot be definitively confirmed on visible sheets without clarification.",
                cell_note,
            ),
            Paragraph("Auditor clarification required.", cell_note),
        ],
        [
            Paragraph("<font color='#64748b'><b>NOT APPLICABLE</b></font>", cell_bold),
            Paragraph("Scope Exclusion", cell_style),
            Paragraph(
                "Requirement does not apply to this specific drawing package or building type (e.g. residential setbacks do not apply to structural rebar sets).",
                cell_note,
            ),
            Paragraph("No action needed.", cell_note),
        ],
    ]
    status_guide_table = Table(status_guide_data, colWidths=[95, 115, 230, 100])
    status_guide_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(status_guide_table)
    story.append(Spacer(1, 12))

    # 10. Engineering Parameter Glossary & Value Meaning Guide
    story.append(Paragraph("8. Engineering Parameter Glossary & Value Meaning Guide", section_heading))
    story.append(
        Paragraph(
            "<i>Engineering definitions, units, and municipal bylaw significance for all extracted values:</i>",
            cell_note,
        )
    )
    story.append(Spacer(1, 4))

    param_glossary_data = [
        [
            Paragraph("<b>Parameter Key</b>", cell_bold),
            Paragraph("<b>Engineering Name</b>", cell_bold),
            Paragraph("<b>Meaning, Formula & Code Significance</b>", cell_bold),
            Paragraph("<b>Standard Unit</b>", cell_bold),
        ],
        [
            Paragraph("plot_area_marla", cell_bold),
            Paragraph("Site / Plot Area", cell_style),
            Paragraph(
                "Explicit plot category or area. In Lahore/DHA/LDA, 1 Marla = 225 sq ft (revenue record = 272.25 sq ft). Governs setback requirements and FAR.",
                cell_note,
            ),
            Paragraph("Marla / Sq Ft", cell_note),
        ],
        [
            Paragraph("front_setback_ft", cell_bold),
            Paragraph("Front Setback", cell_style),
            Paragraph(
                "Mandatory clear open-to-sky space between road-facing plot boundary and building line. Required for sightlines, road widening, and emergency access.",
                cell_note,
            ),
            Paragraph("Feet (ft)", cell_note),
        ],
        [
            Paragraph("rear_setback_ft", cell_bold),
            Paragraph("Rear Setback", cell_style),
            Paragraph(
                "Mandatory clear open space between rear plot boundary and exterior wall for natural cross-ventilation, light wells, and utility passages.",
                cell_note,
            ),
            Paragraph("Feet (ft)", cell_note),
        ],
        [
            Paragraph("left / right_setback_ft", cell_bold),
            Paragraph("Side Clearances", cell_style),
            Paragraph(
                "Side open passages between plot boundary and building line. Mandatory for plots 10 Marla and larger (or corner plots on road flanks).",
                cell_note,
            ),
            Paragraph("Feet (ft)", cell_note),
        ],
        [
            Paragraph("total_height_ft", cell_bold),
            Paragraph("Total Building Height", cell_style),
            Paragraph(
                "Vertical elevation from crown of front road to highest top roof slab. Excludes mumty (stair tower), water tank enclosure, and parapet walls.",
                cell_note,
            ),
            Paragraph("Feet (ft)", cell_note),
        ],
        [
            Paragraph("ground_coverage_pct", cell_bold),
            Paragraph("Ground Coverage", cell_style),
            Paragraph(
                "Ratio of ground-floor plinth built-up footprint to total plot area. Excludes unroofed setbacks and open-to-sky courtyards.",
                cell_note,
            ),
            Paragraph("Percentage (%)", cell_note),
        ],
        [
            Paragraph("storeys", cell_bold),
            Paragraph("Habitable Storeys", cell_style),
            Paragraph(
                "Ground floor plus complete habitable upper storeys (G+1 or G+2). Excludes basements, mumty, overhead water tanks, and service pergolas.",
                cell_note,
            ),
            Paragraph("Floors Count", cell_note),
        ],
        [
            Paragraph("plinth_height_ft", cell_bold),
            Paragraph("Plinth Level", cell_style),
            Paragraph(
                "Finished floor elevation of ground floor above the crown of the adjoining road. Ensures stormwater runoff does not enter the residence.",
                cell_note,
            ),
            Paragraph("Feet (ft)", cell_note),
        ],
        [
            Paragraph("ugwt / ohwt_gallons", cell_bold),
            Paragraph("Water Tank Capacities", cell_style),
            Paragraph(
                "Domestic Underground (UGWT) and Overhead (OHWT) storage capacity in gallons. Calculated as: Internal Length × Width × Height × 7.48 gal/cu ft.",
                cell_note,
            ),
            Paragraph("Gallons", cell_note),
        ],
        [
            Paragraph("septic_length/width/depth", cell_bold),
            Paragraph("Septic Tank Geometry", cell_style),
            Paragraph(
                "Internal usable dimensions of on-site domestic sewage septic tank measured to underside of cover slab (not external wall/slab depth).",
                cell_note,
            ),
            Paragraph("Feet (ft)", cell_note),
        ],
        [
            Paragraph("projection_ft", cell_bold),
            Paragraph("Sunshade / Chajja", cell_style),
            Paragraph(
                "Maximum allowable cantilever canopy, weather shade, or sunshade projection over mandatory setbacks (typically max 2.5 to 3.0 ft).",
                cell_note,
            ),
            Paragraph("Feet (ft)", cell_note),
        ],
        [
            Paragraph("boundary_wall_height_ft", cell_bold),
            Paragraph("Boundary Wall", cell_style),
            Paragraph(
                "Total maximum allowable height of front/side plot boundary wall above road crown, including solid masonry plinth plus decorative railing/grill.",
                cell_note,
            ),
            Paragraph("Feet (ft)", cell_note),
        ],
        [
            Paragraph("concrete_grade_psi", cell_bold),
            Paragraph("Concrete Strength (fc')", cell_style),
            Paragraph(
                "Specified 28-day cylinder compressive strength of reinforced concrete (fc'). Minimum 3,000 psi required per Pakistan Building Code / ACI 318.",
                cell_note,
            ),
            Paragraph("PSI / MPa", cell_note),
        ],
        [
            Paragraph("steel_grade_psi", cell_bold),
            Paragraph("Steel Yield Strength (fy)", cell_style),
            Paragraph(
                "Specified minimum yield strength of deformed reinforcing rebar. Grade 60 (fy = 60,000 psi) ASTM A615 is standard for residential/commercial frames.",
                cell_note,
            ),
            Paragraph("PSI / Grade", cell_note),
        ],
        [
            Paragraph("slab_thickness_in", cell_bold),
            Paragraph("Slab Depth", cell_style),
            Paragraph(
                'Overall thickness of solid reinforced concrete floor and roof slabs. Minimum 4.5" to 5.0" required to satisfy serviceability and deflection criteria.',
                cell_note,
            ),
            Paragraph("Inches (in)", cell_note),
        ],
        [
            Paragraph("foundation_depth_ft", cell_bold),
            Paragraph("Foundation Excavation", cell_style),
            Paragraph(
                "Depth of foundation excavation below Natural Surface Level (NSL) to reach sound load-bearing soil stratum cited in geotechnical report.",
                cell_note,
            ),
            Paragraph("Feet (ft)", cell_note),
        ],
        [
            Paragraph("column / beam / slab schedules", cell_bold),
            Paragraph("Structural Detailing", cell_style),
            Paragraph(
                "Mandatory schedules specifying cross-section dimensions, longitudinal bar counts/diameters, clear concrete covers, and shear stirrup/tie spacing.",
                cell_note,
            ),
            Paragraph("Boolean / Detailed", cell_note),
        ],
    ]
    param_glossary_table = Table(param_glossary_data, colWidths=[120, 110, 230, 80])
    param_glossary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(param_glossary_table)

    # Build PDF
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    buffer.seek(0)
    return buffer
