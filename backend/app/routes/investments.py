from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection

from app.database import get_db
from app.schemas.investment import InvestmentCreateRequest
from hedera.token_service import transfer_tokens

router = APIRouter(prefix="/investment", tags=["Investments"])



@router.post("/", status_code=status.HTTP_201_CREATED)
def create_investment(
    request: InvestmentCreateRequest,
    connection: Connection = Depends(get_db),
):
    with connection.cursor() as cursor:
        # Fetch the project and its associated token, locking the rows for update.
        cursor.execute(
            """
            SELECT
                p.id AS project_id,
                p.status AS project_status,
                p.target_amount,
                t.id AS token_id,
                t.hedera_token_id,
                t.total_supply
            FROM projects AS p
            JOIN tokens AS t ON t.project_id = p.id
            WHERE p.id = %s
            FOR UPDATE OF p, t
            """,
            (request.project_id,),
        )
        project = cursor.fetchone()
        
        # Check if the project and its associated token exist
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {request.project_id} or its token was not found",
            )

        # Check if the project is still accepting investments
        if project["project_status"] != "funding": #type: ignore
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This project is no longer accepting investments",
            )

        # Fetch the investing user's Hedera account ID and balance, locking the row for update.
        cursor.execute(
            """
            SELECT
                id,
                hedera_id,
                balance,
                identity_verified,
                EXISTS (
                    SELECT 1
                    FROM verifiable_credentials vc
                    WHERE vc.subject_user_id = users.id
                      AND vc.credential_type = 'InvestorVerification'
                      AND vc.revoked_at IS NULL
                      AND vc.expires_at > CURRENT_TIMESTAMP
                ) AS investor_verified
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
        if not user["identity_verified"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A verified user identity is required to invest",
            )

        # Calculate the amount to be paid by the user for the requested token amount.
        unit_price = Decimal(str(project["target_amount"])) / Decimal("100") #type: ignore
        amount_paid = unit_price * request.token_amount
        if Decimal(str(user["balance"])) < amount_paid: #type: ignore
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient user balance",
            )
            
    
        # Check if the investment would exceed the 100-token supply limit
        new_total_supply = int(project["total_supply"]) + request.token_amount #type: ignore
        if new_total_supply > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This investment would exceed the 100-token supply limit",
            )

        # Transfer tokens from the operator treasury to the investing user's Hedera account.
        try:
            transfer = transfer_tokens(
                str(project["hedera_token_id"]), #type: ignore
                str(user["hedera_id"]), #type: ignore
                request.token_amount,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not transfer Hedera tokens: {exc}",
            ) from exc

        transaction_id = transfer["transaction_id"]
        
        # Update the user's balance in the users table

        cursor.execute(
            """
            UPDATE users
            SET balance = balance - %s
            WHERE id = %s
            """,
            (amount_paid, request.user_id),
        )
        
        # Update the token_balances table

        cursor.execute(
            """
            INSERT INTO token_balances (user_id, token_id, amount)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, token_id)
            DO UPDATE SET amount = token_balances.amount + EXCLUDED.amount
            """,
            (request.user_id, project["token_id"], request.token_amount), #type: ignore
        )
        
        #Update the total_supply

        cursor.execute(
            """
            UPDATE tokens
            SET total_supply = total_supply + %s
            WHERE id = %s
            """,
            (request.token_amount, project["token_id"]), #type: ignore
        )
        
        
        # Insert the investment record into the investments table

        cursor.execute(
            """
            INSERT INTO investments (
                project_id,
                investor_id,
                token_amount,
                amount_paid,
                transaction_id
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                request.project_id,
                request.user_id,
                request.token_amount,
                amount_paid,
                transaction_id,
            ),
        )
        investment = cursor.fetchone()
        
        # Insert transaction into token_transactions table
        cursor.execute(
            """
            INSERT INTO token_transactions (
                token_id,
                from_id,
                to_id,
                amount,
                hedera_trans_id
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                project["token_id"], #type: ignore
                0,
                request.user_id,
                request.token_amount,
                transaction_id,
            ),
        )

    return {
        "investment_id": investment["id"] if investment else None,  #type: ignore
        "project_id": request.project_id,
        "user_id": request.user_id,
        "token_amount": request.token_amount,
        "amount_paid": amount_paid,
        "transaction_id": transaction_id,
        "total_supply": new_total_supply,
        "project_status": "active" if new_total_supply == 100 else "funding",
    }


@router.get("/{investor_id}")
def get_investments(
    investor_id: int,
    connection: Connection = Depends(get_db),
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM investments AS i
            WHERE i.investor_id = %s
            ORDER BY i.id
            """,
            (investor_id,),
        )
        investments = cursor.fetchall()

    return investments
