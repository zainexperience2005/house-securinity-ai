"""Add cases and reviews tables for persistent drawing review packages in Neon DB.

Revision ID: 002_cases_and_reviews
Revises: 001_initial_schema
Create Date: 2026-10-01

Stores immutable review cases, uploaded drawing PDF packages (BYTEA),
verdicts, and engineering sign-off decisions in Neon PostgreSQL without
saving files to the local app filesystem.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, BYTEA

# revision identifiers, used by Alembic
revision = "002_cases_and_reviews"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # cases — persistent audit packages, verdicts, and source PDF bytes
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            authority TEXT,
            filenames_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            verdict_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            pdf_bytes BYTEA
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cases_created_at
            ON cases(created_at DESC);
    """)

    # -------------------------------------------------------------------------
    # reviews — human engineer audit decisions and review notes
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            review_id SERIAL PRIMARY KEY,
            case_id TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            reviewer_name TEXT NOT NULL,
            decision TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT ''
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_reviews_case_id
            ON reviews(case_id, created_at DESC);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS reviews CASCADE;")
    op.execute("DROP TABLE IF EXISTS cases CASCADE;")
