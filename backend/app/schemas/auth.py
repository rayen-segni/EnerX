"""Authentication-related request and response schemas."""

import datetime

from pydantic import BaseModel, EmailStr, Field


class DIDCreateRequest(BaseModel):
    user_id: int = Field(gt=0)
    legal_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    hedera_id: str = Field(pattern=r"^\d+\.\d+\.\d+$")


class DIDCreateResponse(BaseModel):
    user_id: int
    did: str

class UserPatchRequest(BaseModel):
    id: int
    hedera_id: str | None = None
    did: str | None = None
    legal_name: str | None = None
    email: str | None = None
    phone: str | None = None
    balance: int | None = None



class UserResponse(BaseModel):
    id: int
    hedera_id: str
    did: str | None
    legal_name: str
    email: str
    phone: str | None
    balance: int
    created_at: datetime.datetime