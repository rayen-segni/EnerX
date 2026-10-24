from datetime import datetime

from pydantic import BaseModel, Field


class IssueCredentialRequest(BaseModel):
    user_id: int = Field(gt=0)
    credential_type: str = Field(
        pattern=r"^(InvestorVerification|ProjectOwnerVerification)$"
    )
    document_hash: str = Field(min_length=64, max_length=128)
    expires_at: datetime


class CredentialResponse(BaseModel):
    credential_id: str
    user_id: int
    credential_type: str
    issuer: str
    subject_did: str
    document_hash: str
    issued_at: datetime
    expires_at: datetime
    signature: str
