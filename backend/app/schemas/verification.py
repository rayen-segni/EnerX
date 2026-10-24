from pydantic import BaseModel, Field


class ChallengeRequest(BaseModel):
    user_id: int = Field(gt=0)


class ChallengeResponse(BaseModel):
    challenge_id: str
    nonce: str
    expires_at: str


class VerifyChallengeRequest(BaseModel):
    user_id: int = Field(gt=0)
    challenge_id: str
    nonce: str = Field(min_length=16, max_length=512)
    public_key: str = Field(min_length=16, max_length=512)
    signature: str = Field(min_length=16, max_length=2048)


class VerificationStatusResponse(BaseModel):
    user_id: int
    did: str | None
    identity_verified: bool
    investor_verified: bool
    owner_verified: bool
