from fastapi import HTTPException, status
from hiero_sdk_python import PrivateKey
from hiero_did_sdk_python import HederaDid

from hedera.client import get_client


async def create_user_did(*, private_key_hex: str, profile_url: str) -> str:
    """Register a DID from an ECDSA HEX key and expose its profile service."""
    if not private_key_hex:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPERATOR_KEY is not configured",
        )

    try:
        private_key = PrivateKey.from_string_ecdsa(private_key_hex)
        private_key_der = private_key.to_string_der()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OPERATOR_KEY is not a valid ECDSA HEX key: {exc}",
        ) from exc

    client = get_client()

    did = HederaDid(
        client=client,
        private_key_der=private_key_der,
    )

    await did.register()

    await did.add_or_update_service(
        id_=f"{did.identifier}#service-1",
        service_type="Profile", #type: ignore
        service_endpoint=profile_url,
    )

    return did.identifier #type: ignore