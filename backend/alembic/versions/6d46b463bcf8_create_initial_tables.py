"""create_initial_tables

Revision ID: 6d46b463bcf8
Revises: 
Create Date: 2026-10-05 16:06:36.275719

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d46b463bcf8'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
    CREATE TYPE project_status AS ENUM ('funding', 'active');

    CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        hedera_id VARCHAR(255) UNIQUE NOT NULL,
        did VARCHAR(255) UNIQUE,
        legal_name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        phone VARCHAR(50),
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE projects (
        id SERIAL PRIMARY KEY,
        owner_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        target_amount INT NOT NULL,
        funded_amount INT NOT NULL DEFAULT 0,
        status project_status NOT NULL DEFAULT 'funding',
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE tokens (
        id SERIAL PRIMARY KEY,
        project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        hedera_token_id VARCHAR(255) NOT NULL,
        total_supply INT NOT NULL,
        initial_price NUMERIC(15, 2) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE investments (
        id SERIAL PRIMARY KEY,
        project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        investor_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token_amount INT NOT NULL,
        amount_paid NUMERIC(15, 2) NOT NULL,
        transaction_id VARCHAR(255),
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE token_transactions (
        id SERIAL PRIMARY KEY,
        token_id INT NOT NULL REFERENCES tokens(id) ON DELETE CASCADE,
        from_id INT REFERENCES users(id) ON DELETE SET NULL,
        to_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        amount INT NOT NULL,
        hedera_trans_id VARCHAR(255),
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE token_balances (
        id SERIAL UNIQUE,
        token_id INT NOT NULL REFERENCES tokens(id) ON DELETE CASCADE,
        user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        amount INT NOT NULL DEFAULT 0,
        ownership_percentage NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
        PRIMARY KEY (token_id, user_id)
    );

    CREATE TABLE energy_productions (
        id SERIAL PRIMARY KEY,
        project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        production_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        energy_kwh NUMERIC(12, 2) NOT NULL,
        revenue NUMERIC(15, 2) NOT NULL
    );

    CREATE TABLE distributions (
        id SERIAL PRIMARY KEY,
        token_balance_id INT NOT NULL REFERENCES token_balances(id) ON DELETE CASCADE,
        amount NUMERIC(15, 2) NOT NULL,
        production_id INT NOT NULL REFERENCES energy_productions(id) ON DELETE CASCADE,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE token_listings (
        id SERIAL PRIMARY KEY,
        tk_balance INT NOT NULL REFERENCES token_balances(id) ON DELETE CASCADE,
        unit_price NUMERIC(15, 2) NOT NULL,
        offered_tokens INT NOT NULL
    );
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
    DROP TABLE IF EXISTS token_listings;
    DROP TABLE IF EXISTS distributions;
    DROP TABLE IF EXISTS energy_productions;
    DROP TABLE IF EXISTS token_balances;
    DROP TABLE IF EXISTS token_transactions;
    DROP TABLE IF EXISTS investments;
    DROP TABLE IF EXISTS tokens;
    DROP TABLE IF EXISTS projects;
    DROP TABLE IF EXISTS users;
    DROP TYPE IF EXISTS project_status;
    """)

