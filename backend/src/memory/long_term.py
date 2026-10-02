"""src/memory/long_term.py - Cross-Thread Scrutiny Knowledge & Submission Memory.

Persists cross-thread engineering records, drawing registry, and municipal precedent.
NOTE: As requested, user preferences are NOT stored in long-term memory; each PDF
scrutiny runs as an independent thread. Long-term memory provides cross-submission
intelligence (past project revisions, historical defect patterns, and thread registry).
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from src.memory.cache import (
    get_cached_chat,
    get_cached_thread,
    get_cached_thread_list,
    invalidate_chat,
    invalidate_thread,
    invalidate_thread_list,
    set_cached_chat,
    set_cached_thread,
    set_cached_thread_list,
)
from src.memory.database import get_db_connection

logger = logging.getLogger(__name__)

# In-memory fallback cache for offline development or disconnected test runs
_LOCAL_THREAD_CACHE: dict[str, dict[str, Any]] = {}
_LOCAL_THREAD_MESSAGES: dict[str, list[dict[str, Any]]] = {}


def save_chat_message(
    thread_id: str,
    sender: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Persists a single chat message (user or assistant) for a thread.

    Writes to the ``thread_messages`` table in Neon PostgreSQL and mirrors
    into the in-memory fallback so chat history survives DB outages within
    the same process lifetime.
    """
    meta = metadata or {}
    now_iso = datetime.now(UTC).isoformat()
    record = {
        "thread_id": thread_id,
        "sender": sender,
        "content": content,
        "metadata": meta,
        "created_at": now_iso,
    }

    # In-memory fallback (short-term within the process)
    _LOCAL_THREAD_MESSAGES.setdefault(thread_id, []).append(record)

    # Invalidate chat cache so next read fetches fresh data from DB
    invalidate_chat(thread_id)

    # Attempt PostgreSQL persistence
    try:
        with get_db_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                    INSERT INTO thread_messages (thread_id, sender, content, metadata)
                    VALUES (%s, %s, %s, %s);
                    """,
                (thread_id, sender, content, json.dumps(meta)),
            )
        logger.debug(f"Chat message saved for thread '{thread_id}' (sender={sender}).")
        return True
    except Exception as exc:
        logger.warning(f"Could not persist chat message to Neon DB ({exc}); cached in memory.")
        return False


def get_chat_messages(
    thread_id: str,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Retrieves ordered chat history for a thread from Neon PostgreSQL.

    Cache-aside: checks Redis first (TTL=20s), falls back to DB on miss.
    Falls back to the in-memory cache if the DB is also unreachable.
    Returns messages in ascending chronological order (oldest first).
    """
    cached = get_cached_chat(thread_id)
    if cached is not None:
        return cached[:limit]

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT message_id, thread_id, sender, content, metadata, created_at
                    FROM thread_messages
                    WHERE thread_id = %s
                    ORDER BY created_at ASC, message_id ASC
                    LIMIT %s;
                    """,
                    (thread_id, limit),
                )
                rows = cur.fetchall()
                messages = []
                for r in rows:
                    messages.append(
                        {
                            "message_id": r[0],
                            "thread_id": r[1],
                            "sender": r[2],
                            "content": r[3],
                            "metadata": r[4] if isinstance(r[4], dict) else {},
                            "created_at": r[5].isoformat() if hasattr(r[5], "isoformat") else str(r[5]),
                        }
                    )
                set_cached_chat(thread_id, messages)
                return messages
    except Exception as exc:
        logger.debug(f"Neon query for thread messages {thread_id} failed ({exc}), using in-memory fallback.")
        return list(_LOCAL_THREAD_MESSAGES.get(thread_id, []))[:limit]


def save_thread_scrutiny(
    thread_id: str,
    thread_name: str,
    pdf_filename: str,
    authority: str,
    verdict: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    processing_time_seconds: float | None = None,
) -> bool:
    """Persists a completed scrutiny thread and its verdict to long-term memory."""
    meta = metadata or {}

    # Extract wall-clock processing time
    proc_time = processing_time_seconds
    if proc_time is None:
        proc_time = verdict.get("processing_seconds") or meta.get("processing_seconds")
    if proc_time is not None:
        try:
            proc_time = float(proc_time)
            verdict["processing_seconds"] = proc_time
        except (ValueError, TypeError):
            proc_time = None

    # Extract key engineering indicators from verdict for indexing
    struct_params = verdict.get("structural_analysis", {}).get("parameters", {})
    concrete_psi = struct_params.get("concrete_grade_psi", {}).get("value")
    if concrete_psi is not None:
        try:
            concrete_psi = float(concrete_psi)
        except (ValueError, TypeError):
            concrete_psi = None

    slab_in = struct_params.get("slab_thickness_in", {}).get("value")
    if slab_in is not None:
        try:
            slab_in = float(slab_in)
        except (ValueError, TypeError):
            slab_in = None

    comp_score = verdict.get("completeness_audit", {}).get("completeness_score_pct")
    if comp_score is not None:
        try:
            comp_score = float(comp_score)
        except (ValueError, TypeError):
            comp_score = None

    overall = verdict.get("overall", "PENDING_VERIFICATION")
    now_iso = datetime.now(UTC).isoformat()

    record = {
        "thread_id": thread_id,
        "thread_name": thread_name,
        "pdf_filename": pdf_filename,
        "authority": authority,
        "overall_verdict": overall,
        "concrete_grade_psi": concrete_psi,
        "slab_thickness_in": slab_in,
        "completeness_score_pct": comp_score,
        "processing_time_seconds": proc_time,
        "created_at": now_iso,
        "updated_at": now_iso,
        "metadata": meta,
        "raw_verdict": verdict,
    }

    # Store in local fallback cache
    _LOCAL_THREAD_CACHE[thread_id] = record

    # Attempt PostgreSQL persistence in Neon DB
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO scrutiny_threads (
                        thread_id, thread_name, pdf_filename, authority,
                        overall_verdict, concrete_grade_psi, slab_thickness_in,
                        completeness_score_pct, processing_time_seconds, metadata, raw_verdict, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (thread_id) DO UPDATE SET
                        thread_name = EXCLUDED.thread_name,
                        overall_verdict = EXCLUDED.overall_verdict,
                        concrete_grade_psi = EXCLUDED.concrete_grade_psi,
                        slab_thickness_in = EXCLUDED.slab_thickness_in,
                        completeness_score_pct = EXCLUDED.completeness_score_pct,
                        processing_time_seconds = COALESCE(EXCLUDED.processing_time_seconds, scrutiny_threads.processing_time_seconds),
                        metadata = EXCLUDED.metadata,
                        raw_verdict = EXCLUDED.raw_verdict,
                        updated_at = CURRENT_TIMESTAMP;
                """,
                    (
                        thread_id,
                        thread_name,
                        pdf_filename,
                        authority,
                        overall,
                        concrete_psi,
                        slab_in,
                        comp_score,
                        proc_time,
                        json.dumps(meta),
                        json.dumps(verdict),
                    ),
                )
        # Invalidate cached thread record and thread list
        invalidate_thread(thread_id)
        invalidate_thread_list()
        logger.info(
            f"Thread '{thread_name}' ({thread_id}) saved to Neon long-term memory with processing time: {proc_time}s."
        )
        return True
    except Exception as exc:
        logger.warning(f"Could not persist thread to Neon DB ({exc}); cached in memory.")
        return False


