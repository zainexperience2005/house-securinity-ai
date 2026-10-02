"""Initial schema: scrutiny_threads, thread_messages, ai_models.

Revision ID: 001_initial_schema
Revises: (none — first migration)
Create Date: 2026-10-01

Replaces the ad-hoc CREATE TABLE IF NOT EXISTS calls that were scattered
throughout database.py and models_store.py and ran on every single request.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP

# revision identifiers, used by Alembic
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # scrutiny_threads — long-term cross-submission registry
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS scrutiny_threads (
            thread_id TEXT PRIMARY KEY,
            thread_name TEXT NOT NULL,
            pdf_filename TEXT NOT NULL,
            authority TEXT,
            overall_verdict TEXT,
            concrete_grade_psi DOUBLE PRECISION,
            slab_thickness_in DOUBLE PRECISION,
            completeness_score_pct DOUBLE PRECISION,
            processing_time_seconds DOUBLE PRECISION,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB DEFAULT '{}'::jsonb,
            raw_verdict JSONB DEFAULT '{}'::jsonb
        );
    """)
    op.execute("""
        ALTER TABLE scrutiny_threads
            ADD COLUMN IF NOT EXISTS processing_time_seconds DOUBLE PRECISION;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_scrutiny_threads_created
            ON scrutiny_threads(created_at DESC);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_scrutiny_threads_name
            ON scrutiny_threads(thread_name);
    """)

    # -------------------------------------------------------------------------
    # thread_messages — conversational chat history (short-term + long-term)
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS thread_messages (
            message_id SERIAL PRIMARY KEY,
            thread_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_thread_messages_thread
            ON thread_messages(thread_id, created_at ASC);
    """)

    # -------------------------------------------------------------------------
    # ai_models — multimodal AI model catalog with live pricing
    # -------------------------------------------------------------------------
    op.execute("""
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
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_models_provider ON ai_models(provider);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_models_model_id ON ai_models(model_id);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_models CASCADE;")
    op.execute("DROP TABLE IF EXISTS thread_messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS scrutiny_threads CASCADE;")
