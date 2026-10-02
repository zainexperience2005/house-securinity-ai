"""TypeSafe System One (Jev) wrapper with conservative fallbacks.

Jev answers typed Choice questions (sheet type, checklist status). If the SDK
is missing or the API fails after retries, answers use PENDING/other so an
outage cannot silently become PASS or architectural_drawing.
"""

import time

from src.config.settings import typesafe_client


def _safe_fallback_choice(criteria):
    """Pick an uncertainty-preserving label when Jev cannot run.

    Dictionaries start with positive labels (PASS, architectural_drawing), so
    ``next(iter(criteria))`` would be an unsafe default.
    """
    if "PENDING" in criteria:
        return "PENDING"
    if "other" in criteria:
        return "other"
    return next(iter(criteria), "PENDING")


def _fallback_answers(questions, error):
    """Build a full answers map with zero confidence and the recorded error."""
    fallback = {}
    for qk, qv in questions.items():
        criteria = getattr(qv, "criteria", None) or (qv.get("criteria") if isinstance(qv, dict) else {})
        choice = _safe_fallback_choice(criteria)
        fallback[qk] = {
            "choice": choice,
            "confidence": 0.0,
            "probabilities": {key: (1.0 if key == choice else 0.0) for key in criteria},
            "error": error,
        }
    return fallback


def jev_call(state, questions):
    """Call TypeSafe System One with exponential backoff (3 attempts).

    Args:
        state: JSON-serializable context Jev reads (pages, observations, …).
        questions: Mapping of question id -> Choice (criteria + instructions).

    Returns:
        tuple: (answers dict with choice/confidence/probabilities, usage dict)
    """
    if not typesafe_client:
        return _fallback_answers(questions, "TypeSafeClient not initialized"), {"input_tokens": 0, "output_tokens": 0}

    last_error = None
    for attempt in range(3):
        try:
            res = typesafe_client.system_one(state=state, questions=questions)
            answers = {k: (v.model_dump() if hasattr(v, "model_dump") else v) for k, v in res.answers.items()}
            usage = {
                "input_tokens": getattr(res.usage, "input_tokens", 0) if hasattr(res, "usage") and res.usage else 0,
                "output_tokens": getattr(res.usage, "output_tokens", 0) if hasattr(res, "usage") and res.usage else 0,
            }
            return answers, usage
        except Exception as exc:
            last_error = str(exc)
            if attempt < 2:
                time.sleep(0.5 * (2**attempt))

    return _fallback_answers(questions, last_error or "TypeSafe request failed"), {
        "input_tokens": 0,
        "output_tokens": 0,
    }
