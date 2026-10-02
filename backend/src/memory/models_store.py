"""src/memory/models_store.py - AI Models Catalog & Pricing in Neon PostgreSQL.

Stores multimodal AI models (with both vision and text capacity) and their token pricing
in Neon PostgreSQL database. Provides real-time dynamic switching, provider management,
and user-extensible model registration.
"""

import logging
from typing import Any

from src.memory.database import get_db_connection

logger = logging.getLogger(__name__)

# Fallback in-memory catalog with live internet-sourced pricing for multimodal models
INITIAL_MULTIMODAL_MODELS: list[dict[str, Any]] = [
    # --- OpenAI ---
    {
        "provider": "OpenAI",
        "model_id": "gpt-4o",
        "model_name": "GPT-4o (Omni Multimodal)",
        "input_price_per_1m": 2.50,
        "output_price_per_1m": 10.00,
        "supports_vision": True,
        "supports_text": True,
        "context_window": 128000,
        "is_default": True,
    },
    {
        "provider": "OpenAI",
        "model_id": "gpt-4o-mini",
        "model_name": "GPT-4o Mini (Affordable Multimodal)",
        "input_price_per_1m": 0.15,
        "output_price_per_1m": 0.60,
        "supports_vision": True,
        "supports_text": True,
        "context_window": 128000,
        "is_default": False,
    },
    {
        "provider": "OpenAI",
        "model_id": "gpt-4.1",
        "model_name": "GPT-4.1 (Next-Gen Multimodal)",
        "input_price_per_1m": 2.00,
        "output_price_per_1m": 8.00,
        "supports_vision": True,
        "supports_text": True,
        "context_window": 128000,
        "is_default": False,
    },
    {
        "provider": "OpenAI",
        "model_id": "gpt-4.1-mini",
        "model_name": "GPT-4.1 Mini (High Efficiency)",
        "input_price_per_1m": 0.15,
        "output_price_per_1m": 0.60,
        "supports_vision": True,
        "supports_text": True,
        "context_window": 128000,
        "is_default": False,
    },
    {
        "provider": "OpenAI",
        "model_id": "o1",
        "model_name": "OpenAI o1 (Multimodal Reasoning)",
        "input_price_per_1m": 15.00,
        "output_price_per_1m": 60.00,
        "supports_vision": True,
        "supports_text": True,
        "context_window": 200000,
        "is_default": False,
    },
    {
        "provider": "OpenAI",
        "model_id": "gpt-5-mini",
        "model_name": "GPT-5 Mini",
        "input_price_per_1m": 0.25,
        "output_price_per_1m": 2.00,
        "supports_vision": True,
        "supports_text": True,
        "context_window": 128000,
        "is_default": False,
    },
    {
        "provider": "OpenAI",
        "model_id": "gpt-5",
        "model_name": "GPT-5 (Flagship)",
        "input_price_per_1m": 2.00,
        "output_price_per_1m": 8.00,
        "supports_vision": True,
        "supports_text": True,
        "context_window": 128000,
        "is_default": False,
    },
    # --- Google ---
    {
        "provider": "Google",
        "model_id": "gemini-1.5-flash",
        "model_name": "Gemini 1.5 Flash (Fast Multimodal)",
        "input_price_per_1m": 0.075,
        "output_price_per_1m": 0.30,
        "supports_vision": True,
        "supports_text": True,
        "context_window": 1000000,
        "is_default": False,
    },
    {
        "provider": "Google",
        "model_id": "gemini-1.5-pro",
        "model_name": "Gemini 1.5 Pro (Deep Multimodal)",
        "input_price_per_1m": 1.25,
        "output_price_per_1m": 5.00,
        "supports_vision": True,
        "supports_text": True,
        "context_window": 2000000,
        "is_default": False,
    },
    {
        "provider": "Google",
        "model_id": "gemini-2.0-flash",
        "model_name": "Gemini 2.0 Flash (Ultra-Fast Multimodal)",
        "input_price_per_1m": 0.10,
        "output_price_per_1m": 0.40,
        "supports_vision": True,
        "supports_text": True,
        "context_window": 1000000,
        "is_default": False,
    },
    # --- Anthropic ---
    {
        "provider": "Anthropic",
        "model_id": "claude-3-5-sonnet-20241022",
        "model_name": "Claude 3.5 Sonnet (State-of-the-Art Vision)",
        "input_price_per_1m": 3.00,
        "output_price_per_1m": 15.00,
        "supports_vision": True,
        "supports_text": True,
        "context_window": 200000,
        "is_default": False,
    },
    {
        "provider": "Anthropic",
        "model_id": "claude-3-5-haiku-20241022",
        "model_name": "Claude 3.5 Haiku (High-Speed Multimodal)",
        "input_price_per_1m": 0.80,
        "output_price_per_1m": 4.00,
        "supports_vision": True,
        "supports_text": True,
        "context_window": 200000,
        "is_default": False,
    },
    # --- Groq / Meta ---
    {
        "provider": "Groq / Meta",
        "model_id": "llama-3.2-11b-vision-preview",
        "model_name": "Llama 3.2 11B Vision (Groq LPU)",
        "input_price_per_1m": 0.05,
        "output_price_per_1m": 0.08,
        "supports_vision": True,
        "supports_text": True,
        "context_window": 128000,
        "is_default": False,
    },
    {
        "provider": "Groq / Meta",
        "model_id": "llama-3.2-90b-vision-preview",
        "model_name": "Llama 3.2 90B Vision (Groq LPU)",
        "input_price_per_1m": 0.59,
        "output_price_per_1m": 0.79,
        "supports_vision": True,
        "supports_text": True,
        "context_window": 128000,
        "is_default": False,
    },
    # --- Mistral ---
    {
        "provider": "Mistral",
        "model_id": "pixtral-12b-2409",
        "model_name": "Pixtral 12B (Open Multimodal)",
        "input_price_per_1m": 0.15,
        "output_price_per_1m": 0.15,
        "supports_vision": True,
        "supports_text": True,
        "context_window": 128000,
        "is_default": False,
    },
]

