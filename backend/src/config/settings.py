"""Runtime settings loaded via Pydantic Settings from the environment.

Centralizes all environment configuration (model selection, token pricing,
concurrency limits, and API keys) into a single typed Settings class.
When you change the model name in .env, settings automatically updates
pricing, model identifiers, and configurations across the entire codebase.
"""

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Always force-load local .env with override=True
load_dotenv(override=True)


# Standard pricing catalog (USD per 1M tokens) for known models
KNOWN_MODEL_PRICING: dict[str, tuple[float, float]] = {
    # model_name: (input_price_per_1m, output_price_per_1m)
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5": (2.00, 8.00),
    "gpt-5-nano": (0.10, 0.50),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.15, 0.60),
    "gpt-4.1-nano": (0.08, 0.35),
    "o3-mini": (1.10, 4.40),
    "o1": (15.00, 60.00),
    "o1-mini": (1.10, 4.40),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API Keys
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    typesafe_api_key: str | None = Field(default=None, alias="TYPESAFE_API_KEY")

    # OpenAI Vision Model Configuration
    openai_model: str = Field(default="gpt-5-mini", alias="OPENAI_MODEL")
    openai_input_price_per_1m: float | None = Field(default=None, alias="OPENAI_INPUT_PRICE_PER_1M")
    openai_output_price_per_1m: float | None = Field(default=None, alias="OPENAI_OUTPUT_PRICE_PER_1M")

    # Pipeline Settings
    max_crops_per_page: int = Field(default=4, alias="MAX_CROPS_PER_PAGE")
    vision_max_concurrency: int = Field(default=2, alias="VISION_MAX_CONCURRENCY")
    enable_case_storage: bool = Field(default=False, alias="ENABLE_CASE_STORAGE")

    # Neon PostgreSQL Memory Database
    database_url: str | None = Field(
        default="postgresql://neondb_owner:npg_3OK9dMfVaUkb@ep-shiny-breeze-b4r10ing-pooler.c-6.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
        alias="DATABASE_URL",
    )

    # Redis Cache
    redis_url: str | None = Field(default="redis://red-dav42tu0tbcc73dh444g:6379", alias="REDIS_URL")

    # Frontend CORS Integration
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")

    @property
    def input_price_per_1m(self) -> float:
        """Return explicit input rate from .env or derive automatically from known model catalog."""
        if self.openai_input_price_per_1m is not None:
            return float(self.openai_input_price_per_1m)
        return KNOWN_MODEL_PRICING.get(self.openai_model, (0.25, 2.00))[0]

    @property
    def output_price_per_1m(self) -> float:
        """Return explicit output rate from .env or derive automatically from known model catalog."""
        if self.openai_output_price_per_1m is not None:
            return float(self.openai_output_price_per_1m)
        return KNOWN_MODEL_PRICING.get(self.openai_model, (0.25, 2.00))[1]

    @property
    def price_input_per_token(self) -> float:
        return self.input_price_per_1m / 1_000_000.0

    @property
    def price_output_per_token(self) -> float:
        return self.output_price_per_1m / 1_000_000.0


# Global settings singleton
settings = Settings()

# Backward-compatibility module-level exports
OPENAI_MODEL = settings.openai_model
OPENAI_INPUT_PRICE_PER_1M = settings.input_price_per_1m
OPENAI_OUTPUT_PRICE_PER_1M = settings.output_price_per_1m
OPENAI_PRICE_INPUT_PER_TOKEN = settings.price_input_per_token
OPENAI_PRICE_OUTPUT_PER_TOKEN = settings.price_output_per_token
MAX_CROPS_PER_PAGE = settings.max_crops_per_page
VISION_MAX_CONCURRENCY = settings.vision_max_concurrency

# TypeSafe System One (Jev). None means jev_call uses uncertainty-preserving fallbacks.
try:
    from typesafe_sdk import TypeSafeClient

    typesafe_client = TypeSafeClient()
except Exception:
    typesafe_client = None
