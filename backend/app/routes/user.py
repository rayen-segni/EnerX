from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection
from psycopg.errors import IntegrityError

from app.database import get_db
from app.schemas.auth import UserPatchRequest, UserResponse
from app.schemas.user import UserDetailsResponse

router = APIRouter(prefix="/user", tags=["Users"])


@router.get("/{user_id}", response_model=UserDetailsResponse)
def get_user(
    user_id: int,
    connection: Connection = Depends(get_db),
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, hedera_id, did, legal_name, email, phone, balance, created_at
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        user = cursor.fetchone()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} was not found",
            )

        cursor.execute(
            """
            SELECT
                tb.id,
                tb.token_id,
                tb.amount,
                t.hedera_token_id,
                t.token_name,
                t.token_symbol,
                p.id AS project_id,
                p.name AS project_name
            FROM token_balances AS tb
            JOIN tokens AS t ON t.id = tb.token_id
            JOIN projects AS p ON p.id = t.project_id
            WHERE tb.user_id = %s
            ORDER BY tb.token_id
            """,
            (user_id,),
        )
        token_balances = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                p.id,
                p.owner_id,
                p.name,
                p.description,
                p.target_amount,
                p.status,
                t.id AS token_id,
                t.hedera_token_id,
                t.token_name,
                t.token_symbol,
                t.total_supply,
                p.commitment_file_id,
                p.commitment_transaction_id
            FROM projects AS p
            JOIN tokens AS t ON t.project_id = p.id
            WHERE p.owner_id = %s
            ORDER BY p.id
            """,
            (user_id,),
        )
        projects = cursor.fetchall()

    return {
        **dict(user),
        "token_balances": token_balances,
        "projects": projects,
    }


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