# In-memory runtime cache for resilience
_IN_MEMORY_MODELS_CACHE: dict[str, dict[str, Any]] = {m["model_id"]: dict(m) for m in INITIAL_MULTIMODAL_MODELS}


def init_models_table() -> bool:
    """Initializes the ai_models table in PostgreSQL and seeds initial models."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS ai_models (
                        id SERIAL PRIMARY KEY,
                        provider TEXT NOT NULL,
                        model_id TEXT UNIQUE NOT NULL,
                        model_name TEXT NOT NULL,
                        input_price_per_1m DOUBLE PRECISION NOT NULL,
                        output_price_per_1m DOUBLE PRECISION NOT NULL,
                        supports_vision BOOLEAN DEFAULT TRUE,
                        supports_text BOOLEAN DEFAULT TRUE,
                        context_window INTEGER DEFAULT 128000,
                        is_active BOOLEAN DEFAULT TRUE,
                        is_default BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX IF NOT EXISTS idx_ai_models_provider ON ai_models(provider);
                    CREATE INDEX IF NOT EXISTS idx_ai_models_model_id ON ai_models(model_id);
                """)

                # Check if table is empty
                cur.execute("SELECT COUNT(*) FROM ai_models;")
                count = cur.fetchone()[0]
                if count == 0:
                    seed_default_models(conn=conn)
        return True
    except Exception as exc:
        logger.warning(f"Could not initialize Neon DB ai_models table: {exc}")
        return False


