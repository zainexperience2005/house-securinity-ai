"""OpenAI vision extraction with structured JSON schema and batch isolation.

Each request is one chunk of images; the model is told not to treat missing
pages in that chunk as a missing submission. Transient 429s are retried by
ChatOpenAI; chunks run concurrently up to VISION_MAX_CONCURRENCY.
"""

import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config.prompts import SYSTEM
from src.config.schemas import Extraction
from src.config.settings import VISION_MAX_CONCURRENCY, settings


def _filter_batch_scope_flags(flags):
    """Drop model claims caused by an individual vision chunk, not the upload.

    Every page is tracked deterministically by ``n_crop``. A model sees one
    image chunk at a time, so it must not turn that local view into an
    ``INCOMPLETE_BATCH`` submission finding.
    """
    return [
        flag
        for flag in flags
        if not re.search(r"\bincomplete[ _-]?batch\b|\bonly pages?\b.*\b(?:supplied|available)\b", flag, re.IGNORECASE)
    ]


def run_vision_extraction_batch(prompt_header, doc_text, pass_shots, max_batch_size=8, model_name=None):
    """Executes structured vision extraction with automatic chunking/batching and 429 rate-limit backoff.

    Ensures complete coverage for submissions of any size without
    exceeding LLM token-per-minute (TPM) limits or failing on transient 429 rate limits.
    """
    if not pass_shots:
        return {
            "values": [],
            "structural_values": [],
            "certificate_details": None,
            "observations": [],
            "flags": [],
            "revisions": [],
        }, {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    combined_parsed = {
        "values": [],
        "structural_values": [],
        "certificate_details": None,
        "observations": [],
        "flags": [],
        "revisions": [],
    }
    usage_sum = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    active_model = model_name or settings.openai_model
    llm = ChatOpenAI(model=active_model, max_retries=6, timeout=120).with_structured_output(
        Extraction, method="json_schema", include_raw=True
    )

    batch_messages = []
    batch_numbers = []
    for i in range(0, len(pass_shots), max_batch_size):
        chunk = pass_shots[i : i + max_batch_size]
        batch_num = (i // max_batch_size) + 1
        total_batches = (len(pass_shots) + max_batch_size - 1) // max_batch_size
        batch_suffix = f" (Batch {batch_num}/{total_batches})" if total_batches > 1 else ""

        content = [
            {
                "type": "text",
                "text": (
                    f"{prompt_header}{batch_suffix}\n"
                    "BATCH SCOPE: These images are one processing chunk from a single uploaded submission. "
                    "Do not claim that the submission is incomplete, that only these pages were supplied, or that "
                    "another page is missing merely because it is outside this chunk. Report only evidence tied to a page.\n"
                    f"DOCUMENT TEXT:\n{doc_text[:8000]}"
                ),
            }
        ]
        for sh in chunk:
            content.append({"type": "text", "text": f"[Page {sh['page']} - {sh['label']}]"})
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64," + sh["b64"], "detail": sh["detail"]},
                }
            )
        batch_messages.append([SystemMessage(SYSTEM), HumanMessage(content)])
        batch_numbers.append(batch_num)

    # Independent image chunks do not depend on one another.  Runnable.batch
    # keeps the response order deterministic while using a bounded worker pool.
    # ChatOpenAI's built-in max_retries still handles transient 429/network errors.
    results = llm.batch(
        batch_messages,
        config={"max_concurrency": VISION_MAX_CONCURRENCY},
        return_exceptions=True,
    )

    for batch_num, res in zip(batch_numbers, results, strict=False):
        if isinstance(res, Exception):
            combined_parsed["flags"].append(f"OpenAI Vision extraction batch {batch_num} failed: {str(res)[:120]}")
            continue
        if res and res.get("parsed"):
            p = res["parsed"].model_dump()
            combined_parsed["values"].extend(p.get("values", []))
            combined_parsed["structural_values"].extend(p.get("structural_values", []))
            if p.get("certificate_details") and not combined_parsed["certificate_details"]:
                combined_parsed["certificate_details"] = p["certificate_details"]
            combined_parsed["observations"].extend(p.get("observations", []))
            combined_parsed["flags"].extend(_filter_batch_scope_flags(p.get("flags", [])))
            if p.get("revision"):
                combined_parsed["revisions"].append(p["revision"])
            if p.get("revisions_table"):
                if "revisions_table" not in combined_parsed:
                    combined_parsed["revisions_table"] = []
                combined_parsed["revisions_table"].extend(p["revisions_table"])

        if res and hasattr(res.get("raw"), "usage_metadata") and res["raw"].usage_metadata:
            u = res["raw"].usage_metadata
            usage_sum["input_tokens"] += u.get("input_tokens", 0)
            usage_sum["output_tokens"] += u.get("output_tokens", 0)
            usage_sum["total_tokens"] += u.get("total_tokens", 0)

    return combined_parsed, usage_sum
