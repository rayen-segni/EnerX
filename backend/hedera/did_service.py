from hiero_did_sdk_python import HederaDid
from fastapi import HTTPException, status
from hedera.client import get_client


async def create_user_did(*, private_key_der: str, profile_url: str) -> str:
    """Register a DID and expose the user's profile endpoint as a DID service."""
    if not private_key_der:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HEDERA_OPERATOR_KEY_DER is not configured",
        )

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