def seed_default_models(conn=None, force: bool = False) -> int:
    """Seeds the initial multimodal models and their pricing into the database."""
    inserted = 0
    try:

        def _seed(c):
            nonlocal inserted
            with c.cursor() as cur:
                for m in INITIAL_MULTIMODAL_MODELS:
                    if force:
                        cur.execute(
                            """
                            INSERT INTO ai_models (
                                provider, model_id, model_name, input_price_per_1m,
                                output_price_per_1m, supports_vision, supports_text,
                                context_window, is_default, is_active
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                            ON CONFLICT (model_id) DO UPDATE SET
                                provider = EXCLUDED.provider,
                                model_name = EXCLUDED.model_name,
                                input_price_per_1m = EXCLUDED.input_price_per_1m,
                                output_price_per_1m = EXCLUDED.output_price_per_1m,
                                supports_vision = EXCLUDED.supports_vision,
                                supports_text = EXCLUDED.supports_text,
                                context_window = EXCLUDED.context_window,
                                updated_at = CURRENT_TIMESTAMP;
                        """,
                            (
                                m["provider"],
                                m["model_id"],
                                m["model_name"],
                                m["input_price_per_1m"],
                                m["output_price_per_1m"],
                                m["supports_vision"],
                                m["supports_text"],
                                m["context_window"],
                                m["is_default"],
                            ),
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO ai_models (
                                provider, model_id, model_name, input_price_per_1m,
                                output_price_per_1m, supports_vision, supports_text,
                                context_window, is_default, is_active
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                            ON CONFLICT (model_id) DO NOTHING;
                        """,
                            (
                                m["provider"],
                                m["model_id"],
                                m["model_name"],
                                m["input_price_per_1m"],
                                m["output_price_per_1m"],
                                m["supports_vision"],
                                m["supports_text"],
                                m["context_window"],
                                m["is_default"],
                            ),
                        )
                    inserted += 1

        if conn is not None:
            _seed(conn)
        else:
            with get_db_connection() as new_conn:
                _seed(new_conn)
        logger.info(f"Seeded {inserted} multimodal AI models into PostgreSQL.")
        return inserted
    except Exception as exc:
        logger.warning(f"Error seeding default AI models to DB: {exc}")
        return len(INITIAL_MULTIMODAL_MODELS)


def list_models(
    provider: str | None = None, only_active: bool = True, only_vision: bool = True
) -> list[dict[str, Any]]:
    """List all AI models from PostgreSQL, with filtering options and memory fallback."""
    try:
        with get_db_connection() as conn, conn.cursor() as cur:
            query = """
                    SELECT id, provider, model_id, model_name, input_price_per_1m,
                           output_price_per_1m, supports_vision, supports_text,
                           context_window, is_active, is_default, created_at, updated_at
                    FROM ai_models
                    WHERE 1=1
                """
            params = []
            if only_active:
                query += " AND is_active = TRUE"
            if only_vision:
                query += " AND supports_vision = TRUE"
            if provider:
                query += " AND LOWER(provider) = LOWER(%s)"
                params.append(provider)

            query += " ORDER BY provider ASC, is_default DESC, model_name ASC;"
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

            results = []
            for row in rows:
                m = {
                    "id": row[0],
                    "provider": row[1],
                    "model_id": row[2],
                    "model_name": row[3],
                    "input_price_per_1m": float(row[4]),
                    "output_price_per_1m": float(row[5]),
                    "supports_vision": bool(row[6]),
                    "supports_text": bool(row[7]),
                    "context_window": int(row[8]),
                    "is_active": bool(row[9]),
                    "is_default": bool(row[10]),
                    "created_at": row[11],
                    "updated_at": row[12],
                }
                results.append(m)
                _IN_MEMORY_MODELS_CACHE[m["model_id"]] = m

            if results:
                return results
    except Exception as exc:
        logger.debug(f"DB list_models error: {exc}. Using fallback cache.")

    # In-memory fallback
    cached = list(_IN_MEMORY_MODELS_CACHE.values())
    if only_active:
        cached = [m for m in cached if m.get("is_active", True)]
    if only_vision:
        cached = [m for m in cached if m.get("supports_vision", True)]
    if provider:
        cached = [m for m in cached if m.get("provider", "").lower() == provider.lower()]
    cached.sort(key=lambda x: (x.get("provider", ""), not x.get("is_default", False), x.get("model_name", "")))
    return cached


def list_providers() -> list[str]:
    """Returns a sorted list of unique providers present in the catalog."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT provider FROM ai_models WHERE is_active = TRUE ORDER BY provider ASC;")
                rows = cur.fetchall()
                if rows:
                    return [r[0] for r in rows]
    except Exception as exc:
        logger.debug(f"DB list_providers error: {exc}")

    providers = sorted({m.get("provider", "OpenAI") for m in _IN_MEMORY_MODELS_CACHE.values()})
    return providers or ["OpenAI", "Google", "Anthropic", "Groq / Meta", "Mistral"]


def get_model(model_id: str) -> dict[str, Any] | None:
    """Retrieve details for a specific model ID."""
    if not model_id:
        return None
    try:
        with get_db_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                    SELECT id, provider, model_id, model_name, input_price_per_1m,
                           output_price_per_1m, supports_vision, supports_text,
                           context_window, is_active, is_default, created_at, updated_at
                    FROM ai_models
                    WHERE model_id = %s;
                """,
                (model_id,),
            )
            row = cur.fetchone()
            if row:
                m = {
                    "id": row[0],
                    "provider": row[1],
                    "model_id": row[2],
                    "model_name": row[3],
                    "input_price_per_1m": float(row[4]),
                    "output_price_per_1m": float(row[5]),
                    "supports_vision": bool(row[6]),
                    "supports_text": bool(row[7]),
                    "context_window": int(row[8]),
                    "is_active": bool(row[9]),
                    "is_default": bool(row[10]),
                    "created_at": row[11],
                    "updated_at": row[12],
                }
                _IN_MEMORY_MODELS_CACHE[model_id] = m
                return m
    except Exception as exc:
        logger.debug(f"DB get_model error: {exc}")

    return _IN_MEMORY_MODELS_CACHE.get(model_id)


def get_default_model() -> dict[str, Any]:
    """Retrieve the designated default model."""
    try:
        with get_db_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                    SELECT id, provider, model_id, model_name, input_price_per_1m,
                           output_price_per_1m, supports_vision, supports_text,
                           context_window, is_active, is_default, created_at, updated_at
                    FROM ai_models
                    WHERE is_default = TRUE AND is_active = TRUE
                    LIMIT 1;
                """)
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "provider": row[1],
                    "model_id": row[2],
                    "model_name": row[3],
                    "input_price_per_1m": float(row[4]),
                    "output_price_per_1m": float(row[5]),
                    "supports_vision": bool(row[6]),
                    "supports_text": bool(row[7]),
                    "context_window": int(row[8]),
                    "is_active": bool(row[9]),
                    "is_default": bool(row[10]),
                }
    except Exception:
        pass

    for m in _IN_MEMORY_MODELS_CACHE.values():
        if m.get("is_default"):
            return m
    return INITIAL_MULTIMODAL_MODELS[0]


