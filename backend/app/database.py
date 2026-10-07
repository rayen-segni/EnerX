"""Synchronous PostgreSQL connection dependency."""

from collections.abc import Generator
from typing import Any, cast

import psycopg
from psycopg import Connection
from psycopg.rows import DictRow, dict_row

from app.config import settings

DATABASE_URL = f"postgresql://{settings.DATABASE_USER}:{settings.DATABASE_PASSWORD}@{settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}"


def get_db() -> Generator[Connection[DictRow], None, None]:
    """Yield a database connection and commit or roll back the request transaction."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn: #type: ignore
        yield conn #type: ignore