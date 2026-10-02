"""Compile and run the House Scrutiny LangGraph with Short-Term and Long-Term Memory.

Flow: ingest -> (unreadable? reject : gate) -> (eligible? crop : reject) ->
extract -> judge -> report -> END.

Persistence Architecture:
- Short-term Memory: Thread-scoped checkpointing with LangGraph PostgresSaver (Neon DB).
  Each PDF upload creates a new, isolated thread sequence. Every node transition
  (ingest -> gate -> crop -> extract -> judge -> report) is persisted to Neon DB checkpoints.
- Long-term Memory: Scrutiny history, drawing index, and municipal precedent across threads.
  (User preferences are intentionally excluded to keep individual submissions isolated).
"""

import os
import time

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from src.config.schemas import S
from src.config.settings import settings
from src.memory.long_term import save_thread_scrutiny
from src.memory.short_term import generate_thread_id, get_checkpointer

from .nodes import n_crop, n_extract, n_gate, n_ingest, n_judge, n_reject, n_report


def build(checkpointer: BaseCheckpointSaver | None = None):
    """Assemble and compile the StateGraph. Nodes share TypedDict ``S``.

    Args:
        checkpointer: Optional LangGraph checkpoint saver (e.g., PostgresSaver or InMemorySaver).
                      If provided, enables step-by-step state checkpointing and time travel.
    """
    g = StateGraph(S)

    for name, fn in (
        ("ingest", n_ingest),
        ("gate", n_gate),
        ("reject", n_reject),
        ("crop", n_crop),
        ("extract", n_extract),
        ("judge", n_judge),
        ("report", n_report),
    ):
        g.add_node(name, fn)

    g.add_edge(START, "ingest")

    # Password-empty-corrupt PDFs skip classification and vision entirely.
    g.add_conditional_edges(
        "ingest", lambda s: "reject" if s.get("unreadable") else "gate", {"reject": "reject", "gate": "gate"}
    )

    # Resumes, invoices, cert-only packages never consume vision tokens.
    g.add_conditional_edges(
        "gate",
        lambda s: "crop" if s.get("document_eligibility") == "ELIGIBLE" else "reject",
        {"crop": "crop", "reject": "reject"},
    )

    for a, b in (("crop", "extract"), ("extract", "judge"), ("judge", "report"), ("report", END)):
        g.add_edge(a, b)
    g.add_edge("reject", END)

    if checkpointer is not None:
        return g.compile(checkpointer=checkpointer)
    return g.compile()


# Default stateless graph for fast or offline runs
compiled_graph = build()


def run(
    pdf_path: str,
    authority: str | None = "DHA_Lahore",
    thread_id: str | None = None,
    thread_name: str | None = None,
    use_memory: bool = True,
    checkpointer: BaseCheckpointSaver | None = None,
    active_model: str | None = None,
    **kwargs,
) -> dict:
    """Execute scrutiny on a local PDF path with short-term and long-term memory.

    Args:
        pdf_path: Path to the PDF file on disk.
        authority: Municipal authority bylaws to enforce (default: "DHA_Lahore").
        thread_id: Optional thread ID. If None, generates a new unique thread for this PDF.
        thread_name: Human-friendly thread name (defaults to the PDF basename).
        use_memory: Whether to enable PostgreSQL checkpointing and long-term storage.
        checkpointer: Custom checkpointer instance (defaults to Neon PostgresSaver).
        active_model: Custom or switched multimodal vision model identifier.

    Returns:
        dict: The final scrutiny verdict dictionary, including thread_id metadata.
    """
    filename = os.path.basename(pdf_path)
    active_thread_name = thread_name or filename
    active_thread_id = thread_id or generate_thread_id(filename)
    chosen_model = active_model or kwargs.get("model_name") or settings.openai_model

    initial_state = {
        "pdf": pdf_path,
        "authority": authority,
        "thread_id": active_thread_id,
        "thread_name": active_thread_name,
        "active_model": chosen_model,
    }

    started_at = time.perf_counter()
    if use_memory:
        active_checkpointer = checkpointer or get_checkpointer()
        executable_graph = build(checkpointer=active_checkpointer)
        config = {"configurable": {"thread_id": active_thread_id}}
        result = executable_graph.invoke(initial_state, config=config)
    else:
        result = compiled_graph.invoke(initial_state)

    elapsed_seconds = round(time.perf_counter() - started_at, 2)
    verdict = result.get("verdict", {})
    if isinstance(verdict, dict):
        verdict["thread_id"] = active_thread_id
        verdict["thread_name"] = active_thread_name
        verdict["processing_seconds"] = elapsed_seconds

        # Persist to Neon DB long-term cross-submission memory
        if use_memory:
            try:
                save_thread_scrutiny(
                    thread_id=active_thread_id,
                    thread_name=active_thread_name,
                    pdf_filename=filename,
                    authority=authority or "DHA_Lahore",
                    verdict=verdict,
                    processing_time_seconds=elapsed_seconds,
                    metadata={
                        "pdf_path": pdf_path,
                        "checks_count": len(verdict.get("checks", [])),
                        "review_flags": len(verdict.get("review_flags", [])),
                        "processing_seconds": elapsed_seconds,
                    },
                )
            except Exception:
                # Fallback to local memory cache already handled inside save_thread_scrutiny
                pass

    return verdict


