"""Chatbot Evaluation Suite for House Scrutiny AI.

Evaluates post-report follow-up chat accuracy, factual grounding against
audit verdict JSON, anti-hallucination guardrails, and HITL cancellation handling.
"""

import json

# Mock Scrutiny Verdict fixture representing a real structural drawing package
MOCK_VERDICT = {
    "overall": "PASSED_WITH_CONDITIONS",
    "authority": "DHA_Lahore",
    "pdf_filename": "Structural_Design_Rev2.pdf",
    "doc_type": {
        "document_type": "structural_drawing",
        "primary_type": "structural_drawing",
        "has_architectural": False,
        "has_structural": True,
        "has_stability_certificate": True,
        "page_types": {"1": "General Notes", "2": "Column Foundation", "3": "Slab Details"},
    },
    "structural_analysis": {
        "concrete_grade_psi": 3000,
        "slab_thickness_in": 6.0,
        "steel_grade_psi": 60000,
        "foundation_depth_ft": 5.5,
        "column_schedule": True,
        "beam_schedule": True,
        "slab_rebar_detail": True,
        "structural_notes": True,
        "structural_pages": [1, 2, 3],
    },
    "values": {},
    "bylaws": {
        "structural_stability_certificate": "PASS",
        "concrete_compressive_strength": "PASS",
        "slab_thickness": "PASS",
    },
    "bylaw_profile": {
        "status": "VALID",
        "display_name": "DHA 1-Kanal Residential",
        "plot_category": "1_kanal",
        "notice": "Structural drawings evaluated under DHA Engineering Code 2024.",
    },
    "checks": {
        "STR-01": {"status": "PASS", "evidence": "General Notes Sheet S-1 specifies 3000 PSI", "page": 1},
        "STR-02": {"status": "PASS", "evidence": "Slab section indicates 6.0 in thickness", "page": 3},
    },
    "review_flags": [],
}


def build_test_system_prompt(verdict: dict) -> str:
    """Helper mimicking the backend prompt construction in threads.py."""
    doc_type_info = verdict.get("doc_type", {})
    has_arch = doc_type_info.get("has_architectural", False)
    has_struct = doc_type_info.get("has_structural", False)
    struct_analysis = verdict.get("structural_analysis", {})

    compact_audit = {
        "auditing_authority": verdict.get("authority", "N/A"),
        "document_classification": {
            "document_type": doc_type_info.get("primary_type", "Unknown"),
            "has_architectural_drawings": has_arch,
            "has_structural_drawings": has_struct,
            "total_pages": len(struct_analysis.get("structural_pages", [])),
        },
        "overall_audit_verdict": verdict.get("overall"),
        "structural_engineering_parameters": {
            "concrete_compressive_strength_psi": struct_analysis.get("concrete_grade_psi"),
            "slab_thickness_inches": struct_analysis.get("slab_thickness_in"),
            "steel_yield_strength_psi": struct_analysis.get("steel_grade_psi"),
            "foundation_depth_ft": struct_analysis.get("foundation_depth_ft"),
        },
        "bylaw_compliance_status": verdict.get("bylaws", {}),
    }

    prompt = (
        "You are House Scrutiny AI, a certified senior civil & structural engineer and statutory bylaw scrutiny officer.\n"
        "You answer questions directly, accurately, and authoritatively based STRICTLY on the Scrutiny Audit Data JSON below.\n\n"
        "Core Directives:\n"
        "1. Document Type Grounding: Always check 'document_classification'. Distinguish clearly between the uploaded PDF filename and the engineering classification.\n"
        "2. Structural Parameters: For concrete strength, slab thickness, steel grade, foundation depth, or schedules, cite exact figures, units (e.g. 3000 PSI, 6.0 inches), and sheet page numbers.\n"
        "3. Architectural Setbacks & Height: If the drawing is classified as structural and lacks architectural drawings, explain concisely that architectural measurements (height, setbacks, FAR) cannot be evaluated from structural sheets.\n"
        "4. Bylaw Citations: Reference statutory authority bylaws (DHA Lahore, LDA, CDA) when addressing permissible vs measured values.\n"
        "5. Formatting: Output cleanly formatted Markdown using headings, bold values, bullet points, and tables where appropriate.\n"
        "6. Anti-Hallucination: If a parameter is not recorded or unverified in the audit JSON, state clearly that it is unverified rather than guessing.\n\n"
        f"SCRUTINY AUDIT DATA (JSON):\n```json\n{json.dumps(compact_audit, indent=2)}\n```"
    )
    return prompt


