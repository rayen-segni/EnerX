"""Compile and deploy the EnerX revenue distribution contract to Hedera."""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT / "contracts" / "RevenueDistribution.sol"


def validate_contract_source(source: str) -> None:
    """Reject a source file that is not the operator-controlled revenue contract."""
    required_patterns = {
        "RevenueDistribution contract":
            r"\bcontract\s+RevenueDistribution\b",
        "operator authorization modifier":
            r"\bmodifier\s+onlyOperator\s*\(",
        "operator initialized by the deploying account":
            r"\bconstructor\s*\(\s*\)\s*\{\s*operator\s*=\s*msg\.sender\s*;",
        "authorized recordDistribution function":
            r"\bfunction\s+recordDistribution\s*\("
            r"[\s\S]*?\)\s*external\s+onlyOperator\b",
        "100-token ownership check":
            r"\brequire\s*\(\s*totalTokens\s*==\s*100\b",
        "recipient payout event":
            r"\bemit\s+RecipientPayout\s*\(",
        "distribution confirmation event":
            r"\bemit\s+RevenueDistributed\s*\(",
    }
    missing = [
        description
        for description, pattern in required_patterns.items()
        if re.search(pattern, source) is None
    ]
    if missing:
        raise ValueError(
            "The Solidity source is not the expected EnerX contract; missing: "
            + ", ".join(missing)
        )


def validate_compiled_contract(abi: list[dict[str, Any]], bytecode: str) -> None:
    """Ensure the compiler output exposes the expected contract API and has deployable code."""
    if not bytecode or not re.fullmatch(r"(?:[0-9a-fA-F]{2})+", bytecode):
        raise ValueError("The compiled RevenueDistribution bytecode is empty or invalid")

    record_functions = [
        entry
        for entry in abi
        if entry.get("type") == "function"
        and entry.get("name") == "recordDistribution"
    ]
    expected_inputs = [
        ("string", None),
        ("address", "[]"),
        ("uint256", "[]"),
        ("uint256", None),
    ]
    if len(record_functions) != 1:
        raise ValueError("Compiled contract must expose exactly one recordDistribution function")

    function = record_functions[0]
    actual_inputs = [
        (
            argument.get("type", "").removesuffix("[]"),
            "[]" if argument.get("type", "").endswith("[]") else None,
        )
        for argument in function.get("inputs", [])
    ]
    if actual_inputs != expected_inputs or function.get("stateMutability") != "nonpayable":
        raise ValueError(
            "Compiled recordDistribution API does not match "
            "(string, address[], uint256[], uint256)"
        )

    event_names = {
        entry.get("name")
        for entry in abi
        if entry.get("type") == "event"
    }
    if not {"RevenueDistributed", "RecipientPayout"}.issubset(event_names):
        raise ValueError("Compiled contract is missing the expected payout events")


def compile_contract(source_path: Path, compiler: str) -> tuple[list[dict[str, Any]], str]:
    source = source_path.read_text(encoding="utf-8")
    validate_contract_source(source)

    compiler_path = shutil.which(compiler)
    if compiler_path is None:
        raise RuntimeError(
            f"Solidity compiler '{compiler}' was not found. Install solc 0.8.20 or newer."
        )

    input_json = {
        "language": "Solidity",
        "sources": {source_path.name: {"content": source}},
        "settings": {
            "outputSelection": {
                "*": {
                    "RevenueDistribution": ["abi", "evm.bytecode.object"],
                }
            }
        },
    }
    result = subprocess.run(
        [compiler_path, "--standard-json"],
        input=json.dumps(input_json),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Solidity compilation failed:\n{result.stderr.strip() or result.stdout.strip()}"
        )

    output_start = result.stdout.find("{")
    if output_start < 0:
        raise RuntimeError(
            "Solidity compiler returned no JSON output:\n" + result.stderr.strip()
        )
    try:
        output = json.loads(result.stdout[output_start:])
    except json.JSONDecodeError as exc:
        raise RuntimeError("Could not parse Solidity compiler output") from exc

    errors = [
        diagnostic.get("formattedMessage", diagnostic.get("message", "Compiler error"))
        for diagnostic in output.get("errors", [])
        if diagnostic.get("severity") == "error"
    ]
    if errors:
        raise RuntimeError("Solidity compilation failed:\n" + "\n".join(errors))

    compiled = (
        output.get("contracts", {})
        .get(source_path.name, {})
        .get("RevenueDistribution")
    )
    if compiled is None:
        raise RuntimeError("Compiler output did not contain the RevenueDistribution contract")

    abi = compiled.get("abi", [])
    bytecode = compiled.get("evm", {}).get("bytecode", {}).get("object", "")
    validate_compiled_contract(abi, bytecode)
    return abi, bytecode


def deploy_contract(bytecode: str, skip_confirmation: bool) -> int:
    from app.config import settings
    from hedera.client import get_client, operator_id, operator_key
    from hiero_sdk_python import ContractCreateTransaction
    from hiero_sdk_python.transaction.transaction_receipt import TransactionReceipt

    print(f"Network: {settings.HEDERA_NETWORK}")
    print(f"Deploying account: {operator_id}")
    if not skip_confirmation:
        confirmation = input("Type 'deploy' to submit the contract deployment: ")
        if confirmation != "deploy":
            print("Deployment cancelled.")
            return 1

    client = get_client()
    transaction = (
        ContractCreateTransaction()
        .set_bytecode(bytes.fromhex(bytecode))
        .set_gas(2_000_000)
        .freeze_with(client)
    )
    transaction_id = str(transaction.transaction_id)
    transaction.sign(operator_key)
    receipt = transaction.execute(client)
    if not isinstance(receipt, TransactionReceipt):
        raise RuntimeError("Hedera did not return a deployment transaction receipt")

    contract_id = receipt.contract_id
    if contract_id is None:
        raise RuntimeError(
            f"Deployment receipt did not contain a contract ID "
            f"(status: {receipt.status}, transaction: {transaction_id})"
        )

    print(f"Contract ID: {contract_id}")
    print(f"Transaction ID: {transaction_id}")
    print(f"Add this to your backend .env: HEDERA_REVENUE_CONTRACT_ID={contract_id}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate, compile, and deploy RevenueDistribution.sol to Hedera."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Solidity source file (default: contracts/RevenueDistribution.sol)",
    )
    parser.add_argument(
        "--solc",
        default="solc",
        help="Solidity compiler executable (default: solc)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate and compile without connecting to Hedera or deploying",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation before deployment",
    )
    args = parser.parse_args()

    try:
        _, bytecode = compile_contract(args.source, args.solc)
        print(f"Validated and compiled {args.source}")
        if args.check_only:
            print("Contract source and compiled ABI match RevenueDistribution.")
            return 0
        return deploy_contract(bytecode, args.yes)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Deployment failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
