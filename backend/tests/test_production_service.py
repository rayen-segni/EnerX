import unittest

from app.services.production_service import TokenHolder, allocate_revenue


class RevenueAllocationTests(unittest.TestCase):
    def test_allocates_revenue_by_token_ownership(self) -> None:
        holders = [
            TokenHolder(1, 1, "0.0.1", 20),
            TokenHolder(2, 2, "0.0.2", 80),
        ]

        allocations = allocate_revenue(holders, 10_000)

        self.assertEqual(
            {item.user_id: item.amount_minor for item in allocations},
            {1: 2_000, 2: 8_000},
        )

    def test_distributes_residual_cents_and_preserves_total(self) -> None:
        holders = [
            TokenHolder(1, 1, "0.0.1", 33),
            TokenHolder(2, 2, "0.0.2", 67),
        ]

        allocations = allocate_revenue(holders, 10_001)

        self.assertEqual(
            {item.user_id: item.amount_minor for item in allocations},
            {1: 3_300, 2: 6_701},
        )
        self.assertEqual(sum(item.amount_minor for item in allocations), 10_001)

    def test_residual_cent_tie_break_is_deterministic(self) -> None:
        holders = [
            TokenHolder(2, 2, "0.0.2", 50),
            TokenHolder(1, 1, "0.0.1", 50),
        ]

        allocations = allocate_revenue(holders, 1)

        self.assertEqual(
            [(item.hedera_id, item.amount_minor) for item in allocations],
            [("0.0.1", 1), ("0.0.2", 0)],
        )

    def test_rejects_holdings_that_do_not_cover_the_full_supply(self) -> None:
        holders = [TokenHolder(1, 1, "0.0.1", 99)]

        with self.assertRaisesRegex(ValueError, "exactly 100"):
            allocate_revenue(holders, 100)


if __name__ == "__main__":
    unittest.main()
