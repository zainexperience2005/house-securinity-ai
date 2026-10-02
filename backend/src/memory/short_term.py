"""src/memory/short_term.py - Short-Term Thread-Scoped Checkpoint Memory.

Manages LangGraph checkpointers backed by Neon PostgreSQL (with InMemorySaver fallback).
Each PDF scrutiny execution runs in its own dedicated, isolated thread_id.
Intermediate states across nodes (ingest -> gate -> crop -> extract -> judge -> report)
are persisted in PostgreSQL checkpoints, enabling failure recovery, state inspection,
and resumption.
"""

import logging
import os
import re
import uuid
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from src.memory.database import get_database_url

logger = logging.getLogger(__name__)

# Cached checkpointer instance
_GLOBAL_CHECKPOINTER: BaseCheckpointSaver | None = None


def generate_thread_id(pdf_name: str | None = None) -> str:
    """Generates a clean, identifiable thread ID named after the PDF drawing.

    Format: thread_{clean_pdf_name}_{short_uuid}
    Example: thread_93_B_OPF_GROUND_FLOOR_SLAB_STR_DWG_a1b2c3d4
    """
    clean_prefix = "submission"
    if pdf_name:
        # Strip directory and extension
        base = os.path.basename(pdf_name)
        base_no_ext, _ = os.path.splitext(base)
        # Normalize non-alphanumeric chars to underscore
        base_clean = re.sub(r"[^\w]+", "_", base_no_ext).strip("_")
        clean_prefix = base_clean[:40] if base_clean else "drawing"

    unique_suffix = uuid.uuid4().hex[:8]
    return f"thread_{clean_prefix}_{unique_suffix}"


def get_checkpointer(force_memory: bool = False) -> BaseCheckpointSaver:
    """Returns a production PostgreSQL checkpointer connected to Neon DB.

    If force_memory=True or if the PostgreSQL connection is unreachable,
    gracefully falls back to an InMemorySaver for offline testing or unit runs.
    """
    global _GLOBAL_CHECKPOINTER
    if force_memory:
        return InMemorySaver()

    if _GLOBAL_CHECKPOINTER is not None:
        return _GLOBAL_CHECKPOINTER

    db_url = get_database_url()
    try:
        from langgraph.checkpoint.postgres import PostgresSaver

        # Initialize and setup checkpointer tables if not already present
        saver = PostgresSaver.from_conn_string(db_url)
        saver.setup()
        _GLOBAL_CHECKPOINTER = saver
        logger.info("Initialized LangGraph PostgresSaver backed by Neon DB.")
        return saver
    except Exception as exc:
        logger.warning(f"Failed to connect PostgresSaver to Neon DB ({exc}). Falling back to InMemorySaver.")
        fallback = InMemorySaver()
        _GLOBAL_CHECKPOINTER = fallback
        return fallback


def get_thread_state(graph: Any, thread_id: str) -> dict[str, Any] | None:
    """Retrieves the latest checkpointed state for a given thread_id."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state_snapshot = graph.get_state(config)
        if state_snapshot and state_snapshot.values:
            return state_snapshot.values
        return None
    except Exception as exc:
        logger.debug(f"Could not retrieve state for thread {thread_id}: {exc}")
        return None


def get_thread_checkpoint_history(graph: Any, thread_id: str) -> list[dict[str, Any]]:
    """Retrieves chronological checkpoint steps for a given thread_id."""
    config = {"configurable": {"thread_id": thread_id}}
    history = []
    try:
        for snapshot in graph.get_state_history(config):
            history.append(
                {
                    "checkpoint_id": getattr(snapshot.config.get("configurable", {}), "checkpoint_id", None),
                    "next": snapshot.next,
                    "values_keys": list(snapshot.values.keys()) if snapshot.values else [],
                    "created_at": getattr(snapshot, "created_at", None),
                }
            )
    except Exception as exc:
        logger.debug(f"Error fetching checkpoint history for thread {thread_id}: {exc}")
    return history
