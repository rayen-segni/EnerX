from decimal import Decimal

from pydantic import BaseModel, Field


class MarketplaceListingCreateRequest(BaseModel):
    user_id: int = Field(gt=0)
    token_id: int = Field(gt=0)
    u_price: Decimal = Field(gt=0)
    amount: int = Field(gt=0)


class MarketplaceListingResponse(BaseModel):
    id: int
    user_id: int
    token_id: int
    u_price: Decimal
    amount: int
    
class MarketplacePurchaseRequest(BaseModel):
    user_id: int = Field(gt=0)
    listing_id: int = Field(gt=0)
    amount: int = Field(gt=0)


class MarketplacePurchaseResponse(BaseModel):
    investment_id: int | None
    listing_id: int
    buyer_id: int
    seller_id: int
    token_id: int
    amount: int
    amount_paid: Decimal
    transaction_id: str
    remaining_offered_tokens: int