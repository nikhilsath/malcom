"""add webhook_api_events.delivery_id

Revision ID: 0002_add_webhook_delivery_id
Revises: 0001_baseline_schema
Create Date: 2026-04-06 00:00:00

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_webhook_delivery_id"
down_revision = "0001_baseline_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable delivery_id column and an index to support GitHub delivery dedupe.
    op.add_column("webhook_api_events", sa.Column("delivery_id", sa.Text(), nullable=True))
    # SQLite/other dialects may not support conditional unique indexes; migration may be adjusted by DB maintainer.
    try:
        op.execute("CREATE UNIQUE INDEX IF NOT EXISTS webhook_api_events_delivery_id_idx ON webhook_api_events(delivery_id)")
    except Exception:
        # Some DBs don't support IF NOT EXISTS on index creation; ignore if fails.
        pass


def downgrade() -> None:
    try:
        op.drop_index("webhook_api_events_delivery_id_idx", table_name="webhook_api_events")
    except Exception:
        pass
    # dropping a column is not portable; leave as no-op for downgrade.
    return
