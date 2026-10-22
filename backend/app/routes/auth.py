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
from hedera.did_service import create_user_did

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
async def create_did(
    request: DIDCreateRequest,
    connection: Connection = Depends(get_db),
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, hedera_id, legal_name, email
            FROM users
            WHERE id = %s
            FOR UPDATE
            """,
            (request.user_id,),
        )
        user = cursor.fetchone()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {request.user_id} was not found",
            )

        if (
            str(user["hedera_id"]) != request.hedera_id #type: ignore
            or user["legal_name"] != request.legal_name #type: ignore
            or user["email"] != str(request.email) #type: ignore
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The identity data does not match the registered user",
            )

        try:
            did = await create_user_did(
                private_key_hex=settings.OPERATOR_KEY,
                profile_url=f"{settings.DID_SERVICE_ENDPOINT}/user/{request.user_id}",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not register the DID on Hedera: {exc}",
            ) from exc

        cursor.execute(
            """
            UPDATE users
            SET did = %s
            WHERE id = %s
            """,
            (did, request.user_id),
        )

    return {"user_id": request.user_id, "did": did}