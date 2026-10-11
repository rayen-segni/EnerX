from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    user_id: int
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=512)
    target_amount: int = Field(gt=0)
    token_name: str = Field(min_length=1, max_length=255)
    token_symbol: str = Field(min_length=1, max_length=50)


class ProjectCreateResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    description: str | None
    target_amount: int
    status: str
    token_id: int | None
    hedera_token_id: str
    token_name: str
    token_symbol: str
    total_supply: int
    commitment_file_id: str
    commitment_transaction_id: str

class ProjectResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    description: str | None
    token_name: str
    token_symbol: str
    token_id: int | None
    token_supply: int
    target_amount: int
    status: str
    commitment_file_id: str | None
    commitment_transaction_id: str | None