def list_all_threads(limit: int = 50) -> list[dict[str, Any]]:
    """Retrieves all past scrutiny threads ordered by recency.

    Cache-aside: checks Redis first (TTL=30s), falls back to DB on miss.
    """
    cached = get_cached_thread_list()
    if cached is not None:
        return cached[:limit]

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT thread_id, thread_name, pdf_filename, authority,
                           overall_verdict, completeness_score_pct, processing_time_seconds,
                           created_at, metadata
                    FROM scrutiny_threads
                    ORDER BY created_at DESC
                    LIMIT %s;
                """,
                    (limit,),
                )
                rows = cur.fetchall()
                threads = []
                for r in rows:
                    threads.append(
                        {
                            "thread_id": r[0],
                            "thread_name": r[1],
                            "pdf_filename": r[2],
                            "authority": r[3],
                            "overall_verdict": r[4],
                            "completeness_score_pct": r[5],
                            "processing_time_seconds": float(r[6]) if r[6] is not None else None,
                            "created_at": r[7].isoformat() if hasattr(r[7], "isoformat") else str(r[7]),
                            "metadata": r[8] if isinstance(r[8], dict) else {},
                        }
                    )
                set_cached_thread_list(threads)
                return threads
    except Exception as exc:
        logger.debug(f"Neon query failed ({exc}), returning cached in-memory threads.")
        cached = list(_LOCAL_THREAD_CACHE.values())
        cached.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return cached[:limit]


def get_thread_record(thread_id: str) -> dict[str, Any] | None:
    """Retrieves a thread's full record including verdict, processing time, and metadata.

    Cache-aside: checks Redis first (TTL=5min), falls back to DB on miss.
    """
    cached = get_cached_thread(thread_id)
    if cached is not None:
        return cached

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT thread_id, thread_name, pdf_filename, authority,
                           overall_verdict, concrete_grade_psi, slab_thickness_in,
                           completeness_score_pct, processing_time_seconds, created_at, updated_at,
                           metadata, raw_verdict
                    FROM scrutiny_threads
                    WHERE thread_id = %s;
                """,
                    (thread_id,),
                )
                row = cur.fetchone()
                if row:
                    raw_verdict = row[12] if isinstance(row[12], dict) else {}
                    proc_seconds = float(row[8]) if row[8] is not None else None
                    if proc_seconds is not None and "processing_seconds" not in raw_verdict:
                        raw_verdict["processing_seconds"] = proc_seconds

                    record = {
                        "thread_id": row[0],
                        "thread_name": row[1],
                        "pdf_filename": row[2],
                        "authority": row[3],
                        "overall_verdict": row[4],
                        "concrete_grade_psi": row[5],
                        "slab_thickness_in": row[6],
                        "completeness_score_pct": row[7],
                        "processing_time_seconds": proc_seconds,
                        "created_at": row[9].isoformat() if hasattr(row[9], "isoformat") else str(row[9]),
                        "updated_at": row[10].isoformat() if hasattr(row[10], "isoformat") else str(row[10]),
                        "metadata": row[11] if isinstance(row[11], dict) else {},
                        "raw_verdict": raw_verdict,
                    }
                    set_cached_thread(thread_id, record)
                    return record
    except Exception as exc:
        logger.debug(f"Neon query for thread {thread_id} failed ({exc}).")

    # Fallback to local memory cache
    return _LOCAL_THREAD_CACHE.get(thread_id)


