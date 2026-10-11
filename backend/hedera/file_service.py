"""Create public, immutable Hedera File Service project commitments."""

import json
from datetime import datetime, timezone
from typing import Any

from hiero_sdk_python import FileCreateTransaction
from hiero_sdk_python.hapi.services.response_code_pb2 import ResponseCodeEnum

from hedera.client import get_client, operator_key

MAX_COMMITMENT_BYTES = 4_096


def build_simulated_project_commitment(
    *,
    project_id: int,
    owner_user_id: int,
    owner_hedera_id: str,
    project_name: str,
    project_description: str | None,
    funding_target: int,
    token_name: str,
    token_symbol: str,
    hedera_token_id: str,
) -> bytes:
    """Build public MVP terms, explicitly labeling the acknowledgement and equipment as simulated."""
    record: dict[str, Any] = {
        "record_type": "EnerX simulated solar project owner commitment",
        "schema_version": 1,
        "is_simulated": True,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "project": {
            "id": project_id,
            "name": project_name,
            "description": project_description,
            "funding_target": funding_target,
        },
        "owner": {
            "user_id": owner_user_id,
            "hedera_account_id": owner_hedera_id,
            "acknowledgement_type": "simulated project-launch acknowledgement",
        },
        "token": {
            "name": token_name,
            "symbol": token_symbol,
            "hedera_token_id": hedera_token_id,
            "total_supply": 100,
        },
        "simulated_solar_equipment": {
            "panel_model": "SIMULATED 550 W monocrystalline PV panel",
            "quantity": 12,
            "rated_capacity_kw": 6.6,
            "supplier": "SIMULATED supplier; no real vendor confirmed",
            "installation_site": "Not provided; simulated project data",
            "procurement_status": "SIMULATED; not purchased, delivered, or installed",
        },
        "owner_commitment": (
            "For this hackathon MVP demonstration, the owner identified by owner.user_id "
            "acknowledges the intention to use project funds raised for the solar-panel "
            "equipment and installation described in simulated_solar_equipment and to "
            "follow the project data recorded here."
        ),
        "disclaimer": (
            "This public record contains simulated demonstration data only. It is not "
            "evidence of a real purchase, supplier confirmation, installation, or "
            "independent verification. The API records a simulated acknowledgement; "
            "the owner does not cryptographically sign this HFS file."
        ),
    }
    contents = json.dumps(
        record,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(contents) > MAX_COMMITMENT_BYTES:
        raise ValueError(
            f"Project commitment is {len(contents)} bytes; maximum is "
            f"{MAX_COMMITMENT_BYTES} bytes"
        )
    return contents


def _require_success(status: int | None, transaction_id: str) -> None:
    if status is None:
        raise RuntimeError(
            f"Hedera File Service receipt for {transaction_id} did not include a status"
        )
    status_name = ResponseCodeEnum.Name(status)
    if status_name != "SUCCESS":
        raise RuntimeError(
            f"Hedera File Service transaction {transaction_id} failed: {status_name}"
        )


def create_project_commitment(
    *,
    project_id: int,
    owner_user_id: int,
    owner_hedera_id: str,
    project_name: str,
    project_description: str | None,
    funding_target: int,
    token_name: str,
    token_symbol: str,
    hedera_token_id: str,
) -> dict[str, str]:
    """Create a one-transaction HFS file with no file keys, making it immutable."""
    contents = build_simulated_project_commitment(
        project_id=project_id,
        owner_user_id=owner_user_id,
        owner_hedera_id=owner_hedera_id,
        project_name=project_name,
        project_description=project_description,
        funding_target=funding_target,
        token_name=token_name,
        token_symbol=token_symbol,
        hedera_token_id=hedera_token_id,
    )
    client = get_client()
    create_transaction = (
        FileCreateTransaction()
        .set_contents(contents)
        .set_file_memo(f"EnerX simulated project commitment {project_id}")
        .freeze_with(client)
    )
    create_transaction_id = str(create_transaction.transaction_id)
    create_transaction.sign(operator_key)
    receipt = create_transaction.execute(client)
    _require_success(receipt.status, create_transaction_id)

    file_id = receipt.file_id
    if file_id is None:
        raise RuntimeError(
            "Hedera File Service did not return a file ID "
            f"(transaction ID: {create_transaction_id})"
        )

    return {
        "file_id": str(file_id),
        "transaction_id": create_transaction_id,
    }