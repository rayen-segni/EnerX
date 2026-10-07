from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection
from decimal import Decimal

from app.database import get_db
from app.schemas.marketplace import MarketplaceListingCreateRequest, MarketplacePurchaseRequest, MarketplacePurchaseResponse
from hedera.token_service import transfer_tokens_between_accounts
from app.config import settings

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


@router.post(
    "/list",
    status_code=status.HTTP_201_CREATED,
)
def create_listing(
    request: MarketplaceListingCreateRequest,
    connection: Connection = Depends(get_db),
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, amount
            FROM token_balances
            WHERE user_id = %s AND token_id = %s
            FOR UPDATE
            """,
            (request.user_id, request.token_id),
        )
        token_balance = cursor.fetchone()

        if token_balance is None or token_balance["amount"] < request.amount: #type: ignore
            available = token_balance["amount"] if token_balance else 0 #type: ignore
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient token balance: available {available}, "
                    f"requested {request.amount}"
                ),
            )
            

        cursor.execute(
            """
            INSERT INTO token_listings (tk_balance, unit_price, offered_tokens)
            VALUES (%s, %s, %s)
            """,
            (token_balance["id"], request.u_price, request.amount),  #type: ignore
        )

@router.post(
    "/list/buy",
    response_model=MarketplacePurchaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def purchase_listing(
    request: MarketplacePurchaseRequest,
    connection: Connection = Depends(get_db),
):
    
    # Fetch the listing and its associated token balance and token data, locking the rows for update.
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                listing.id AS listing_id,
                listing.unit_price,
                listing.offered_tokens,
                seller_balance.id AS seller_token_balance_id,
                seller_balance.token_id,
                seller_balance.user_id AS seller_id,
                seller_balance.amount AS seller_token_amount,
                token.hedera_token_id,
                token.project_id,
                seller.hedera_id AS seller_hedera_id
            FROM token_listings AS listing
            JOIN token_balances AS seller_balance
                ON seller_balance.id = listing.tk_balance
            JOIN tokens AS token ON token.id = seller_balance.token_id
            JOIN users AS seller ON seller.id = seller_balance.user_id
            WHERE listing.id = %s
            FOR UPDATE OF listing, seller_balance
            """,
            (request.listing_id,),
        )
        listing = cursor.fetchone()
        

        # Check if the seller doesn't want to sell their own listing
        if request.user_id == listing["seller_id"]: #type: ignore
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot buy your own listing",
            )

        # Check if the amount requested is available and the seller has enough tokens to fulfill the listing
        if request.amount > listing["offered_tokens"]: #type: ignore
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Requested {request.amount} tokens, but only "
                    f"{listing['offered_tokens']} are offered" #type: ignore
                ),
            )

        # Check if the seller has enough tokens to fulfill the listing
        if request.amount > listing["seller_token_amount"]: #type: ignore
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The seller no longer has enough tokens to fulfill this listing",
            )

        # Fetch both the buyer and seller users, locking their rows for update.
        cursor.execute(
            """
            SELECT id, hedera_id, balance
            FROM users
            WHERE id IN (%s, %s)
            ORDER BY id
            FOR UPDATE
            """,
            (request.user_id, listing["seller_id"]), #type: ignore
        )
        users = {user["id"]: user for user in cursor.fetchall()} #type: ignore
        buyer = users.get(request.user_id) #type: ignore
        seller = users.get(listing["seller_id"]) #type: ignore
        

        amount_paid = Decimal(str(listing["unit_price"])) * request.amount #type: ignore
        # users.balance is an integer column, so reject fractional currency amounts
        # instead of allowing PostgreSQL to round them during the update.
        if amount_paid != amount_paid.to_integral_value():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The total price must be a whole number with the current integer balance schema",
            )

        # Check if the buyer has enough balance to pay for the tokens
        if buyer["balance"] < amount_paid: #type: ignore
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient buyer balance",
            )

        # Check if the seller's Hedera signing key is configured
        seller_private_key = settings.get_users.get(listing["seller_id"]) #type: ignore
        if not seller_private_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="The seller's Hedera signing key is not configured",
            )

        # Execute the Hedera Token transfer from the seller to the buyer
        try:
            transfer = transfer_tokens_between_accounts(
                str(listing["hedera_token_id"]), #type: ignore
                str(listing["seller_hedera_id"]), #type: ignore
                seller_private_key,
                str(buyer["hedera_id"]), #type: ignore
                request.amount,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not transfer Hedera tokens: {exc}",
            ) from exc

        transaction_id = transfer["transaction_id"]

        # Update the buyer's and seller's balances and token balances
        cursor.execute(
            "UPDATE users SET balance = balance - %s WHERE id = %s",
            (int(amount_paid), request.user_id),
        )
        cursor.execute(
            "UPDATE users SET balance = balance + %s WHERE id = %s",
            (int(amount_paid), listing["seller_id"]), #type: ignore
        )

        # Update the token balances for both the buyer and seller
        cursor.execute(
            """
            UPDATE token_balances
            SET amount = amount - %s
            WHERE id = %s
            """,
            (request.amount, listing["seller_token_balance_id"]), #type: ignore
        )
        cursor.execute(
            """
            INSERT INTO token_balances (token_id, user_id, amount)
            VALUES (%s, %s, %s)
            ON CONFLICT (token_id, user_id)
            DO UPDATE SET amount = token_balances.amount + EXCLUDED.amount
            """,
            (listing["token_id"], request.user_id, request.amount), #type: ignore
        )
        
        # Update the investment of the buyer in the investments table
        cursor.execute(
            """
            UPDATE investments
            SET token_amount = amount_paid - %s, token_amount = token_amount - %s
            WHERE id = %s
            """,
            (int(amount_paid), int(amount_paid), investment["id"], request.amount), #type: ignore
        )

        # Record the investment and the token transaction in the database
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
                listing["project_id"], #type: ignore
                request.user_id,
                request.amount,
                amount_paid,
                transaction_id,
            ),
        )
        investment = cursor.fetchone()

        # Record the token transaction in the token_transactions table
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
                listing["token_id"], #type: ignore
                listing["seller_id"], #type: ignore
                request.user_id,
                request.amount,
                transaction_id,
            ),
        )

        # Update the listing's offered tokens and return the remaining amount
        cursor.execute(
            """
            UPDATE token_listings
            SET offered_tokens = offered_tokens - %s
            WHERE id = %s
            RETURNING offered_tokens
            """,
            (request.amount, request.listing_id),
        )
        updated_listing = cursor.fetchone()

    return {
        "investment_id": investment["id"] if investment else None, #type: ignore
        "listing_id": request.listing_id,
        "buyer_id": request.user_id,
        "seller_id": listing["seller_id"], #type: ignore
        "token_id": listing["token_id"], #type: ignore
        "amount": request.amount,
        "amount_paid": amount_paid,
        "transaction_id": transaction_id,
        "remaining_offered_tokens": updated_listing["offered_tokens"], #type: ignore
    }