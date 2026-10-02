from fastapi import APIRouter, HTTPException

from src.api.schemas import ModelRegisterRequest
from src.config.settings import settings
from src.memory import (
    add_model,
    delete_model,
    get_model,
    list_models,
)
from src.memory import (
    list_providers as get_all_providers,
)

router = APIRouter(prefix="/api/v1/models", tags=["AI Models"])


@router.get("", summary="List registered AI models")
def list_available_models(provider: str | None = None):
    """Returns all registered AI models in the system catalog."""
    models = list_models(provider=provider, only_active=True, only_vision=True)
    return {"count": len(models), "models": models, "active_system_model": settings.openai_model}


@router.get("/providers", summary="List supported AI model providers")
def list_providers():
    """List distinct AI providers supported by the platform."""
    return {"providers": get_all_providers()}


@router.post("", summary="Register a custom AI model")
def register_new_model(req: ModelRegisterRequest):
    """Add a new custom AI model to the system catalog."""
    if not req.supports_vision or not req.supports_text:
        raise HTTPException(status_code=400, detail="Model must support both vision and text capacity.")
    ok = add_model(
        provider=req.provider,
        model_id=req.model_id,
        model_name=req.model_name,
        input_price_per_1m=req.input_price_per_1m,
        output_price_per_1m=req.output_price_per_1m,
        supports_vision=req.supports_vision,
        supports_text=req.supports_text,
        context_window=req.context_window,
        is_default=req.is_default,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save model to database.")
    return {"status": "SUCCESS", "message": f"Model '{req.model_id}' registered successfully."}


@router.post("/{model_id}/select", summary="Select active model")
def select_active_model(model_id: str):
    """Sets a specific model as the active system model."""
    m = get_model(model_id)
    if not m:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")
    settings.openai_model = m["model_id"]
    settings.openai_input_price_per_1m = m["input_price_per_1m"]
    settings.openai_output_price_per_1m = m["output_price_per_1m"]
    return {
        "status": "SUCCESS",
        "active_model": settings.openai_model,
        "input_price_per_1m": settings.input_price_per_1m,
        "output_price_per_1m": settings.output_price_per_1m,
    }


@router.delete("/{model_id}", summary="Delete custom AI model")
def delete_model_endpoint(model_id: str):
    """Delete a custom registered model from database catalog."""
    ok = delete_model(model_id)
    if not ok:
        raise HTTPException(
            status_code=400, detail=f"Model '{model_id}' could not be deleted (might be default or protected)."
        )
    return {"status": "SUCCESS", "message": f"Model '{model_id}' deleted."}
