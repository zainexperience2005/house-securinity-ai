"""Autonomous drawing compliance scrutiny, multi-file packages, and streaming SSE endpoints."""

import asyncio
import json
import logging
import os
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from src.api.common import raise_if_ineligible, run_submission_package
from src.config.settings import settings
from src.core.case_store import create_case, merge_pdf_documents
from src.pipeline import stream_run

logger = logging.getLogger("house_scrutiny.api")

router = APIRouter(prefix="/api/v1/scrutinize", tags=["Drawing Scrutiny"])


@router.post("", summary="Synchronous drawing package scrutiny")
async def scrutinize_drawing_package(
    file: UploadFile = File(..., description="Engineering drawing package in PDF format."),
    plot_id: str | None = Form(None, description="Plot ID or unique reference (e.g. 'Plot-93B-OPF')."),
    authority: str | None = Form(
        "DHA_Lahore", description="Target Housing Society (DHA_Lahore, CDA_Islamabad, LDA, Bahria_Town, OPF_Islamabad)."
    ),
    revision: str | None = Form(None, description="Drawing revision code (e.g. 'Rev 0', 'Rev 1', 'Rev 2')."),
    model_name: str | None = Form(None, description="Optional custom or switched multimodal model."),
    thread_id: str | None = Form(None, description="Optional persistent thread ID to continue/update."),
):
    """Uploads an architectural or structural drawing set and executes the multi-stage autonomous scrutiny pipeline."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF drawing files (.pdf) are supported.")

    try:
        contents = await file.read()
        logger.info(f"📥 Received file upload: '{file.filename}' ({len(contents) / 1024:.1f} KB)")
        verdict, elapsed = run_submission_package(
            contents,
            authority or "DHA_Lahore",
            model_name=model_name,
            thread_name=file.filename,
            thread_id=thread_id,
        )
        raise_if_ineligible(verdict)

        if revision:
            verdict["revision"] = revision
        case_id = create_case([(file.filename, contents)], verdict, authority)

        return {
            "status": "SUCCESS",
            "case_id": case_id,
            "thread_id": verdict.get("thread_id"),
            "filename": file.filename,
            "elapsed_seconds": elapsed,
            "processing_seconds": elapsed,
            "overall_verdict": verdict.get("overall"),
            "doc_type": verdict.get("doc_type"),
            "verdict": verdict,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Scrutiny failed for '{file.filename}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scrutiny pipeline execution failed: {e!s}")


@router.post("/stream", summary="Real-time streaming scrutiny with milestone SSE and HITL cancellation")
async def scrutinize_drawing_package_stream(
    request: Request,
    file: UploadFile = File(..., description="Engineering drawing package in PDF format."),
    plot_id: str | None = Form(None, description="Plot ID or unique reference (e.g. 'Plot-93B-OPF')."),
    authority: str | None = Form(
        "DHA_Lahore", description="Target Housing Society (DHA_Lahore, CDA_Islamabad, LDA, Bahria_Town, OPF_Islamabad)."
    ),
    revision: str | None = Form(None, description="Drawing revision code (e.g. 'Rev 0', 'Rev 1', 'Rev 2')."),
    model_name: str | None = Form(None, description="Optional custom or switched multimodal model."),
    thread_id: str | None = Form(None, description="Optional persistent thread ID to continue/update."),
):
    """Uploads an architectural or structural drawing and streams real-time LangGraph node milestones via SSE."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF drawing files (.pdf) are supported.")

    contents = await file.read()
    active_model = model_name or settings.openai_model
    target_authority = authority or "DHA_Lahore"
    filename = file.filename
    logger.info(f"📥 Received file upload for streaming: '{filename}' ({len(contents) / 1024:.1f} KB)")

    async def event_stream():
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(contents)
            tmp_path = tmp_file.name

        try:
            generator = stream_run(
                tmp_path,
                authority=target_authority,
                active_model=active_model,
                thread_name=filename,
                thread_id=thread_id,
            )
            for event in generator:
                # Check for Human-In-The-Loop client cancellation
                if await request.is_disconnected():
                    logger.info(f"🛑 [HITL] Client stopped scrutiny pipeline stream for '{filename}'")
                    break

                event_type = event.get("event")

                if event_type == "pipeline_complete":
                    final_verdict = event.get("verdict")
                    if revision and isinstance(final_verdict, dict):
                        final_verdict["revision"] = revision

                    try:
                        case_id = create_case([(filename, contents)], final_verdict or {}, target_authority)
                        event["case_id"] = case_id
                        if isinstance(final_verdict, dict):
                            final_verdict["case_id"] = case_id
                    except Exception as _ce:
                        logger.warning(f"Could not create case for stream: {_ce}")

                yield f"data: {json.dumps(event, default=str)}\n\n"
                await asyncio.sleep(0.001)

        except asyncio.CancelledError:
            logger.info(f"🛑 [HITL] Scrutiny stream task cancelled for '{filename}'")
        except Exception as exc:
            logger.error(f"❌ Error during streamed scrutiny of {filename}: {exc}", exc_info=True)
            err_payload = {
                "event": "error",
                "error": str(exc),
                "message": f"Scrutiny failed: {exc!s}",
            }
            yield f"data: {json.dumps(err_payload)}\n\n"
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/package", summary="Scrutinize multi-file drawing package")
async def scrutinize_submission_package(
    files: list[UploadFile] = File(
        ..., description="Architectural, structural, and certificate PDFs for one submission."
    ),
    authority: str | None = Form("DHA_Lahore"),
    plot_id: str | None = Form(None),
    model_name: str | None = Form(None, description="Optional custom or switched multimodal model."),
    thread_id: str | None = Form(None),
):
    """Scrutinize a multi-file package while preserving every source document for review."""
    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF is required.")
    uploaded = []
    for upload in files:
        if not upload.filename or not upload.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400, detail=f"Only PDF files are supported: {upload.filename or 'unnamed file'}"
            )
        uploaded.append((upload.filename, await upload.read()))

    try:
        logger.info(f"📦 Received multi-file package with {len(uploaded)} files: {[n for n, _ in uploaded]}")
        package_bytes = merge_pdf_documents(uploaded)
        pkg_thread_name = uploaded[0][0] if uploaded else "Package Submission"
        verdict, elapsed = run_submission_package(
            package_bytes,
            authority or "DHA_Lahore",
            model_name=model_name,
            thread_name=pkg_thread_name,
            thread_id=thread_id,
        )
        raise_if_ineligible(verdict)
        case_id = create_case(uploaded, verdict, authority)
        return {
            "status": "SUCCESS",
            "case_id": case_id,
            "filenames": [name for name, _ in uploaded],
            "plot_id": plot_id,
            "elapsed_seconds": elapsed,
            "processing_seconds": elapsed,
            "overall_verdict": verdict.get("overall"),
            "doc_type": verdict.get("doc_type"),
            "verdict": verdict,
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"❌ Package scrutiny failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scrutiny pipeline execution failed: {exc!s}")
