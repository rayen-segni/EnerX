"""seed_portal_users

Revision ID: c7a278168115
Revises: 6d46b463bcf8
Create Date: 2026-10-05 16:48:11.890459

"""
import json
import os
from typing import Sequence, Union

from alembic import op
from app.config import settings

# revision identifiers, used by Alembic.
revision: str = 'c7a278168115'
down_revision: Union[str, Sequence[str], None] = '6d46b463bcf8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Path to the portal users JSON file (relative to project root)
PORTAL_USERS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "hedera_portal_users.json")


def _load_users() -> list[dict]:
    with open(PORTAL_USERS_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("users", [])


def upgrade() -> None:
    """Seed users table from data/hedera_portal_users.json."""
    users = _load_users()

    for user in users:
        op.execute(
            f"""
            INSERT INTO users (id, hedera_id, did, legal_name, email, phone)
            VALUES (
                {user['user_id']},
                '{user['hedera_account_id']}',
                NULL,
                '{user['name']}',
                '{user['email']}',
                NULL
            )
            ON CONFLICT (id) DO NOTHING;
            
            INSERT INTO users (id, hedera_id, did, legal_name, email, phone)
            VALUES (0, '{settings.OPERATOR_ID}', NULL, 'Operator', NULL, NULL)
            ON CONFLICT (id) DO NOTHING;
            """
        )

    # Reset the serial sequence to continue after the seeded IDs
    op.execute("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));")


def downgrade() -> None:
    """Remove seeded portal users from users table."""
    users = _load_users()
    ids = ", ".join(str(u["user_id"]) for u in users)
    if ids:
        op.execute(f"DELETE FROM users WHERE id IN ({ids});")

