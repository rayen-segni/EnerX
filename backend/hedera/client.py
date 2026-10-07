from hiero_sdk_python import AccountId, Client, Network, PrivateKey
from app.config import settings

operator_id = AccountId.from_string(settings.OPERATOR_ID)
operator_key = PrivateKey.from_string_ecdsa(settings.OPERATOR_KEY)

def get_client():
    client = Client(Network(settings.HEDERA_NETWORK))
    
    # Hedera Portal Testnet account: signs and pays for the transaction.
    client.set_operator(operator_id, operator_key)
    return client