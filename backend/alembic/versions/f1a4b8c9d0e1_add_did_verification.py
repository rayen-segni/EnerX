"""add DID verification state and authentication challenges

Revision ID: f1a4b8c9d0e1
Revises: e872aac17cc8
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f1a4b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e872aac17cc8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS identity_public_key TEXT,
        ADD COLUMN IF NOT EXISTS identity_verified BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS investor_verified BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS owner_verified BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS verification_updated_at TIMESTAMPTZ;

        CREATE TABLE IF NOT EXISTS auth_challenges (
            id UUID PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            nonce TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMPTZ NOT NULL,
            consumed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS auth_challenges_user_idx
            ON auth_challenges(user_id);

        CREATE TABLE IF NOT EXISTS verifiable_credentials (
            id UUID PRIMARY KEY,
            subject_user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            credential_type VARCHAR(100) NOT NULL,
            issuer VARCHAR(255) NOT NULL,
            document_hash VARCHAR(128) NOT NULL,
            credential_json JSONB NOT NULL,
            signature TEXT NOT NULL,
            issued_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMPTZ NOT NULL,
            revoked_at TIMESTAMPTZ
        );

        CREATE INDEX IF NOT EXISTS credentials_subject_idx
            ON verifiable_credentials(subject_user_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS auth_challenges;
        DROP TABLE IF EXISTS verifiable_credentials;
        ALTER TABLE users
        DROP COLUMN IF EXISTS verification_updated_at,
        DROP COLUMN IF EXISTS owner_verified,
        DROP COLUMN IF EXISTS investor_verified,
        DROP COLUMN IF EXISTS identity_verified,
        DROP COLUMN IF EXISTS identity_public_key;
        """
    )
