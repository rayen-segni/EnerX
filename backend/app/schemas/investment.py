from pydantic import BaseModel, Field


class InvestmentCreateRequest(BaseModel):
    user_id: int
    project_id: int
    token_amount: int = Field(gt=0)