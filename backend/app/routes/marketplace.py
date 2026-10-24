from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection
from decimal import Decimal

from app.database import get_db
from app.schemas.marketplace import (
    MarketplaceListingCreateRequest,
    MarketplaceListingResponse,
    MarketplacePurchaseRequest,
    MarketplacePurchaseResponse,
)
from hedera.token_service import transfer_tokens_between_accounts
from app.config import settings

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


@router.get("/listings")
def get_active_listings(
    connection: Connection = Depends(get_db),
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                listing.id,
                seller_balance.user_id,
                seller_balance.token_id,
                token.project_id,
                listing.unit_price AS u_price,
                listing.offered_tokens AS amount
            FROM token_listings listing
            JOIN token_balances seller_balance
                ON seller_balance.id = listing.tk_balance
            JOIN tokens token
                ON token.id = seller_balance.token_id
            WHERE listing.cancelled_at IS NULL
              AND listing.offered_tokens > 0
            ORDER BY listing.id DESC
            """
        )
        return cursor.fetchall()


@router.post(
    "/list",
    response_model=MarketplaceListingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_listing(
    request: MarketplaceListingCreateRequest,
    connection: Connection = Depends(get_db),
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                tb.id,
                tb.amount,
                u.identity_verified,
                EXISTS (
                    SELECT 1
                    FROM verifiable_credentials vc
                    WHERE vc.subject_user_id = u.id
                      AND vc.credential_type = 'InvestorVerification'
                      AND vc.revoked_at IS NULL
                      AND vc.expires_at > CURRENT_TIMESTAMP
                ) AS investor_verified
            FROM token_balances tb
            JOIN users u ON u.id = tb.user_id
            WHERE tb.user_id = %s AND tb.token_id = %s
            FOR UPDATE OF tb, u
            """,
            (request.user_id, request.token_id),
        )
        token_balance = cursor.fetchone()

        if token_balance is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The seller does not hold this token",
            )
        if not token_balance["identity_verified"]: # type: ignore
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A verified user identity is required to list tokens",
            )

        cursor.execute(
            """
            SELECT COALESCE(SUM(offered_tokens), 0) AS reserved
            FROM token_listings
            WHERE tk_balance = %s
              AND cancelled_at IS NULL
              AND offered_tokens > 0
            """,
            (token_balance["id"],), # type: ignore
        )
        reserved = int(cursor.fetchone()["reserved"]) # type: ignore
        available = int(token_balance["amount"]) - reserved # type: ignore
        if available < request.amount:
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
            RETURNING id
            """,
            (token_balance["id"], request.u_price, request.amount),  #type: ignore
        )
        listing = cursor.fetchone()

    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create marketplace listing",
        )

    return {
        "id": listing["id"],  # type: ignore[index]
        "user_id": request.user_id,
        "token_id": request.token_id,
        "u_price": request.u_price,
        "amount": request.amount,
    }

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
            SELECT token.project_id
            FROM token_listings AS listing
            JOIN token_balances AS seller_balance
                ON seller_balance.id = listing.tk_balance
            JOIN tokens AS token ON token.id = seller_balance.token_id
            WHERE listing.id = %s
            """,
            (request.listing_id,),
        )
        listing_project = cursor.fetchone()
        if listing_project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Listing {request.listing_id} was not found",
            )

        cursor.execute(
            "SELECT id FROM projects WHERE id = %s FOR UPDATE",
            (listing_project["project_id"],),  # type: ignore[index]
        )

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
                seller.hedera_id AS seller_hedera_id,
                buyer.identity_verified AS buyer_identity_verified,
                EXISTS (
                    SELECT 1
                    FROM verifiable_credentials vc
                    WHERE vc.subject_user_id = buyer.id
                      AND vc.credential_type = 'InvestorVerification'
                      AND vc.revoked_at IS NULL
                      AND vc.expires_at > CURRENT_TIMESTAMP
                ) AS buyer_investor_verified
            FROM token_listings AS listing
            JOIN token_balances AS seller_balance
                ON seller_balance.id = listing.tk_balance
            JOIN tokens AS token ON token.id = seller_balance.token_id
            JOIN users AS seller ON seller.id = seller_balance.user_id
            JOIN users AS buyer ON buyer.id = %s
            WHERE listing.id = %s
            FOR UPDATE OF listing, seller_balance
            """,
            (request.user_id, request.listing_id),
        )
        listing = cursor.fetchone()
        if listing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Listing {request.listing_id} was not found",
            )
        if not listing["buyer_identity_verified"]: # type: ignore
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A verified user identity is required to buy tokens",
            )
        

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
            (amount_paid, request.user_id),
        )
        cursor.execute(
            "UPDATE users SET balance = balance + %s WHERE id = %s",
            (amount_paid, listing["seller_id"]), #type: ignore
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


@router.delete("/list/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_listing(
    listing_id: int,
    user_id: int,
    connection: Connection = Depends(get_db),
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT listing.id
            FROM token_listings listing
            JOIN token_balances tb ON tb.id = listing.tk_balance
            WHERE listing.id = %s
              AND tb.user_id = %s
              AND listing.cancelled_at IS NULL
              AND listing.offered_tokens > 0
            FOR UPDATE OF listing
            """,
            (listing_id, user_id),
        )
        listing = cursor.fetchone()
        if listing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active listing not found for this seller",
            )
        cursor.execute(
            """
            UPDATE token_listings
            SET cancelled_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (listing_id,),
        )
    return None
