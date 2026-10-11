import unittest
from unittest.mock import MagicMock, Mock

from fastapi import HTTPException

from app.routes.user import get_user


class UserRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cursor = Mock()
        cursor_context = MagicMock()
        cursor_context.__enter__.return_value = self.cursor
        self.connection = Mock()
        self.connection.cursor.return_value = cursor_context

    def test_get_user_returns_user_balances_and_owned_projects(self) -> None:
        user = {
            "id": 1,
            "hedera_id": "0.0.123",
            "did": None,
            "legal_name": "Example User",
            "email": "example@example.com",
            "phone": None,
            "balance": 1000,
            "created_at": None,
        }
        token_balance = {
            "id": 4,
            "token_id": 7,
            "amount": 30,
            "hedera_token_id": "0.0.456",
            "token_name": "Solar",
            "token_symbol": "SOL",
            "project_id": 9,
            "project_name": "Solar Project",
        }
        project = {
            "id": 9,
            "owner_id": 1,
            "name": "Solar Project",
            "description": None,
            "target_amount": 10000,
            "status": "funding",
            "token_id": 7,
            "hedera_token_id": "0.0.456",
            "token_name": "Solar",
            "token_symbol": "SOL",
            "total_supply": 30,
            "commitment_file_id": "0.0.789",
            "commitment_transaction_id": "0.0.456@1.2",
        }
        self.cursor.fetchone.return_value = user
        self.cursor.fetchall.side_effect = [[token_balance], [project]]

        result = get_user(1, self.connection)

        self.assertEqual(result["id"], 1)
        self.assertEqual(result["token_balances"], [token_balance])
        self.assertEqual(result["projects"], [project])
        self.assertEqual(self.cursor.execute.call_count, 3)

    def test_get_user_raises_404_if_user_does_not_exist(self) -> None:
        self.cursor.fetchone.return_value = None

        with self.assertRaises(HTTPException) as raised:
            get_user(404, self.connection)

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(self.cursor.execute.call_count, 1)


if __name__ == "__main__":
    unittest.main()
