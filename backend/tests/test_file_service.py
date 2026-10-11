import json
import unittest
from unittest.mock import Mock, patch

from hedera.file_service import (
    MAX_COMMITMENT_BYTES,
    build_simulated_project_commitment,
    create_project_commitment,
)


def build_commitment(description: str | None = None) -> bytes:
    return build_simulated_project_commitment(
        project_id=12,
        owner_user_id=1,
        owner_hedera_id="0.0.123",
        project_name="Demo Solar",
        project_description=description,
        funding_target=10_000,
        token_name="Demo Solar Share",
        token_symbol="DSS",
        hedera_token_id="0.0.456",
    )


class ProjectCommitmentTests(unittest.TestCase):
    def test_commitment_marks_all_solar_data_and_acknowledgement_simulated(self) -> None:
        commitment = json.loads(build_commitment().decode("utf-8"))

        self.assertTrue(commitment["is_simulated"])
        self.assertEqual(commitment["project"]["id"], 12)
        self.assertEqual(commitment["owner"]["user_id"], 1)
        self.assertEqual(commitment["token"]["hedera_token_id"], "0.0.456")
        self.assertEqual(commitment["simulated_solar_equipment"]["quantity"], 12)
        self.assertIn("SIMULATED", commitment["simulated_solar_equipment"]["procurement_status"])
        self.assertIn("does not cryptographically sign", commitment["disclaimer"])

    def test_rejects_commitment_above_maximum_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "maximum is"):
            build_commitment("description " * 2_000)

    @patch("hedera.file_service.FileCreateTransaction")
    @patch("hedera.file_service.get_client")
    def test_creates_complete_file_in_one_immutable_transaction(
        self,
        mock_get_client,
        mock_create_transaction,
    ) -> None:
        file_id = Mock()
        file_id.__str__ = Mock(return_value="0.0.900")

        create_tx = Mock()
        create_tx.set_contents.return_value = create_tx
        create_tx.set_file_memo.return_value = create_tx
        create_tx.freeze_with.return_value = create_tx
        create_tx.transaction_id = "0.0.1@1.1"
        create_tx.execute.return_value = Mock(status=22, file_id=file_id)
        mock_create_transaction.return_value = create_tx

        result = create_project_commitment(
            project_id=12,
            owner_user_id=1,
            owner_hedera_id="0.0.123",
            project_name="Demo Solar",
            project_description="Solar panels " * 100,
            funding_target=10_000,
            token_name="Demo Solar Share",
            token_symbol="DSS",
            hedera_token_id="0.0.456",
        )

        self.assertEqual(result, {"file_id": "0.0.900", "transaction_id": "0.0.1@1.1"})
        mock_get_client.assert_called_once()
        create_tx.set_contents.assert_called_once()
        self.assertLessEqual(
            len(create_tx.set_contents.call_args.args[0]),
            MAX_COMMITMENT_BYTES,
        )
        create_tx.set_keys.assert_not_called()


if __name__ == "__main__":
    unittest.main()
