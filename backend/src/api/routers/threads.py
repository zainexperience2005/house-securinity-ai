"""Scrutiny threads, persistent conversation history, and real-time streaming chat with HITL cancellation."""

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from openai import OpenAI

from src.api.schemas import ChatMessageRequest
from src.config.settings import settings
from src.memory.long_term import (
    delete_thread,
    get_chat_messages,
    get_thread_record,
    list_all_threads,
    save_chat_message,
)

logger = logging.getLogger("house_scrutiny.api")

router = APIRouter(prefix="/api/v1/threads", tags=["Scrutiny Threads & Chat"])


@router.get("", summary="List recent scrutiny threads")
def list_threads_endpoint(limit: int = 50):
    """Retrieve historical scrutiny threads ordered by recency."""
    threads = list_all_threads(limit=limit)
    return {"count": len(threads), "threads": threads}


@router.get("/{thread_id}", summary="Get thread verdict and details")
def get_thread_endpoint(thread_id: str):
    """Retrieve full verdict and metadata for a specific scrutiny thread."""
    thread = get_thread_record(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found.")
    return thread


@router.delete("/{thread_id}", summary="Delete scrutiny thread")
def delete_thread_endpoint(thread_id: str):
    """Delete a scrutiny thread from persistent memory."""
    ok = delete_thread(thread_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Thread not found or could not be deleted.")
    return {"status": "SUCCESS", "message": f"Thread '{thread_id}' deleted."}


@router.get("/{thread_id}/messages", summary="Get thread chat message history")
def get_thread_messages_endpoint(thread_id: str, limit: int = 200):
    """Retrieve saved follow-up chat history for a scrutiny thread (oldest-first)."""
    messages = get_chat_messages(thread_id, limit=limit)
    return {"thread_id": thread_id, "count": len(messages), "messages": messages}


@router.post("/{thread_id}/chat", summary="Chat with AI auditor (Streaming SSE with HITL cancellation)")
async def send_thread_chat_message(thread_id: str, body: ChatMessageRequest, request: Request):
    """Send a follow-up question about a scrutiny thread and stream an AI-powered answer.

    Supports Human-in-the-Loop (HITL) cancellation: if the client disconnects or aborts,
    streaming stops immediately and partial tokens are recorded cleanly.
    """
    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    # Retrieve thread context (verdict) from long-term memory
    thread_record = get_thread_record(thread_id)
    verdict_context = ""

    if thread_record and thread_record.get("raw_verdict"):
        raw_v = thread_record["raw_verdict"]
        v = raw_v.get("verdict", raw_v)

        doc_type_info = v.get("doc_type", {})
        primary_doc_type = (
            doc_type_info.get("primary_type")
            or doc_type_info.get("choice")
            or (
                "structural_drawing"
                if doc_type_info.get("has_structural")
                else "architectural_drawing"
                if doc_type_info.get("has_architectural")
                else "Unknown"
            )
        )
        has_arch = doc_type_info.get("has_architectural", False)
        has_struct = doc_type_info.get("has_structural", False)
        has_cert = doc_type_info.get("has_stability_certificate", False)

        struct_analysis = v.get("structural_analysis", {})
        struct_params = struct_analysis.get("parameters", {})
        structural_data = {
            "is_structural_submission": has_struct,
            "concrete_compressive_strength_psi": (
                thread_record.get("concrete_grade_psi")
                or struct_analysis.get("concrete_grade_psi")
                or (struct_params.get("concrete_grade_psi") or {}).get("value")
            ),
            "slab_thickness_inches": (
                thread_record.get("slab_thickness_in")
                or struct_analysis.get("slab_thickness_in")
                or (struct_params.get("slab_thickness_in") or {}).get("value")
            ),
            "steel_yield_strength_psi": (
                struct_analysis.get("steel_grade_psi") or (struct_params.get("steel_grade_psi") or {}).get("value")
            ),
            "foundation_depth_ft": (
                struct_analysis.get("foundation_depth_ft")
                or (struct_params.get("foundation_depth_ft") or {}).get("value")
            ),
            "column_schedule_present": bool(struct_analysis.get("column_schedule")),
            "beam_schedule_present": bool(struct_analysis.get("beam_schedule")),
            "slab_rebar_detail_present": bool(struct_analysis.get("slab_rebar_detail")),
            "structural_notes_present": bool(struct_analysis.get("structural_notes")),
            "structural_pages": struct_analysis.get("structural_pages", []),
        }

        compact_audit = {
            "thread_id": thread_id,
            "file_name": thread_record.get("pdf_filename") or thread_record.get("thread_name", "N/A"),
            "auditing_authority": thread_record.get("authority", "N/A"),
            "document_classification": {
                "document_type": primary_doc_type,
                "has_architectural_drawings": has_arch,
                "has_structural_drawings": has_struct,
                "has_stability_certificate": has_cert,
                "total_pages": len(doc_type_info.get("page_types", {}))
                or len(struct_analysis.get("structural_pages", [])),
                "notice": v.get("bylaw_profile", {}).get("notice", ""),
            },
            "overall_audit_verdict": thread_record.get("overall_verdict", v.get("overall", "N/A")),
            "structural_engineering_parameters": structural_data,
            "architectural_design_values": v.get("values", {}),
            "bylaw_compliance_status": {k: str(val) for k, val in (v.get("bylaws", {}) or {}).items()}
            if isinstance(v.get("bylaws"), dict)
            else {},
            "bylaw_profile": {
                "status": v.get("bylaw_profile", {}).get("status"),
                "display_name": v.get("bylaw_profile", {}).get("display_name"),
                "plot_category": v.get("bylaw_profile", {}).get("plot_category"),
                "notice": v.get("bylaw_profile", {}).get("notice"),
            },
            "checklist_highlights": {
                cid: {
                    "status": c.get("status"),
                    "evidence": c.get("evidence"),
                    "page": c.get("page"),
                    "note": c.get("note"),
                }
                for cid, c in (v.get("checks", {}) or {}).items()
                if c.get("status") in ("PASS", "CORRECTION_REQUIRED", "VIOLATION", "PENDING")
            },
            "audit_flags_and_deficiencies": v.get("review_flags", [])[:10],
        }

        verdict_context = json.dumps(compact_audit, indent=2, default=str)
    else:
        verdict_context = f'{{"thread_id": "{thread_id}", "status": "No audit verdict available in memory"}}'

    all_prior_messages = get_chat_messages(thread_id, limit=50)
    recent_messages = all_prior_messages[-6:] if len(all_prior_messages) > 6 else all_prior_messages
    conversation_history = []
    for m in recent_messages:
        content = (m.get("content") or "").strip()
        if not content:
            continue
        role = "user" if m.get("sender") == "user" else "assistant"
        conversation_history.append({"role": role, "content": content})

    system_prompt = (
        "You are House Scrutiny AI, a certified senior civil & structural engineer and statutory bylaw scrutiny officer.\n"
        "You answer questions directly, accurately, and authoritatively based STRICTLY on the Scrutiny Audit Data JSON below.\n\n"
        "Core Directives:\n"
        "1. Document Type Grounding: Always check 'document_classification'. Distinguish clearly between the uploaded PDF filename and the engineering classification.\n"
        "2. Structural Parameters: For concrete strength, slab thickness, steel grade, foundation depth, or schedules, cite exact figures, units (e.g. 3000 PSI, 6.0 inches), and sheet page numbers.\n"
        "3. Architectural Setbacks & Height: If the drawing is classified as structural and lacks architectural drawings, explain concisely that architectural measurements (height, setbacks, FAR) cannot be evaluated from structural sheets.\n"
        "4. Bylaw Citations: Reference statutory authority bylaws (DHA Lahore, LDA, CDA) when addressing permissible vs measured values.\n"
        "5. Formatting: Output cleanly formatted Markdown using headings, bold values, bullet points, and tables where appropriate.\n"
        "6. Anti-Hallucination: If a parameter is not recorded or unverified in the audit JSON, state clearly that it is unverified rather than guessing.\n\n"
        f"SCRUTINY AUDIT DATA (JSON):\n```json\n{verdict_context}\n```"
    )

    save_chat_message(thread_id, sender="user", content=body.message.strip())

    requested_model = body.model or settings.openai_model
    chat_model = requested_model
    if chat_model in ("gpt-5-mini", "gpt-5", "o1", "o3-mini"):
        chat_model = "gpt-4o-mini"

    messages_payload = [
        {"role": "system", "content": system_prompt},
        *conversation_history,
        {"role": "user", "content": body.message.strip()},
    ]

    client = OpenAI(api_key=settings.openai_api_key)

    async def event_generator():
        collected_reply = []
        stopped_early = False
        try:
            stream = client.chat.completions.create(
                model=chat_model,
                messages=messages_payload,
                max_tokens=1024,
                temperature=0.2,
                stream=True,
            )
            for chunk in stream:
                # Check for HITL client cancellation / disconnection
                if await request.is_disconnected():
                    logger.info(f"🛑 [HITL] Client stopped chat generation for thread {thread_id}")
                    stopped_early = True
                    break

                delta = chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta else None
                if delta:
                    collected_reply.append(delta)
                    yield f"data: {json.dumps({'delta': delta, 'done': False})}\n\n"
                    await asyncio.sleep(0.001)

            full_text = "".join(collected_reply).strip()
            if stopped_early:
                full_text += "\n\n*(Generation stopped by user)*"

            if not full_text:
                full_text = "I reviewed the audit report JSON, but no matching information was found for your query."
                yield f"data: {json.dumps({'delta': full_text, 'done': False})}\n\n"

            save_chat_message(
                thread_id,
                sender="assistant",
                content=full_text,
                metadata={"model": chat_model, "stopped_early": stopped_early},
            )

            yield f"data: {json.dumps({'done': True, 'model': chat_model, 'reply': full_text, 'stopped_early': stopped_early})}\n\n"

        except asyncio.CancelledError:
            logger.info(f"🛑 [HITL] Async task cancelled for thread {thread_id}")
        except Exception as exc:
            logger.error(f"Chat stream failed for thread {thread_id}: {exc}", exc_info=True)
            yield f"data: {json.dumps({'error': str(exc), 'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
