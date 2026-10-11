import unittest
from pathlib import Path
from typing import Any

from deploy_net import validate_compiled_contract, validate_contract_source


CONTRACT_SOURCE = (
    Path(__file__).resolve().parents[1] / "contracts" / "RevenueDistribution.sol"
)


class DeployContractValidationTests(unittest.TestCase):
    def test_project_contract_source_passes_source_validation(self) -> None:
        validate_contract_source(CONTRACT_SOURCE.read_text(encoding="utf-8"))

    def test_unrelated_contract_source_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "RevenueDistribution contract"):
            validate_contract_source("contract OtherContract {}")

    def test_expected_compiled_contract_interface_is_accepted(self) -> None:
        abi: list[dict[str, Any]] = [
            {
                "type": "function",
                "name": "recordDistribution",
                "stateMutability": "nonpayable",
                "inputs": [
                    {"type": "string"},
                    {"type": "address[]"},
                    {"type": "uint256[]"},
                    {"type": "uint256"},
                ],
            },
            {"type": "event", "name": "RevenueDistributed"},
            {"type": "event", "name": "RecipientPayout"},
        ]

        validate_compiled_contract(abi, "60006000")

    def test_wrong_compiled_function_signature_is_rejected(self) -> None:
        abi: list[dict[str, Any]] = [
            {
                "type": "function",
                "name": "recordDistribution",
                "stateMutability": "nonpayable",
                "inputs": [{"type": "uint256"}],
            },
            {"type": "event", "name": "RevenueDistributed"},
            {"type": "event", "name": "RecipientPayout"},
        ]

        with self.assertRaisesRegex(ValueError, "does not match"):
            validate_compiled_contract(abi, "60006000")


if __name__ == "__main__":
    unittest.main()
