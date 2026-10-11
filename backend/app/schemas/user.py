from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class UserTokenBalanceResponse(BaseModel):
    id: int
    token_id: int
    amount: int
    hedera_token_id: str
    token_name: str
    token_symbol: str
    project_id: int
    project_name: str


class UserProjectResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    description: str | None
    target_amount: int
    status: str
    token_id: int
    hedera_token_id: str
    token_name: str
    token_symbol: str
    total_supply: int
    commitment_file_id: str | None
    commitment_transaction_id: str | None


class UserDetailsResponse(BaseModel):
    id: int
    hedera_id: str
    did: str | None
    legal_name: str
    email: str | None
    phone: str | None
    balance: Decimal
    created_at: datetime | None
    token_balances: list[UserTokenBalanceResponse]
    projects: list[UserProjectResponse]
