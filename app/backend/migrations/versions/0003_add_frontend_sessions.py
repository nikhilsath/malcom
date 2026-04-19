"""add frontend_sessions

Revision ID: 0003_add_frontend_sessions
Revises: 0002_add_webhook_delivery_id
Create Date: 2026-04-19 00:00:00

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_add_frontend_sessions"
down_revision = "0002_add_webhook_delivery_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "frontend_sessions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("operator_name", sa.Text(), nullable=False),
        sa.Column("client_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("scopes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("access_token_hash", sa.Text(), nullable=False),
        sa.Column("refresh_token_hash", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("issued_at", sa.Text(), nullable=False),
        sa.Column("access_expires_at", sa.Text(), nullable=False),
        sa.Column("refresh_expires_at", sa.Text(), nullable=False),
        sa.Column("last_used_at", sa.Text(), nullable=True),
        sa.Column("revoked_at", sa.Text(), nullable=True),
    )
    try:
        op.create_unique_constraint("frontend_sessions_access_token_hash_key", "frontend_sessions", ["access_token_hash"])
    except Exception:
        pass
    try:
        op.create_unique_constraint("frontend_sessions_refresh_token_hash_key", "frontend_sessions", ["refresh_token_hash"])
    except Exception:
        pass
    try:
        op.execute(
            "CREATE INDEX IF NOT EXISTS frontend_sessions_status_expires_idx "
            "ON frontend_sessions(status, access_expires_at, refresh_expires_at)"
        )
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index("frontend_sessions_status_expires_idx", table_name="frontend_sessions")
    except Exception:
        pass
    try:
        op.drop_constraint("frontend_sessions_refresh_token_hash_key", "frontend_sessions", type_="unique")
    except Exception:
        pass
    try:
        op.drop_constraint("frontend_sessions_access_token_hash_key", "frontend_sessions", type_="unique")
    except Exception:
        pass
    op.drop_table("frontend_sessions")