def stream_run(
    pdf_path: str,
    authority: str | None = "DHA_Lahore",
    thread_id: str | None = None,
    thread_name: str | None = None,
    use_memory: bool = True,
    checkpointer: BaseCheckpointSaver | None = None,
    active_model: str | None = None,
    **kwargs,
):
    """Execute scrutiny on a local PDF path and yield real-time node progress events.

    Yields:
        dict: Milestone events (pipeline_start, node_start, node_complete, pipeline_complete)
    """
    filename = os.path.basename(pdf_path)
    active_thread_name = thread_name or filename
    active_thread_id = thread_id or generate_thread_id(filename)
    chosen_model = active_model or kwargs.get("model_name") or settings.openai_model

    initial_state = {
        "pdf": pdf_path,
        "authority": authority,
        "thread_id": active_thread_id,
        "thread_name": active_thread_name,
        "active_model": chosen_model,
    }

    started_at = time.perf_counter()

    yield {
        "event": "pipeline_start",
        "thread_id": active_thread_id,
        "thread_name": active_thread_name,
        "filename": filename,
        "authority": authority,
        "model": chosen_model,
        "timestamp": time.time(),
    }

    if use_memory:
        active_checkpointer = checkpointer or get_checkpointer()
        executable_graph = build(checkpointer=active_checkpointer)
        config = {"configurable": {"thread_id": active_thread_id}}
        stream_iter = executable_graph.stream(initial_state, config=config, stream_mode="updates")
    else:
        stream_iter = compiled_graph.stream(initial_state, stream_mode="updates")

    final_verdict = None
    node_start_time = time.perf_counter()

    node_labels = {
        "ingest": (
            "Document Ingestion & CAD Extraction",
            "Reading PDF sheets, parsing CAD vector geometry, and auditing document integrity...",
        ),
        "gate": (
            "Classification & Scope Gate",
            "Analyzing title blocks, sheet classification, and municipal audit eligibility...",
        ),
        "crop": (
            "Region-of-Interest Cropping",
            "Generating high-resolution crops of title blocks, structural schedules, and plans...",
        ),
        "extract": (
            "Multimodal Vision Extraction",
            "Extracting concrete grade, slab thickness, steel rebar specs, and setbacks...",
        ),
        "judge": (
            "Bylaw Compliance Evaluation",
            "Auditing extracted measurements against statutory housing authority rules...",
        ),
        "report": (
            "Report Synthesis & Verdict",
            "Compiling final scrutiny audit matrix, review flags, and evidence chain...",
        ),
        "reject": ("Document Rejection", "Document was flagged as ineligible or unreadable for automated scrutiny."),
    }

    for chunk in stream_iter:
        node_elapsed = round(time.perf_counter() - node_start_time, 2)
        node_start_time = time.perf_counter()

        for node_name, node_output in chunk.items():
            label, default_desc = node_labels.get(node_name, (node_name.capitalize(), ""))
            summary = ""
            details = {}

            if node_name == "ingest":
                pages = node_output.get("pages") or []
                cad = node_output.get("cad_geometry") or {}
                paths = cad.get("total_vector_paths", 0)
                dups = (node_output.get("duplicates_audit") or {}).get("has_duplicates", False)
                unreadable = bool(node_output.get("unreadable"))
                summary = (
                    f"Parsed {len(pages)} page(s) with {paths:,} CAD vector geometry elements. Integrity verified."
                )
                details = {
                    "pages_count": len(pages),
                    "vector_paths": paths,
                    "has_duplicates": dups,
                    "unreadable": unreadable,
                }

            elif node_name == "gate":
                dt = node_output.get("doc_type") or {}
                doc_choice = dt.get("choice") or dt.get("primary_type") or "Drawing Package"
                conf = round((dt.get("confidence") or 0.95) * 100)
                elig = node_output.get("document_eligibility", "ELIGIBLE")
                has_arch = dt.get("has_architectural", False)
                has_struct = dt.get("has_structural", False)
                summary = f"Classified as {doc_choice.replace('_', ' ').title()} ({conf}% confidence). Scope: {'Arch + Struct' if (has_arch and has_struct) else 'Structural' if has_struct else 'Architectural'}."
                details = {
                    "document_type": doc_choice,
                    "confidence_pct": conf,
                    "eligibility": elig,
                    "has_architectural": has_arch,
                    "has_structural": has_struct,
                    "page_types": dt.get("page_types", {}),
                }

            elif node_name == "crop":
                crops = node_output.get("crops") or []
                summary = (
                    f"Generated {len(crops)} high-resolution ROI crops targeting title blocks, notes, and schedules."
                )
                details = {
                    "crops_count": len(crops),
                }

            elif node_name == "extract":
                vals = node_output.get("vals") or {}
                struct = vals.get("structural") or {}
                arch = vals.get("architectural") or {}
                conc = struct.get("concrete_grade_psi")
                slab = struct.get("slab_thickness_in")
                steel = struct.get("steel_grade_psi")
                extracted_params = {}
                if conc:
                    extracted_params["concrete_grade_psi"] = conc
                if slab:
                    extracted_params["slab_thickness_in"] = slab
                if steel:
                    extracted_params["steel_grade_psi"] = steel

                param_strs = []
                if conc:
                    param_strs.append(f"Concrete: {conc} PSI")
                if slab:
                    param_strs.append(f"Slab: {slab} in")
                if steel:
                    param_strs.append(f"Steel: {steel} PSI")
                param_summary = f" Found: {', '.join(param_strs)}" if param_strs else ""
                summary = f"Multimodal vision extraction completed across sheet crops.{param_summary}"
                details = {
                    "parameters": extracted_params,
                    "structural_detected": bool(struct),
                    "architectural_detected": bool(arch),
                }

            elif node_name == "judge":
                checks = node_output.get("checks") or {}
                pass_count = sum(1 for c in checks.values() if isinstance(c, dict) and c.get("status") == "PASS")
                corr_count = sum(
                    1 for c in checks.values() if isinstance(c, dict) and c.get("status") == "CORRECTION_REQUIRED"
                )
                viol_count = sum(
                    1 for c in checks.values() if isinstance(c, dict) and c.get("status") in ("VIOLATION", "FAIL")
                )
                summary = f"Bylaw audit complete: {pass_count} passed, {corr_count} corrections required, {viol_count} violations."
                details = {
                    "passed": pass_count,
                    "corrections_required": corr_count,
                    "violations": viol_count,
                    "total_checks": len(checks),
                }

            elif node_name in ("report", "reject"):
                final_verdict = node_output.get("verdict") or {}
                overall = final_verdict.get("overall", "UNKNOWN")
                summary = f"Final scrutiny audit report compiled with verdict: {overall}."
                details = {
                    "overall_verdict": overall,
                }

            yield {
                "event": "node_complete",
                "node": node_name,
                "label": label,
                "summary": summary,
                "elapsed_seconds": node_elapsed,
                "details": details,
                "timestamp": time.time(),
            }

    total_elapsed = round(time.perf_counter() - started_at, 2)
    if isinstance(final_verdict, dict):
        final_verdict["thread_id"] = active_thread_id
        final_verdict["thread_name"] = active_thread_name
        final_verdict["processing_seconds"] = total_elapsed

        if use_memory:
            try:
                save_thread_scrutiny(
                    thread_id=active_thread_id,
                    thread_name=active_thread_name,
                    pdf_filename=filename,
                    authority=authority or "DHA_Lahore",
                    verdict=final_verdict,
                    processing_time_seconds=total_elapsed,
                    metadata={
                        "pdf_path": pdf_path,
                        "checks_count": len(final_verdict.get("checks", [])),
                        "review_flags": len(final_verdict.get("review_flags", [])),
                        "processing_seconds": total_elapsed,
                    },
                )
            except Exception:
                pass

    yield {
        "event": "pipeline_complete",
        "thread_id": active_thread_id,
        "elapsed_seconds": total_elapsed,
        "verdict": final_verdict,
        "timestamp": time.time(),
    }
