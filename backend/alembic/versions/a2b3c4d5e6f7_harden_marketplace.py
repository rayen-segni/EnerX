"""harden marketplace listings

Revision ID: a2b3c4d5e6f7
Revises: f1a4b8c9d0e1
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1a4b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE token_listings
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;

        CREATE INDEX IF NOT EXISTS token_listings_balance_idx
            ON token_listings(tk_balance)
        WHERE cancelled_at IS NULL AND offered_tokens > 0;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS token_listings_balance_idx;
        ALTER TABLE token_listings
        DROP COLUMN IF EXISTS cancelled_at,
        DROP COLUMN IF EXISTS created_at;
        """
    )
