import unittest
from unittest.mock import MagicMock, Mock

from app.routes.marketplace import create_listing
from app.schemas.marketplace import MarketplaceListingCreateRequest


class MarketplaceListingRouteTests(unittest.TestCase):
    def test_create_listing_returns_the_new_listing_id(self) -> None:
        cursor = Mock()
        cursor.fetchone.side_effect = [
            {"id": 10, "amount": 30},
            {"id": 55},
        ]
        cursor_context = MagicMock()
        cursor_context.__enter__.return_value = cursor
        connection = Mock()
        connection.cursor.return_value = cursor_context

        result = create_listing(
            MarketplaceListingCreateRequest(
                user_id=1,
                token_id=7,
                u_price="100.00",
                amount=5,
            ),
            connection,
        )

        self.assertEqual(result["id"], 55)
        self.assertEqual(result["user_id"], 1)
        self.assertEqual(result["token_id"], 7)
        self.assertEqual(result["amount"], 5)
        self.assertIn("RETURNING id", cursor.execute.call_args_list[-1].args[0])


if __name__ == "__main__":
    unittest.main()
