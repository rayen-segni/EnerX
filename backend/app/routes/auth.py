"""
EnerX Backend - Auth Routes
Simulated authentication using Hedera Portal users from PORTAL_USERS_PATH.
"""

import base64
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, Header, HTTPException, status
from hiero_sdk_python import PrivateKey
from psycopg import Connection

from app.config import settings
from app.database import get_db
from app.schemas.auth import DIDCreateRequest, DIDCreateResponse
from app.schemas.verification import (
    ChallengeRequest,
    ChallengeResponse,
    VerificationStatusResponse,
    VerifyChallengeRequest,
)
from app.schemas.credential import CredentialResponse, IssueCredentialRequest
from hedera.did_service import create_user_did

router = APIRouter(prefix="/auth", tags=["Auth"])


def _load_portal_users() -> list[Dict[str, Any]]:
    """Load users from the simulated portal users JSON file."""
    setting = settings
    try:
        with open(settings.PORTAL_USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("users", [])
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portal users file not found !",
        )


@router.get("/{user_id}", summary="Simulated Portal Login by User ID")
def login(user_id: int) -> Dict[str, Any]:
    """
    Returns the simulated Hedera Portal user matching the given user_id.

    user_id corresponds to the 'user_id' field in data/hedera_portal_users.json.
    """
    users = _load_portal_users()

    for user in users:
        if user.get("user_id") == user_id:
            return user

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No portal user found with user_id={user_id}",
    )


@router.post("/did", response_model=DIDCreateResponse, summary="Create a Hedera DID")
async def create_did(
    request: DIDCreateRequest,
    connection: Connection = Depends(get_db),
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, hedera_id, did, legal_name, email
            FROM users
            WHERE id = %s
            FOR UPDATE
            """,
            (request.user_id,),
        )
        user = cursor.fetchone()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {request.user_id} was not found",
            )

        if (
            str(user["hedera_id"]) != request.hedera_id
            or user["legal_name"] != request.legal_name
            or user["email"] != str(request.email)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The identity data does not match the registered user",
            )

        if user.get("did"):
            # Hackathon MVP: one successful identity check grants the common
            # User permission set used by both investing and project creation.
            cursor.execute(
                """
                UPDATE users
                SET identity_verified = TRUE,
                    investor_verified = TRUE,
                    owner_verified = TRUE,
                    verification_updated_at = %s
                WHERE id = %s
                """,
                (datetime.now(timezone.utc), request.user_id),
            )
            return {"user_id": request.user_id, "did": user["did"]}

        user_private_key = settings.get_users.get(request.user_id)
        if not user_private_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"No private key is configured for user {request.user_id}",
            )

        try:
            did = await create_user_did(
                private_key_hex=user_private_key,
                profile_url=f"{settings.DID_SERVICE_ENDPOINT}/user/{request.user_id}",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not register the DID on Hedera: {exc}",
            ) from exc

        cursor.execute(
            """
            UPDATE users
            SET did = %s,
                identity_verified = TRUE,
                investor_verified = TRUE,
                owner_verified = TRUE,
                verification_updated_at = %s
            WHERE id = %s
            """,
            (did, datetime.now(timezone.utc), request.user_id),
        )

    return {"user_id": request.user_id, "did": did}


@router.post("/challenge", response_model=ChallengeResponse)
def create_challenge(
    request: ChallengeRequest,
    connection: Connection = Depends(get_db),
):
    challenge_id = uuid.uuid4()
    nonce = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE id = %s", (request.user_id,))
        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {request.user_id} was not found",
            )
        cursor.execute(
            """
            INSERT INTO auth_challenges (id, user_id, nonce, expires_at)
            VALUES (%s, %s, %s, %s)
            """,
            (challenge_id, request.user_id, nonce, expires_at),
        )

    return {
        "challenge_id": str(challenge_id),
        "nonce": nonce,
        "expires_at": expires_at.isoformat(),
    }


@router.post("/verify", response_model=VerificationStatusResponse)
def verify_challenge(
    request: VerifyChallengeRequest,
    connection: Connection = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    try:
        signature = base64.b64decode(request.signature, validate=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid signature encoding: {exc}",
        ) from exc

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.nonce, c.expires_at, c.consumed_at,
                   u.id, u.did, u.investor_verified, u.owner_verified
            FROM auth_challenges c
            JOIN users u ON u.id = c.user_id
            WHERE c.id = %s AND c.user_id = %s
            FOR UPDATE
            """,
            (request.challenge_id, request.user_id),
        )
        challenge = cursor.fetchone()
        if challenge is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge not found",
            )
        if challenge["consumed_at"] is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Challenge has already been used",
            )
        if challenge["expires_at"] <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Challenge has expired",
            )
        if challenge["nonce"] != request.nonce:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Challenge nonce does not match",
            )
        configured_key = settings.get_users.get(request.user_id)
        if not configured_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"No identity key is configured for user {request.user_id}",
            )
        try:
            identity_key = PrivateKey.from_string(configured_key)
            expected_public_key = identity_key.public_key().to_string()
            if request.public_key != expected_public_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="The public key is not the registered identity key",
                )
            valid = identity_key.public_key().verify(
                request.nonce.encode("utf-8"),
                signature,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cryptographic proof: {exc}",
            ) from exc
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Signature does not prove control of the supplied public key",
            )

        cursor.execute(
            """
            UPDATE auth_challenges
            SET consumed_at = %s
            WHERE id = %s
            """,
            (now, request.challenge_id),
        )
        cursor.execute(
            """
            UPDATE users
            SET identity_public_key = %s,
                identity_verified = TRUE,
                verification_updated_at = %s
            WHERE id = %s
            RETURNING id, did, identity_verified,
                      investor_verified, owner_verified
            """,
            (request.public_key, now, request.user_id),
        )
        user = cursor.fetchone()

    return {
        "user_id": user["id"],
        "did": user["did"],
        "identity_verified": user["identity_verified"],
        "investor_verified": user["investor_verified"],
        "owner_verified": user["owner_verified"],
    }


