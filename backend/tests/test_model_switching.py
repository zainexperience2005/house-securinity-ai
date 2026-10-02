"""tests/test_model_switching.py - Unit & Integration Tests for AI Model Switching.

Tests:
1. Neon PostgreSQL ai_models schema initialization and initial model seeding.
2. Multimodal capability verification (both vision and text capacity).
3. Provider listing and filtering.
4. Adding custom models and custom providers dynamically.
5. Setting default models.
6. Exact pricing lookup and token cost calculations.
7. Integration with pipeline reporting (n_report).
"""

import pytest

from src.memory.models_store import (
    INITIAL_MULTIMODAL_MODELS,
    add_model,
    delete_model,
    get_default_model,
    get_model,
    init_models_table,
    list_models,
    list_providers,
    set_default_model,
)
from src.pipeline.nodes import n_report


def test_initial_models_have_vision_and_text():
    """All seeded models must have both vision and text capability."""
    for m in INITIAL_MULTIMODAL_MODELS:
        assert m["supports_vision"] is True, f"Model {m['model_id']} missing vision capacity"
        assert m["supports_text"] is True, f"Model {m['model_id']} missing text capacity"
        assert m["input_price_per_1m"] >= 0.0
        assert m["output_price_per_1m"] >= 0.0
        assert m["provider"] in {"OpenAI", "Google", "Anthropic", "Groq / Meta", "Mistral"}


def test_init_models_table_and_seeding():
    """Tests initializing the table and seeding the models."""
    ok = init_models_table()
    assert ok is True

    models = list_models(only_active=True, only_vision=True)
    assert len(models) >= len(INITIAL_MULTIMODAL_MODELS)

    model_ids = {m["model_id"] for m in models}
    assert "gpt-4o" in model_ids
    assert "gemini-1.5-flash" in model_ids
    assert "claude-3-5-sonnet-20241022" in model_ids


def test_list_providers():
    """Tests retrieving unique provider names."""
    providers = list_providers()
    assert "OpenAI" in providers
    assert "Google" in providers
    assert "Anthropic" in providers


def test_get_model_pricing():
    """Tests getting exact pricing for a known model."""
    gpt4o = get_model("gpt-4o")
    assert gpt4o is not None
    assert gpt4o["provider"] == "OpenAI"
    assert gpt4o["input_price_per_1m"] == 2.50
    assert gpt4o["output_price_per_1m"] == 10.00
    assert gpt4o["supports_vision"] is True

    gemini = get_model("gemini-1.5-flash")
    assert gemini is not None
    assert gemini["provider"] == "Google"
    assert gemini["input_price_per_1m"] == 0.075


def test_add_custom_model_and_new_provider():
    """Tests adding a user-defined custom provider and model."""
    custom_prov = "CustomAI-Labs"
    custom_id = "test-custom-vision-v1"
    custom_name = "Custom Vision Model V1"

    # Add model
    added = add_model(
        provider=custom_prov,
        model_id=custom_id,
        model_name=custom_name,
        input_price_per_1m=1.20,
        output_price_per_1m=4.80,
        supports_vision=True,
        supports_text=True,
        context_window=64000,
        is_default=False,
    )
    assert added is True

    # Verify retrieval
    m = get_model(custom_id)
    assert m is not None
    assert m["provider"] == custom_prov
    assert m["model_id"] == custom_id
    assert m["input_price_per_1m"] == 1.20
    assert m["output_price_per_1m"] == 4.80
    assert m["context_window"] == 64000

    # Clean up
    delete_model(custom_id)


def test_add_model_validation():
    """Tests that invalid inputs raise ValueError."""
    with pytest.raises(ValueError):
        add_model(provider="", model_id="foo", model_name="bar", input_price_per_1m=1.0, output_price_per_1m=1.0)
    with pytest.raises(ValueError):
        add_model(provider="test", model_id="", model_name="bar", input_price_per_1m=1.0, output_price_per_1m=1.0)


def test_set_default_model():
    """Tests changing default model designation."""
    set_default_model("gpt-4o-mini")
    default_m = get_default_model()
    assert default_m["model_id"] == "gpt-4o-mini"

    # Reset back to gpt-4o
    set_default_model("gpt-4o")
    reset_m = get_default_model()
    assert reset_m["model_id"] == "gpt-4o"


def test_n_report_uses_active_model_and_pricing():
    """Tests that n_report accurately calculates costs based on active_model."""
    # State with custom active model
    state = {
        "active_model": "gemini-1.5-flash",
        "doc_type": {"has_architectural": True},
        "pages": [{"page_number": 1, "text": "sample text", "dimensions": {"width": 800, "height": 600}}],
        "extraction": {
            "values": [],
            "structural_values": [],
            "observations": [],
            "flags": [],
        },
        "openai_usage": {
            "input_tokens": 10000,
            "output_tokens": 2000,
            "total_tokens": 12000,
        },
        "jev_gate_usage": {"input_tokens": 100, "output_tokens": 10},
        "jev_judge_usage": {"input_tokens": 200, "output_tokens": 20},
    }

    res = n_report(state)
    verdict = res["verdict"]

    assert verdict["active_model"] == "gemini-1.5-flash"
    assert verdict["model_provider"] == "Google"

    metrics = verdict["token_metrics"]["openai"]
    assert "Google" in metrics["provider"]
    assert metrics["input_tokens"] == 10000
    assert metrics["output_tokens"] == 2000

    # Pricing for gemini-1.5-flash: $0.075/1M in, $0.30/1M out
    # 10,000 * (0.075 / 1,000,000) = 0.00075
    # 2,000 * (0.30 / 1,000,000) = 0.00060
    # Expected cost = 0.00135
    assert metrics["cost_float"] == pytest.approx(0.00135, abs=1e-5)
