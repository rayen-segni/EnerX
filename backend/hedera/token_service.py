from hiero_sdk_python import (
    AccountId,
    TokenCreateTransaction,
    TransferTransaction,
)

from hedera.client import (
    get_client,
    operator_id as configured_operator_id,
    operator_key as configured_operator_key,
)


def create_token(
    token_name: str,
    token_symbol: str,
    user_account_id: str,
) -> dict[str, str]:
    """Create 100 tokens in the operator treasury and transfer 30 to the user."""
    client = get_client()
    recipient_id = AccountId.from_string(user_account_id)

    create_tx = (
        TokenCreateTransaction()
        .set_token_name(token_name)
        .set_token_symbol(token_symbol)
        .set_decimals(2)
        .set_initial_supply(100 * 10**2)
        .set_treasury_account_id(configured_operator_id)
        .set_admin_key(configured_operator_key.public_key())
        .set_supply_key(configured_operator_key.public_key())
        .freeze_with(client)
    )
    creation_transaction_id = str(create_tx.transaction_id)

    create_tx.sign(configured_operator_key)
    creation_receipt = create_tx.execute(client)
    token_id = creation_receipt.token_id

    transfer_tx = (
        TransferTransaction()
        .add_token_transfer(token_id, configured_operator_id, -(30 * 10**2)) #type: ignore
        .add_token_transfer(token_id, recipient_id, 30 * 10**2) #type: ignore
        .freeze_with(client)
    )
    transfer_transaction_id = str(transfer_tx.transaction_id)

    transfer_tx.sign(configured_operator_key)
    transfer_tx.execute(client)

    return {
        "token_id": str(token_id),
        "creation_transaction_id": creation_transaction_id,
        "transfer_transaction_id": transfer_transaction_id,
    }
    
from hiero_sdk_python import AccountId, PrivateKey, TokenId, TransferTransaction

from hedera.client import get_client, operator_id, operator_key


def transfer_tokens(
    hedera_token_id: str,
    user_account_id: str,
    token_amount: int,
) -> dict[str, str]:
    """Transfer whole tokens from the operator treasury to a user's account."""
    client = get_client()
    token_id = TokenId.from_string(hedera_token_id)
    recipient_id = AccountId.from_string(user_account_id)

    # Tokens are configured with two decimal places, so convert whole tokens
    # to the token's smallest units for the Hedera transfer transaction.
    amount_in_smallest_units = token_amount * 10**2

    transfer_tx = (
        TransferTransaction()
        .add_token_transfer(token_id, operator_id, -amount_in_smallest_units)
        .add_token_transfer(token_id, recipient_id, amount_in_smallest_units)
        .freeze_with(client)
    )
    transaction_id = str(transfer_tx.transaction_id)

    transfer_tx.sign(operator_key)
    receipt = transfer_tx.execute(client)

    return {
        "transaction_id": transaction_id,
        "status": str(receipt.status),
    }


def transfer_tokens_between_accounts(
    hedera_token_id: str,
    seller_account_id: str,
    seller_private_key: str,
    buyer_account_id: str,
    token_amount: int,
) -> dict[str, str]:
    """Transfer whole tokens from a seller to a buyer on Hedera."""
    client = get_client()
    token_id = TokenId.from_string(hedera_token_id)
    seller_id = AccountId.from_string(seller_account_id)
    seller_key = PrivateKey.from_string_ecdsa(seller_private_key)
    buyer_id = AccountId.from_string(buyer_account_id)
    amount_in_smallest_units = token_amount * 10**2
    
    transfer_tx = (
        TransferTransaction()
        .add_token_transfer(token_id, seller_id, -amount_in_smallest_units)
        .add_token_transfer(token_id, buyer_id, amount_in_smallest_units)
        .freeze_with(client)
    )
    transaction_id = str(transfer_tx.transaction_id)
    transfer_tx.sign(seller_key)
    receipt = transfer_tx.execute(client)

    return {
        "transaction_id": transaction_id,
        "status": str(receipt.status),
    }