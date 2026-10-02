"""evals/test_evals.py - Pytest & DeepEval integration test suite for House Scrutiny Agent."""
import pytest
from deepeval import assert_test
from evals.dataset import build_deepeval_dataset
from evals.metrics import (
    # Deterministic Engineering & Schema Metrics
    schema_validity_metric,
    structural_numerical_tolerance_metric,
    plot_dimensions_tolerance_metric,
    deficiency_recall_metric,
    # Safety, Life-Safety & Guardrails
    structural_safety_guardrail_metric,
    false_approval_penalty_metric,
    drawing_faithfulness_metric,
    toxicity_metric,
    bias_metric,
    adversarial_injection_defense_metric,
    # Domain & Regulatory Scrutiny
    bylaw_zoning_compliance_metric,
    classification_completeness_metric,
    title_block_precision_metric,
    # Memory & State Alignment
    thread_isolation_metric,
    long_term_memory_metric,
)

# Build test cases from golden dataset
dataset = build_deepeval_dataset()


# ==============================================================================
# 1. Deterministic Accuracy & Engineering Precision Tests
# ==============================================================================
@pytest.mark.parametrize("test_case", dataset.test_cases)
def test_schema_validity_and_completeness(test_case):
    """Verifies that generated scrutiny verdict contains all required architectural/structural keys."""
    assert_test(test_case, [schema_validity_metric])


@pytest.mark.parametrize("test_case", dataset.test_cases)
def test_structural_numerical_tolerance(test_case):
    """Verifies that extracted structural numbers (PSI, inches) match engineering tolerances."""
    assert_test(test_case, [structural_numerical_tolerance_metric])


@pytest.mark.parametrize("test_case", dataset.test_cases)
def test_plot_dimensions_and_setbacks(test_case):
    """Verifies plot dimensions and setback measurements against permissible tolerances."""
    assert_test(test_case, [plot_dimensions_tolerance_metric])


@pytest.mark.parametrize("test_case", dataset.test_cases)
def test_deficiency_and_omission_recall(test_case):
    """Ensures missing structural sheets, certificates, or schedules are accurately flagged."""
    assert_test(test_case, [deficiency_recall_metric])


# ==============================================================================
# 2. Safety, Life-Safety Guardrails & Alignment Tests
# ==============================================================================
@pytest.mark.parametrize("test_case", dataset.test_cases)
def test_structural_safety_guardrails(test_case):
    """Verifies life-safety guardrails: missing stability certificates or critical deficits must not pass."""
    assert_test(test_case, [structural_safety_guardrail_metric])


@pytest.mark.parametrize("test_case", dataset.test_cases)
def test_false_approval_penalty(test_case):
    """Zero tolerance for false approvals: non-compliant or deficient submissions must be rejected."""
    assert_test(test_case, [false_approval_penalty_metric])


@pytest.mark.parametrize("test_case", dataset.test_cases)
def test_drawing_faithfulness_and_hallucination(test_case):
    """Verifies that extracted numbers and claims are grounded in CAD text without hallucination."""
    assert_test(test_case, [drawing_faithfulness_metric])


@pytest.mark.parametrize("test_case", dataset.test_cases)
def test_toxicity_guardrail(test_case):
    """Verifies that scrutiny verdict contains strictly professional, non-toxic engineering language."""
    assert_test(test_case, [toxicity_metric])


@pytest.mark.parametrize("test_case", dataset.test_cases)
def test_bias_guardrail(test_case):
    """Verifies objective, impartial engineering review without discriminatory bias."""
    assert_test(test_case, [bias_metric])


@pytest.mark.parametrize("test_case", dataset.test_cases)
def test_adversarial_injection_defense(test_case):
    """Verifies pipeline defense against adversarial prompt injections embedded in CAD text."""
    assert_test(test_case, [adversarial_injection_defense_metric])


# ==============================================================================
# 3. Domain & Regulatory Compliance Tests
# ==============================================================================
@pytest.mark.parametrize("test_case", dataset.test_cases)
def test_document_classification_accuracy(test_case):
    """Evaluates classification accuracy of drawing discipline (architectural, structural, composite)."""
    assert_test(test_case, [classification_completeness_metric])


@pytest.mark.parametrize("test_case", dataset.test_cases)
def test_bylaw_zoning_compliance(test_case):
    """Evaluates adherence to municipal building bylaws (FAR, ground coverage, height, setbacks)."""
    assert_test(test_case, [bylaw_zoning_compliance_metric])


@pytest.mark.parametrize("test_case", dataset.test_cases)
def test_title_block_precision(test_case):
    """Evaluates precision of title block metadata extraction, project title, and sheet tracking."""
    assert_test(test_case, [title_block_precision_metric])


# ==============================================================================
# 4. Short-Term & Long-Term Memory Alignment Tests
# ==============================================================================
@pytest.mark.parametrize("test_case", dataset.test_cases)
def test_thread_isolation_short_term(test_case):
    """Verifies that 1 PDF scrutiny = 1 isolated thread without state cross-contamination."""
    assert_test(test_case, [thread_isolation_metric])


@pytest.mark.parametrize("test_case", dataset.test_cases)
def test_long_term_memory_persistence(test_case):
    """Verifies long-term submission record structure while ensuring zero user preferences are stored."""
    assert_test(test_case, [long_term_memory_metric])

