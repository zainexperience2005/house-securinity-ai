"""Pick a controlling drawing revision and drop values from older marked sheets."""

import re


def filter_values_to_master_revision(raw_values, revision_audit):
    """Exclude values explicitly tied to an older numeric drawing revision.

    Unmarked sheets are retained for the normal conflict resolver: a title
    block often carries one revision for a whole set rather than repeating it
    on every page.  Values from a page that is explicitly marked older than a
    clearly established master revision are never allowed to drive bylaw
    compliance.
    """
    history = (revision_audit or {}).get("revision_history", [])
    master_revision = str((revision_audit or {}).get("master_revision", ""))

    def number(revision_id):
        found = re.findall(r"\d+", str(revision_id or ""))
        return int(found[0]) if found else None

    master_number = number(master_revision)
    page_revisions = {}
    for entry in history:
        item = entry.model_dump() if hasattr(entry, "model_dump") else entry
        page = item.get("page")
        revision_number = number(item.get("revision_id"))
        if page is not None and revision_number is not None:
            page_revisions[page] = revision_number

    if master_number is None or not page_revisions:
        return list(raw_values), []

    accepted = []
    flags = []
    for value in raw_values:
        item = value.model_dump() if hasattr(value, "model_dump") else value
        page = item.get("page")
        page_revision = page_revisions.get(page)
        if page_revision is not None and page_revision < master_number:
            flags.append(
                f"REVISION FILTER: Ignored architectural values from page {page} "
                f"(Rev {page_revision}); controlling revision is {master_revision}."
            )
            continue
        accepted.append(value)
    return accepted, list(dict.fromkeys(flags))


def resolve_authoritative_revisions(revisions_table, doc_revisions, pages_list):
    """Deterministically extracts, sorts, and audits sheet revisions across the entire submission.

    Resolves:
    - Latest master revision ID and date
    - Per-sheet revision breakdown
    - Sheet-to-sheet revision conflicts (e.g. Architectural Sheet at Rev 2 while Structural is Rev 0)
    """
    entries = []

    # 1. From OpenAI structured revisions table
    for r in revisions_table:
        r_dict = r.model_dump() if hasattr(r, "model_dump") else r
        if r_dict.get("revision_id"):
            entries.append(r_dict)

    # 2. From document revision strings
    for dr in doc_revisions:
        if isinstance(dr, str) and dr.strip():
            entries.append(
                {
                    "revision_id": dr.strip(),
                    "date": None,
                    "sheet_number": None,
                    "description": "Extracted from drawing revision block",
                    "page": 1,
                }
            )

    # 3. Deterministic regex scan across page text layers
    for p in pages_list:
        p_num = p.get("n", 1)
        p_text = p.get("text", "")
        for m in re.finditer(r"\b(REV(?:ISION)?\.?[\s\:\-\#]*([A-Z0-9\-\.]+))\b", p_text, re.IGNORECASE):
            rev_str = m.group(1).strip()
            if not any(e.get("revision_id") == rev_str and e.get("page") == p_num for e in entries):
                entries.append(
                    {
                        "revision_id": rev_str,
                        "date": None,
                        "sheet_number": f"Page {p_num}",
                        "description": "Detected in digital title-block layer",
                        "page": p_num,
                    }
                )

    if not entries:
        return {
            "master_revision": "Rev 0 (Initial Submission)",
            "revision_date": None,
            "sheet_count": len(pages_list),
            "is_consistent": True,
            "revision_history": [],
            "conflict_flags": [],
        }

    def rev_sort_key(e):
        rid = str(e.get("revision_id", "")).upper()
        nums = re.findall(r"\d+", rid)
        return (int(nums[0]) if nums else 0, rid)

    sorted_entries = sorted(entries, key=rev_sort_key, reverse=True)
    master_rev = sorted_entries[0].get("revision_id", "Rev 0")
    master_date = sorted_entries[0].get("date")

    by_page = {}
    for e in entries:
        pn = e.get("page", 1)
        by_page.setdefault(pn, set()).add(e.get("revision_id"))

    conflicts = []
    if len(by_page) > 1:
        rev_sets = list(by_page.values())
        if any(s != rev_sets[0] for s in rev_sets[1:]):
            conflicts.append(
                f"Sheet revision mismatch detected across submission pages: { {f'Page {k}': list(v) for k, v in by_page.items()} }"
            )

    return {
        "master_revision": master_rev,
        "revision_date": master_date,
        "sheet_count": len(pages_list),
        "is_consistent": len(conflicts) == 0,
        "revision_history": sorted_entries,
        "conflict_flags": conflicts,
    }
