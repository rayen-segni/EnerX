from collections.abc import Sequence

from hiero_sdk_python import (
    AccountId,
    ContractExecuteTransaction,
    ContractFunctionParameters,
)
from hiero_sdk_python.contract.contract_id import ContractId
from hiero_sdk_python.hapi.services.response_code_pb2 import ResponseCodeEnum

from app.config import settings
from app.services.production_service import DistributionAllocation
from hedera.client import get_client, operator_key


def _response_code_name(status: int | None) -> str:
    if status is None:
        raise RuntimeError("Hedera transaction receipt did not include a status")
    return ResponseCodeEnum.Name(status)


def record_revenue_distribution(
    project_id: str,
    allocations: Sequence[DistributionAllocation],
    total_amount_minor: int,
) -> dict[str, str]:
    """Record a confirmed payout snapshot in the configured HSCS contract."""
    contract_id_value = settings.HEDERA_REVENUE_CONTRACT_ID
    if not contract_id_value:
        raise RuntimeError("HEDERA_REVENUE_CONTRACT_ID is not configured")
    if total_amount_minor <= 0:
        raise ValueError("The total distribution amount must be positive")
    if (
        not allocations
        or any(item.token_amount <= 0 for item in allocations)
        or sum(item.token_amount for item in allocations) != 100
    ):
        raise ValueError("Distribution allocations must cover exactly 100 tokens")
    if sum(item.amount_minor for item in allocations) != total_amount_minor:
        raise ValueError("Payout allocations must sum to the total distribution amount")

    recipients: list[str | bytes] = [
        AccountId.from_string(item.hedera_id).to_evm_address()
        for item in allocations
    ]
    parameters = (
        ContractFunctionParameters("recordDistribution")
        .add_string(project_id)
        .add_address_array(recipients)
        .add_uint256_array([item.token_amount for item in allocations])
        .add_uint256(total_amount_minor)
    )
    client = get_client()
    transaction = (
        ContractExecuteTransaction()
        .set_contract_id(ContractId.from_string(contract_id_value))
        .set_gas(5_000_000)
        .set_function("recordDistribution", parameters)
        .freeze_with(client)
    )
    transaction_id = str(transaction.transaction_id)
    transaction.sign(operator_key)
    receipt = transaction.execute(client)
    transaction_status = _response_code_name(receipt.status)
    if transaction_status != "SUCCESS":
        raise RuntimeError(
            "Revenue distribution contract transaction failed: "
            f"{transaction_status} (transaction ID: {transaction_id})"
        )

    return {
        "transaction_id": transaction_id,
        "status": transaction_status,
    }