from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection
from psycopg.errors import IntegrityError

from app.database import get_db
from app.schemas.auth import UserPatchRequest, UserResponse

router = APIRouter(prefix="/user", tags=["Users"])




@router.patch("", response_model=UserResponse)
def update_user(
    request: UserPatchRequest,
    connection: Connection = Depends(get_db),
):
    updates = request.model_dump(
        exclude={"id"},
        exclude_unset=True,
    )
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one user field to update",
        )

    # Column names come only from the fields declared on UserPatchRequest.
    set_clause = ", ".join(f"{column} = %s" for column in updates)
    values = list(updates.values())

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE users
                SET {set_clause}
                WHERE id = %s
                RETURNING id, hedera_id, did, legal_name, email, phone, balance, created_at
                """,  #type: ignore
                (*values, request.id),
            )
            user = cursor.fetchone()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The update conflicts with an existing user or violates a database constraint",
        ) from exc

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {request.id} was not found",
        )

    return user

