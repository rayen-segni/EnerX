"""
EnerX Backend - Auth Routes
Simulated authentication using Hedera Portal users from PORTAL_USERS_PATH.
"""

import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection

from app.config import settings
from app.database import get_db
from app.schemas.auth import DIDCreateRequest, DIDCreateResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


def _load_portal_users() -> list[Dict[str, Any]]:
    """Load users from the simulated portal users JSON file."""
    setting = settings
    try:
        with open(settings.PORTAL_USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("users", [])
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portal users file not found !",
        )


@router.get("/{user_id}", summary="Simulated Portal Login by User ID")
def login(user_id: int) -> Dict[str, Any]:
    """
    Returns the simulated Hedera Portal user matching the given user_id.

    user_id corresponds to the 'user_id' field in data/hedera_portal_users.json.
    """
    users = _load_portal_users()

    for user in users:
        if user.get("user_id") == user_id:
            return user

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No portal user found with user_id={user_id}",
    )


@router.post("/did", response_model=DIDCreateResponse, summary="Create a Hedera DID")
def create_did(
    request: DIDCreateRequest,
    connection: Connection = Depends(get_db),
):
    pass

