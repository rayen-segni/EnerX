"""add_user_id_to_tokens

Revision ID: d4a1c7e09f32
Revises: c7a278168115
Create Date: 2026-10-06
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d4a1c7e09f32"
down_revision: Union[str, Sequence[str], None] = "c7a278168115"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE tokens
        ADD COLUMN user_id INT REFERENCES users(id) ON DELETE CASCADE;

        UPDATE tokens
        SET user_id = projects.owner_id
        FROM projects
        WHERE tokens.project_id = projects.id;

        ALTER TABLE tokens
        ALTER COLUMN user_id SET NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE tokens DROP COLUMN user_id;")