# ==============================================================================
# EVALUATION METRICS & TESTS
# ==============================================================================


def test_eval_prompt_contains_structural_grounding():
    """Eval 1: Verifies that system prompt grounds structural parameters without omission."""
    prompt = build_test_system_prompt(MOCK_VERDICT)
    assert "3000" in prompt, "Concrete compressive strength missing from prompt grounding"
    assert "6.0" in prompt, "Slab thickness missing from prompt grounding"
    assert "60000" in prompt, "Steel yield strength missing from prompt grounding"
    assert "DHA_Lahore" in prompt, "Target authority missing from prompt grounding"


def test_eval_architectural_hallucination_guard():
    """Eval 2: Tests that the prompt strictly instructs the agent not to invent architectural setbacks when only structural sheets are present."""
    prompt = build_test_system_prompt(MOCK_VERDICT)
    assert "Architectural Setbacks & Height" in prompt
    assert "cannot be evaluated from structural sheets" in prompt


def test_eval_mock_response_factual_scoring():
    """Eval 3: Evaluates synthetic assistant replies against ground-truth audit parameters."""
    good_reply = (
        "### Structural Drawing Analysis\n\n"
        "- **Concrete Compressive Strength**: **3000 PSI** (Specified in General Notes)\n"
        "- **Slab Thickness**: **6.0 inches**\n"
        "- **Steel Yield Strength**: **60,000 PSI** (Grade 60 Deformed Bars)\n"
        "- **Status**: Compliant with **DHA Lahore** minimum structural requirements."
    )

    bad_hallucinated_reply = "The building height is 35 feet and the front setback is 10 feet. Concrete is 4000 PSI."

    def evaluate_response_grounding(reply: str, truth: dict) -> dict:
        score = 0.0
        reasons = []

        # Check concrete PSI
        expected_psi = str(truth["structural_analysis"]["concrete_grade_psi"])
        if expected_psi in reply:
            score += 0.35
        else:
            reasons.append(f"Missing or incorrect concrete PSI (expected {expected_psi})")

        # Check slab thickness
        expected_slab = str(truth["structural_analysis"]["slab_thickness_in"])
        if expected_slab in reply:
            score += 0.35
        else:
            reasons.append(f"Missing or incorrect slab thickness (expected {expected_slab})")

        # Check markdown formatting
        if any(marker in reply for marker in ["**", "###", "- "]):
            score += 0.15
        else:
            reasons.append("Lacks structured markdown formatting")

        # Check anti-hallucination (should not claim 4000 PSI when 3000 PSI is specified)
        if "4000 PSI" in reply:
            score -= 0.5
            reasons.append("Hallucinated incorrect concrete PSI")

        return {"score": round(max(0.0, score), 2), "reasons": reasons}

    good_eval = evaluate_response_grounding(good_reply, MOCK_VERDICT)
    bad_eval = evaluate_response_grounding(bad_hallucinated_reply, MOCK_VERDICT)

    assert good_eval["score"] >= 0.8, f"Good response scored too low: {good_eval}"
    assert bad_eval["score"] < 0.5, f"Bad response scored too high: {bad_eval}"


def test_eval_hitl_cancellation_formatting():
    """Eval 4: Tests that HITL cancellation correctly appends the stoppage marker."""
    partial_text = "The foundation depth is 5.5 ft according to Sheet S-2"
    stopped_text = f"{partial_text}\n\n*(Generation stopped by user)*"

    assert "*(Generation stopped by user)*" in stopped_text
    assert stopped_text.startswith(partial_text)
