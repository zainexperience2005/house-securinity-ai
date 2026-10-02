"""tests/test_memory_short_term.py - Unit tests for LangGraph Short-Term Checkpoint Memory.

Tests:
1. Thread ID generation: clean naming derived from PDF filename with unique UUID suffix.
2. Checkpointer initialization: returns a valid BaseCheckpointSaver (PostgresSaver / InMemorySaver).
3. Thread isolation: verifies that separate threads (different PDFs) maintain strictly isolated states.
4. Intermediate checkpointing: verifies node-level state capture and retrieval via get_thread_state.
5. Checkpoint history traversal: verifies chronological state snapshot tracking.
"""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from src.memory.short_term import (
    generate_thread_id,
    get_checkpointer,
    get_thread_checkpoint_history,
    get_thread_state,
)


class DummyState(TypedDict):
    step_history: list
    pdf_name: str
    verdict: str


def node_step_a(state: DummyState) -> dict:
    hist = list(state.get("step_history", []))
    hist.append("step_a")
    return {"step_history": hist}


def node_step_b(state: DummyState) -> dict:
    hist = list(state.get("step_history", []))
    hist.append("step_b")
    return {"step_history": hist, "verdict": "COMPLETE"}


def build_test_graph(checkpointer):
    g = StateGraph(DummyState)
    g.add_node("step_a", node_step_a)
    g.add_node("step_b", node_step_b)
    g.add_edge(START, "step_a")
    g.add_edge("step_a", "step_b")
    g.add_edge("step_b", END)
    return g.compile(checkpointer=checkpointer)


def test_generate_thread_id_from_pdf():
    """Verifies that thread IDs are properly sanitized and named according to the PDF drawing."""
    tid1 = generate_thread_id("93-B OPF GROUND FLOOR SLAB STR DWG.pdf")
    assert tid1.startswith("thread_93_B_OPF_GROUND_FLOOR_SLAB_STR_DWG")
    assert len(tid1) > 20

    tid2 = generate_thread_id("AMBER MOSQUE AT LAHORE STR DWG (1).pdf")
    assert "AMBER_MOSQUE" in tid2

    # None or empty fallback
    tid3 = generate_thread_id(None)
    assert tid3.startswith("thread_submission_")

    # Uniqueness across calls
    tid4 = generate_thread_id("drawing.pdf")
    tid5 = generate_thread_id("drawing.pdf")
    assert tid4 != tid5


def test_checkpointer_instance():
    """Verifies that get_checkpointer returns an active, valid BaseCheckpointSaver."""
    cp = get_checkpointer(force_memory=True)
    assert isinstance(cp, InMemorySaver)


def test_thread_state_isolation():
    """Verifies that 1 PDF scrutiny = 1 thread and two threads never leak state into each other."""
    cp = InMemorySaver()
    graph = build_test_graph(cp)

    thread_alpha = generate_thread_id("Drawing_Alpha.pdf")
    thread_beta = generate_thread_id("Drawing_Beta.pdf")

    config_alpha = {"configurable": {"thread_id": thread_alpha}}
    config_beta = {"configurable": {"thread_id": thread_beta}}

    # Run thread Alpha
    graph.invoke({"step_history": ["init_alpha"], "pdf_name": "Alpha.pdf", "verdict": "PENDING"}, config_alpha)

    # Run thread Beta
    graph.invoke({"step_history": ["init_beta"], "pdf_name": "Beta.pdf", "verdict": "PENDING"}, config_beta)

    # Inspect checkpointed state for each thread
    state_alpha = get_thread_state(graph, thread_alpha)
    state_beta = get_thread_state(graph, thread_beta)

    assert state_alpha is not None
    assert state_beta is not None

    # Verify completely isolated state values
    assert state_alpha["pdf_name"] == "Alpha.pdf"
    assert state_alpha["step_history"] == ["init_alpha", "step_a", "step_b"]

    assert state_beta["pdf_name"] == "Beta.pdf"
    assert state_beta["step_history"] == ["init_beta", "step_a", "step_b"]


def test_checkpoint_history_traversal():
    """Verifies that checkpoint history captures intermediate execution steps."""
    cp = InMemorySaver()
    graph = build_test_graph(cp)
    thread_id = generate_thread_id("Drawing_History_Test.pdf")
    config = {"configurable": {"thread_id": thread_id}}

    graph.invoke({"step_history": [], "pdf_name": "HistoryTest.pdf", "verdict": "PENDING"}, config)

    history = get_thread_checkpoint_history(graph, thread_id)
    assert len(history) >= 2  # multiple snapshots created during graph execution