def add_model(
    provider: str,
    model_id: str,
    model_name: str,
    input_price_per_1m: float,
    output_price_per_1m: float,
    supports_vision: bool = True,
    supports_text: bool = True,
    context_window: int = 128000,
    is_default: bool = False,
) -> bool:
    """Adds or updates a custom AI model and its pricing in PostgreSQL."""
    clean_provider = provider.strip()
    clean_id = model_id.strip()
    clean_name = model_name.strip()

    if not clean_provider or not clean_id or not clean_name:
        raise ValueError("Provider, Model ID, and Model Name must not be empty.")

    new_model = {
        "provider": clean_provider,
        "model_id": clean_id,
        "model_name": clean_name,
        "input_price_per_1m": float(input_price_per_1m),
        "output_price_per_1m": float(output_price_per_1m),
        "supports_vision": bool(supports_vision),
        "supports_text": bool(supports_text),
        "context_window": int(context_window),
        "is_active": True,
        "is_default": bool(is_default),
    }

    # Update in-memory cache
    _IN_MEMORY_MODELS_CACHE[clean_id] = new_model
    if is_default:
        for k in _IN_MEMORY_MODELS_CACHE:
            if k != clean_id:
                _IN_MEMORY_MODELS_CACHE[k]["is_default"] = False

    try:
        with get_db_connection() as conn, conn.cursor() as cur:
            if is_default:
                cur.execute("UPDATE ai_models SET is_default = FALSE;")

            cur.execute(
                """
                    INSERT INTO ai_models (
                        provider, model_id, model_name, input_price_per_1m,
                        output_price_per_1m, supports_vision, supports_text,
                        context_window, is_default, is_active
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                    ON CONFLICT (model_id) DO UPDATE SET
                        provider = EXCLUDED.provider,
                        model_name = EXCLUDED.model_name,
                        input_price_per_1m = EXCLUDED.input_price_per_1m,
                        output_price_per_1m = EXCLUDED.output_price_per_1m,
                        supports_vision = EXCLUDED.supports_vision,
                        supports_text = EXCLUDED.supports_text,
                        context_window = EXCLUDED.context_window,
                        is_default = EXCLUDED.is_default,
                        is_active = TRUE,
                        updated_at = CURRENT_TIMESTAMP;
                """,
                (
                    clean_provider,
                    clean_id,
                    clean_name,
                    float(input_price_per_1m),
                    float(output_price_per_1m),
                    bool(supports_vision),
                    bool(supports_text),
                    int(context_window),
                    bool(is_default),
                ),
            )
        logger.info(f"Model '{clean_id}' saved to database.")
        return True
    except Exception as exc:
        logger.warning(f"Failed to persist custom model '{clean_id}' to DB: {exc}")
        return True  # Retained in memory cache


def set_default_model(model_id: str) -> bool:
    """Sets a given model_id as the primary active default."""
    clean_id = model_id.strip()
    if clean_id in _IN_MEMORY_MODELS_CACHE:
        for k in _IN_MEMORY_MODELS_CACHE:
            _IN_MEMORY_MODELS_CACHE[k]["is_default"] = k == clean_id

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE ai_models SET is_default = FALSE;")
                cur.execute("UPDATE ai_models SET is_default = TRUE WHERE model_id = %s;", (clean_id,))
        return True
    except Exception as exc:
        logger.warning(f"Could not set default model in DB: {exc}")
        return True


def delete_model(model_id: str) -> bool:
    """Soft-deletes or removes a custom model from the database."""
    clean_id = model_id.strip()
    if clean_id in _IN_MEMORY_MODELS_CACHE:
        _IN_MEMORY_MODELS_CACHE.pop(clean_id, None)

    try:
        with get_db_connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM ai_models WHERE model_id = %s;", (clean_id,))
        return True
    except Exception as exc:
        logger.warning(f"Could not delete model {clean_id}: {exc}")
        return False