@router.get("/verification/{user_id}", response_model=VerificationStatusResponse)
def get_verification_status(
    user_id: int,
    connection: Connection = Depends(get_db),
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, did, identity_verified,
                   investor_verified, owner_verified
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        user = cursor.fetchone()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} was not found",
        )
    return {
        "user_id": user["id"],
        "did": user["did"],
        "identity_verified": user["identity_verified"],
        "investor_verified": user["investor_verified"],
        "owner_verified": user["owner_verified"],
    }


@router.post("/credentials/issue", response_model=CredentialResponse)
def issue_credential(
    request: IssueCredentialRequest,
    connection: Connection = Depends(get_db),
    issuer_token: str | None = Header(default=None, alias="X-Verification-Token"),
):
    if not settings.VERIFICATION_ISSUER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The verification issuer is not configured",
        )
    if issuer_token != settings.VERIFICATION_ISSUER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the configured verification issuer can issue credentials",
        )
    if request.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credential expiration must be in the future",
        )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, did, identity_verified
            FROM users
            WHERE id = %s
            FOR UPDATE
            """,
            (request.user_id,),
        )
        user = cursor.fetchone()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {request.user_id} was not found",
            )
        if not user["identity_verified"] or not user["did"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user's cryptographic identity must be verified first",
            )

        credential_id = uuid.uuid4()
        issued_at = datetime.now(timezone.utc)
        issuer = f"did:hedera:testnet:{settings.OPERATOR_ID}"
        credential = {
            "id": str(credential_id),
            "type": ["VerifiableCredential", request.credential_type],
            "issuer": issuer,
            "issuanceDate": issued_at.isoformat(),
            "expirationDate": request.expires_at.isoformat(),
            "credentialSubject": {
                "id": user["did"],
                "documentHash": request.document_hash,
            },
        }
        payload = json.dumps(
            credential,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        try:
            issuer_key = PrivateKey.from_string_ecdsa(settings.OPERATOR_KEY)
            signature = base64.b64encode(issuer_key.sign(payload)).decode("ascii")
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not sign the credential with OPERATOR_KEY: {exc}",
            ) from exc

        cursor.execute(
            """
            INSERT INTO verifiable_credentials (
                id, subject_user_id, credential_type, issuer,
                document_hash, credential_json, signature, issued_at, expires_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                credential_id,
                request.user_id,
                request.credential_type,
                issuer,
                request.document_hash,
                json.dumps(credential),
                signature,
                issued_at,
                request.expires_at,
            ),
        )
        flag = (
            "investor_verified"
            if request.credential_type == "InvestorVerification"
            else "owner_verified"
        )
        cursor.execute(
            f"""
            UPDATE users
            SET {flag} = TRUE, verification_updated_at = %s
            WHERE id = %s
            """,
            (issued_at, request.user_id),
        )

    return {
        "credential_id": str(credential_id),
        "user_id": request.user_id,
        "credential_type": request.credential_type,
        "issuer": issuer,
        "subject_did": user["did"],
        "document_hash": request.document_hash,
        "issued_at": issued_at,
        "expires_at": request.expires_at,
        "signature": signature,
    }
