"""Pydantic schemas and request/response models for House Scrutiny API."""

from pydantic import BaseModel, Field


class ReviewDecision(BaseModel):
    """Body for POST /reviews: human decision does not mutate stored AI verdict."""

    reviewer_name: str = Field(..., description="Name or license number of the inspecting engineer")
    decision: str = Field(..., description="Decision: APPROVED, CORRECTION_REQUIRED, PENDING, or NOT_APPLICABLE")
    note: str | None = Field("", description="Optional engineering observations or review notes")


class ChatMessageRequest(BaseModel):
    """Payload for conversational follow-up questions."""

    message: str = Field(..., description="User prompt or question regarding drawing bylaws")
    model: str | None = Field(None, description="Optional override model ID (e.g. gpt-4o, gpt-5-mini)")


class ModelRegisterRequest(BaseModel):
    """Payload for registering a custom AI model."""

    provider: str = Field(..., description="Provider name (OpenAI, Anthropic, Google, Ollama, etc.)")
    model_id: str = Field(..., description="Model identifier string")
    model_name: str = Field(..., description="Display label for the model")
    input_price_per_1m: float = Field(0.0, description="Cost in USD per 1M input tokens")
    output_price_per_1m: float = Field(0.0, description="Cost in USD per 1M output tokens")
    supports_vision: bool = Field(True, description="Whether model supports image/vision processing")
    supports_text: bool = Field(True, description="Whether model supports text chat")
    context_window: int = Field(128000, description="Context window size in tokens")
    is_default: bool = Field(False, description="Set as system default model")


class HealthResponse(BaseModel):
    status: str
    timestamp: float
    openai_model: str
    typesafe_connected: bool
