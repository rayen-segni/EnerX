"""add project commitment file

Revision ID: e872aac17cc8
Revises: c7a278168115
Create Date: 2026-10-11 14:57:13.710598

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e872aac17cc8'
down_revision: Union[str, Sequence[str], None] = 'c7a278168115'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE projects
        ADD COLUMN commitment_file_id VARCHAR(255),
        ADD COLUMN commitment_transaction_id VARCHAR(255);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE projects
        DROP COLUMN commitment_transaction_id,
        DROP COLUMN commitment_file_id;
        """
    )
