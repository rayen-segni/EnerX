from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection
from psycopg.rows import DictRow

from app.config import settings
from app.database import get_db
from app.schemas.production import ProductionCreateRequest
from app.services.production_service import TokenHolder, allocate_revenue
from hedera.contract_service import record_revenue_distribution

router = APIRouter(prefix="/prod", tags=["Production"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_production(
    request: ProductionCreateRequest,
    connection: Connection[DictRow] = Depends(get_db),
):
    if not settings.HEDERA_REVENUE_CONTRACT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HEDERA_REVENUE_CONTRACT_ID is not configured",
        )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.id, t.id AS token_id
            FROM projects AS p
            JOIN tokens AS t ON t.project_id = p.id
            WHERE p.id = %s
            FOR UPDATE OF p, t
            """,
            (request.project_id,),
        )
        project = cursor.fetchone()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {request.project_id} or its token was not found",
            )

        cursor.execute(
            """
            SELECT
                tb.id AS token_balance_id,
                tb.user_id,
                tb.amount AS token_amount,
                u.hedera_id
            FROM token_balances AS tb
            JOIN users AS u ON u.id = tb.user_id
            WHERE tb.token_id = %s AND tb.amount > 0
            ORDER BY tb.user_id
            FOR UPDATE OF tb
            """,
            (project["token_id"],),  # type: ignore[index]
        )
        holders = [
            TokenHolder(
                token_balance_id=int(row["token_balance_id"]),
                user_id=int(row["user_id"]),
                hedera_id=str(row["hedera_id"]),
                token_amount=int(row["token_amount"]),
            )
            for row in cursor.fetchall()
        ]
        owned_tokens = sum(holder.token_amount for holder in holders)
        if owned_tokens != 100:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Revenue distribution requires exactly 100 owned project tokens; "
                    f"found {owned_tokens}"
                ),
            )

        amount_minor = int(request.revenue * 100)
        allocations = allocate_revenue(holders, amount_minor)

        cursor.execute(
            """
            INSERT INTO energy_productions (project_id, energy_kwh, revenue)
            VALUES (%s, %s, %s)
            RETURNING id, production_date
            """,
            (request.project_id, request.energy_kwh, request.revenue),
        )
        production = cursor.fetchone()
        if production is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create the energy production record",
            )

        try:
            contract_result = record_revenue_distribution(
                str(request.project_id),
                allocations,
                amount_minor,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not confirm revenue distribution on Hedera: {exc}",
            ) from exc

        distribution_results = []
        for allocation in allocations:
            amount = Decimal(allocation.amount_minor) / Decimal(100)
            cursor.execute(
                """
                INSERT INTO distributions (token_balance_id, amount, production_id)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (
                    allocation.token_balance_id,
                    amount,
                    production["id"],  # type: ignore[index]
                ),
            )
            distribution = cursor.fetchone()

            cursor.execute(
                "UPDATE users SET balance = balance + %s WHERE id = %s",
                (amount, allocation.user_id),
            )
            distribution_results.append(
                {
                    "distribution_id": distribution["id"] if distribution else None,  # type: ignore[index]
                    "token_balance_id": allocation.token_balance_id,
                    "user_id": allocation.user_id,
                    "token_amount": allocation.token_amount,
                    "amount": amount,
                }
            )

    return {
        "production_id": production["id"],  # type: ignore[index]
        "project_id": request.project_id,
        "production_date": production["production_date"],  # type: ignore[index]
        "energy_kwh": request.energy_kwh,
        "revenue": request.revenue,
        "contract_transaction_id": contract_result["transaction_id"],
        "contract_status": contract_result["status"],
        "distributions": distribution_results,
    }