from hiero_did_sdk_python import HederaDid

from hedera.client import get_client


async def create_user_did(user: dict):
    client = get_client()

    # This key identifies this user’s DID.
    did = HederaDid(
        client=client,
        private_key_der=user["did_private_key_der"],
    )

    await did.register()

    await did.add_or_update_service(
        id_=f"{did.identifier}#service-1",
        service_type="Profile", #type: ignore
        service_endpoint=user["profile_url"],
    )

    return did.identifier