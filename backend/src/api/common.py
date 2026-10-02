"""Shared helper utilities for House Scrutiny API routers."""

import logging
import os
import tempfile
import time
from typing import Any

from fastapi import HTTPException

from src.config.settings import settings
from src.pipeline import run

logger = logging.getLogger("house_scrutiny.api")


def raise_if_ineligible(verdict: dict[str, Any]) -> None:
    """Keep unsupported files out of reports and persistent review cases."""
    overall = verdict.get("overall")
    if overall == "UNSUPPORTED_DOCUMENT":
        raise HTTPException(
            status_code=422,
            detail={
                "code": "UNSUPPORTED_DOCUMENT",
                "message": verdict.get("message", "Upload an architectural or structural drawing package."),
                "doc_type": verdict.get("doc_type", {}),
            },
        )
    if overall == "CLASSIFICATION_UNAVAILABLE":
        raise HTTPException(
            status_code=503,
            detail={
                "code": "CLASSIFICATION_UNAVAILABLE",
                "message": verdict.get(
                    "message",
                    "Document classifier could not reach vision services. Please retry shortly.",
                ),
            },
        )


def run_submission_package(
    package_bytes: bytes,
    authority: str,
    model_name: str | None = None,
    thread_name: str | None = None,
    thread_id: str | None = None,
) -> tuple[dict[str, Any], float]:
    """Write bytes to a temporary PDF, execute the pipeline graph, and attach elapsed time."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(package_bytes)
        tmp_path = tmp_file.name
    try:
        active_model = model_name or settings.openai_model
        logger.info(f"⚙️ Running Scrutiny Graph: Authority={authority} | Model={active_model} | Thread={thread_name}")
        started = time.perf_counter()
        verdict = run(
            tmp_path,
            authority=authority,
            active_model=active_model,
            thread_name=thread_name,
            thread_id=thread_id,
        )
        elapsed = round(time.perf_counter() - started, 2)
        verdict["processing_seconds"] = elapsed
        logger.info(
            f"✅ Scrutiny Graph Completed in {elapsed:.2f}s | "
            f"Verdict: {verdict.get('overall', 'UNKNOWN')} | "
            f"Doc Type: {verdict.get('doc_type', {}).get('document_type', 'N/A')}"
        )
        return verdict, elapsed
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
