"""Sheet numbers (A-01, S-02, SHEET 3 OF 12) and sequence-gap detection."""

import re


def audit_sheet_numbering(pages_list):
    """Validates sheet numbering, sequence continuity, missing sheets, duplicates, and discipline prefixes across all pages.

    Recognizes standard architectural/structural sheet codes:
    - Architectural: A-01, A-02, A-03, ARCH-1, AR-101, etc.
    - Structural: S-01, S-02, STR-1, ST-101, S-1, etc.
    - Plumbing / MEP: P-01, MEP-01, SAN-01, etc.
    - Electrical: E-01, ELEC-1, etc.
    - Civil / Site: C-01, SITE-1, etc.
    """
    detected_sheets = []

    # Strict sheet identification patterns (requiring explicit sheet/dwg keywords or standard discipline sheet prefixes)
    sheet_patterns = [
        r"\b(?:SHEET|DWG|DRG|SH)\s*(?:NO\.?|NUMBER|\#|\:|\-)?\s*([A-Z]{1,4})\s*[\-\_\.\s]?\s*0*(\d{1,3})\b",
        r"\b(?:SHEET|DWG|DRG|SH)\s*(?:NO\.?|NUMBER|\#|\:|\-)?\s*0*(\d{1,3})\b",
        r"\b(A|S|STR|ARCH|C|P|E|MEP)\s*[\-\_\.]\s*0*(\d{1,3})\b",
        r"\bSHEET\s+([0-9]+)\s+OF\s+([0-9]+)\b",
    ]

    discipline_map = {
        "A": "Architectural",
        "ARCH": "Architectural",
        "AR": "Architectural",
        "S": "Structural",
        "STR": "Structural",
        "ST": "Structural",
        "SE": "Structural",
        "C": "Civil / Site",
        "SITE": "Civil / Site",
        "CIV": "Civil / Site",
        "P": "Plumbing / Sanitary",
        "PL": "Plumbing",
        "MEP": "MEP / Services",
        "E": "Electrical",
        "EL": "Electrical",
        "ELEC": "Electrical",
    }

    for p in pages_list:
        p_num = p.get("n", 1)
        p_text = p.get("text", "")
        heads = [h[0] for h in p.get("heads", [])]
        combined_text = "\n".join(heads) + "\n" + p_text

        found_sheet = None
        for pat in sheet_patterns:
            matches = list(re.finditer(pat, combined_text, re.IGNORECASE))
            if matches:
                for m in matches:
                    if len(m.groups()) == 2 and m.group(1).isdigit() and m.group(2).isdigit():
                        # Match 'SHEET X OF Y'
                        seq = int(m.group(1))
                        found_sheet = {
                            "page": p_num,
                            "sheet_id": f"Sheet {seq}",
                            "discipline": "General Document",
                            "discipline_code": "GEN",
                            "sequence_number": seq,
                            "raw_match": m.group(0).strip(),
                        }
                        break
                    elif len(m.groups()) == 2 and not m.group(1).isdigit():
                        disc_raw = m.group(1).upper()
                        if disc_raw in ("SHEET", "DWG", "DRG", "SH"):
                            disc = "General"
                        else:
                            disc = discipline_map.get(disc_raw, disc_raw)
                        try:
                            seq = int(float(m.group(2)))
                        except Exception:
                            seq = 1
                        found_sheet = {
                            "page": p_num,
                            "sheet_id": f"{disc_raw}-{seq:02d}"
                            if disc_raw not in ("SHEET", "DWG", "DRG", "SH")
                            else f"SH-{seq:02d}",
                            "discipline": disc,
                            "discipline_code": disc_raw,
                            "sequence_number": seq,
                            "raw_match": m.group(0).strip(),
                        }
                        break
                    elif len(m.groups()) == 1 and m.group(1).isdigit():
                        seq = int(m.group(1))
                        found_sheet = {
                            "page": p_num,
                            "sheet_id": f"Sheet {seq}",
                            "discipline": "General Document",
                            "discipline_code": "GEN",
                            "sequence_number": seq,
                            "raw_match": m.group(0).strip(),
                        }
                        break
            if found_sheet:
                break

        if not found_sheet:
            found_sheet = {
                "page": p_num,
                "sheet_id": f"Sheet {p_num}",
                "discipline": "Drawing Sheet",
                "discipline_code": "GEN",
                "sequence_number": p_num,
                "raw_match": f"Sheet {p_num}",
            }
        detected_sheets.append(found_sheet)

    by_disc = {}
    for s in detected_sheets:
        d_code = s.get("discipline_code", "GEN")
        by_disc.setdefault(d_code, []).append(s)

    missing_sheets = []
    duplicate_sheets = []
    sequence_issues = []

    seen_ids = {}
    for s in detected_sheets:
        sid = s["sheet_id"]
        if sid.startswith("Page-"):
            continue
        if sid in seen_ids:
            duplicate_sheets.append(f"Duplicate sheet number '{sid}' on Page {s['page']} and Page {seen_ids[sid]}")
        else:
            seen_ids[sid] = s["page"]

    for d_code, s_list in by_disc.items():
        if d_code in ("GEN", "Page"):
            continue
        seqs = [s["sequence_number"] for s in s_list]
        if len(seqs) > 1:
            min_seq, max_seq = min(seqs), max(seqs)
            expected_set = set(range(min_seq, max_seq + 1))
            missing_set = expected_set - set(seqs)
            for m in sorted(missing_set):
                missing_sheets.append(f"{d_code}-{m:02d}")
                sequence_issues.append(
                    f"Missing sheet {d_code}-{m:02d} in {discipline_map.get(d_code, d_code)} sequence ({min_seq}..{max_seq})"
                )

            for k in range(len(seqs) - 1):
                if seqs[k + 1] < seqs[k]:
                    sequence_issues.append(
                        f"Out-of-sequence sheet order: {d_code}-{seqs[k]:02d} (p.{s_list[k]['page']}) is followed by {d_code}-{seqs[k + 1]:02d} (p.{s_list[k + 1]['page']})"
                    )

    is_valid = len(missing_sheets) == 0 and len(duplicate_sheets) == 0 and len(sequence_issues) == 0

    return {
        "detected_sheets": detected_sheets,
        "missing_sheets": missing_sheets,
        "duplicate_sheets": duplicate_sheets,
        "sequence_issues": sequence_issues,
        "is_sequence_valid": is_valid,
        "total_sheets_indexed": len(detected_sheets),
        "disciplines_present": sorted({s["discipline"] for s in detected_sheets}),
    }
