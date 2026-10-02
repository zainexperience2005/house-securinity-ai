"""Prompt-injection defense for untrusted CAD/PDF text.

Every text line from metadata, annotations, form fields, hidden runs, and page
content is scanned with ``INJ``. Matching lines are dropped from the packed
prompt and recorded in ``security_audit`` so engineers can see the attempt.
"""

import time

from src.config.prompts import INJ


def scrub(t, flags, where, page_num=None, security_log=None):
    """Remove injection-pattern lines from ``t`` and append audit records.

    Args:
        t: Raw extracted text (may be None).
        flags: Mutable list of human-readable review flags (mutated in place).
        where: Location label (e.g. ``page 3``, ``metadata.Creator``).
        page_num: 1-based page index when known.
        security_log: Optional list that receives structured CRITICAL entries.

    Returns:
        Sanitized multiline string safe to embed in vision/Jev payloads.
    """
    keep = []
    for ln in str(t or "").splitlines():
        if INJ.search(ln):
            audit_entry = {
                "page": page_num,
                "location": where,
                "flag_type": "PROMPT_INJECTION_ATTEMPT",
                "matched_snippet": ln.strip()[:120],
                "raw_payload": ln,
                "sanitization": "REMOVED_FROM_PROMPT",
                "severity": "CRITICAL",
                "timestamp": time.time(),
            }
            flags.append(f"Security Alert in {where}: adversarial injection pattern scrubbed ({ln.strip()[:80]})")
            if security_log is not None:
                security_log.append(audit_entry)
        else:
            keep.append(ln)
    return "\n".join(keep)