def delete_thread(thread_id: str) -> bool:
    """Deletes a thread record from long-term memory and invalidates its cache entries."""
    _LOCAL_THREAD_CACHE.pop(thread_id, None)

    # Evict from Redis before DB delete
    invalidate_thread(thread_id)
    invalidate_chat(thread_id)

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM scrutiny_threads WHERE thread_id = %s;", (thread_id,))
        invalidate_thread_list()
        return True
    except Exception as exc:
        logger.warning(f"Failed to delete thread {thread_id} from Neon DB: {exc}")
        return False


def find_related_submissions(plot_or_project_name: str, limit: int = 5) -> list[dict[str, Any]]:
    """Cross-thread intelligence: searches past submissions for the same project or plot."""
    if not plot_or_project_name:
        return []

    pattern = f"%{plot_or_project_name.strip()}%"
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT thread_id, thread_name, authority, overall_verdict,
                           created_at, completeness_score_pct
                    FROM scrutiny_threads
                    WHERE thread_name ILIKE %s OR pdf_filename ILIKE %s
                    ORDER BY created_at DESC
                    LIMIT %s;
                """,
                    (pattern, pattern, limit),
                )
                results = []
                for r in cur.fetchall():
                    results.append(
                        {
                            "thread_id": r[0],
                            "thread_name": r[1],
                            "authority": r[2],
                            "overall_verdict": r[3],
                            "created_at": r[4].isoformat() if hasattr(r[4], "isoformat") else str(r[4]),
                            "completeness_score_pct": r[5],
                        }
                    )
                return results
    except Exception as exc:
        logger.debug(f"Cross-submission search failed ({exc}).")
        results = []
        for t in _LOCAL_THREAD_CACHE.values():
            if plot_or_project_name.lower() in t["thread_name"].lower():
                results.append(t)
        return results[:limit]
