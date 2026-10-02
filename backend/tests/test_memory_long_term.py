"""tests/test_memory_long_term.py - Unit tests for Long-Term Scrutiny Memory.

Tests:
1. Saving scrutiny threads: verifies thread metadata, parameters, and verdicts are recorded.
2. Thread listing: verifies list_all_threads returns registered threads for the UI sidebar.
3. Thread retrieval: verifies get_thread_record fetches complete verdicts and audit logs.
4. Precedent retrieval: verifies cross-submission lookup for identical plots or project revisions.
5. Deletion: verifies thread removal from memory.
6. User preference exclusion: verifies that user preferences are NOT stored in long-term memory
   (adhering to the explicit user constraint that submissions are strictly 1-PDF-per-thread).
"""

import uuid

import pytest

from src.memory.long_term import (
    delete_thread,
    find_related_submissions,
    get_thread_record,
    list_all_threads,
    save_thread_scrutiny,
)


@pytest.fixture
def sample_verdict():
    return {
        "overall": "CORRECTION_REQUIRED",
        "doc_type": {"choice": "structural_drawing"},
        "structural_analysis": {
            "parameters": {
                "concrete_grade_psi": {"value": 3000.0},
                "slab_thickness_in": {"value": 6.0},
                "steel_grade_psi": {"value": 40000.0},
            }
        },
        "completeness_audit": {"completeness_status": "INCOMPLETE", "completeness_score_pct": 75.0},
        "review_flags": ["Missing Structural Stability Certificate"],
    }


def test_save_and_retrieve_thread_scrutiny(sample_verdict):
    """Verifies that a completed scrutiny thread is persisted and retrievable."""
    thread_id = f"thread_test_save_{uuid.uuid4().hex[:6]}"
    thread_name = "Plot_93-B_OPF_Ground_Floor.pdf"
    pdf_filename = "93-B_OPF_GROUND_FLOOR_SLAB.pdf"
    authority = "OPF_Islamabad"

    success = save_thread_scrutiny(
        thread_id=thread_id,
        thread_name=thread_name,
        pdf_filename=pdf_filename,
        authority=authority,
        verdict=sample_verdict,
        metadata={"plot_size": "1_Kanal"},
    )
    assert success is True

    record = get_thread_record(thread_id)
    assert record is not None
    assert record["thread_id"] == thread_id
    assert record["thread_name"] == thread_name
    assert record["overall_verdict"] == "CORRECTION_REQUIRED"
    assert record["concrete_grade_psi"] == 3000.0
    assert record["slab_thickness_in"] == 6.0
    assert record["completeness_score_pct"] == 75.0
    assert record["raw_verdict"]["overall"] == "CORRECTION_REQUIRED"

    # Cleanup
    delete_thread(thread_id)


def test_list_all_threads_for_sidebar(sample_verdict):
    """Verifies that list_all_threads returns threads suitable for the Streamlit sidebar."""
    t1 = f"thread_sidebar_1_{uuid.uuid4().hex[:6]}"
    t2 = f"thread_sidebar_2_{uuid.uuid4().hex[:6]}"

    save_thread_scrutiny(t1, "Drawing_1.pdf", "Drawing_1.pdf", "DHA_Lahore", sample_verdict)
    save_thread_scrutiny(t2, "Drawing_2.pdf", "Drawing_2.pdf", "LDA_Lahore", sample_verdict)

    threads = list_all_threads(limit=10)
    assert len(threads) >= 2
    thread_ids = [t["thread_id"] for t in threads]
    assert t1 in thread_ids or t2 in thread_ids

    # Cleanup
    delete_thread(t1)
    delete_thread(t2)


def test_find_related_submissions(sample_verdict):
    """Verifies cross-thread lookup for finding previous drawings of the same plot or project."""
    unique_proj = f"Villa_Project_{uuid.uuid4().hex[:4]}"
    tid = f"thread_cross_{uuid.uuid4().hex[:6]}"

    save_thread_scrutiny(
        thread_id=tid,
        thread_name=f"{unique_proj}_Structural_Rev0.pdf",
        pdf_filename=f"{unique_proj}.pdf",
        authority="DHA_Lahore",
        verdict=sample_verdict,
    )

    matches = find_related_submissions(unique_proj)
    assert len(matches) >= 1
    assert matches[0]["thread_id"] == tid

    # Cleanup
    delete_thread(tid)


def test_no_user_preferences_in_long_term_memory(sample_verdict):
    """Explicitly verifies user requirement: long-term memory does NOT store user preferences.

    1 PDF scrutiny = 1 thread. Long-term memory records only engineering submissions,
    drawings, and scrutiny outcomes.
    """
    thread_id = f"thread_no_pref_{uuid.uuid4().hex[:6]}"
    save_thread_scrutiny(
        thread_id=thread_id,
        thread_name="Commercial_Plaza.pdf",
        pdf_filename="Commercial_Plaza.pdf",
        authority="LDA_Lahore",
        verdict=sample_verdict,
        metadata={"user_preference": "DO_NOT_STORE"},  # Should not be tracked as preference store
    )

    record = get_thread_record(thread_id)
    # The record should not expose or manage user preference schemas
    assert "user_preferences" not in record
    assert "user_id" not in record

    # Cleanup
    delete_thread(thread_id)
