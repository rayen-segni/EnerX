from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class TokenHolder:
    token_balance_id: int
    user_id: int
    hedera_id: str
    token_amount: int


@dataclass(frozen=True)
class DistributionAllocation:
    token_balance_id: int
    user_id: int
    hedera_id: str
    token_amount: int
    amount_minor: int


@dataclass
class _PendingAllocation:
    holder: TokenHolder
    amount_minor: int
    remainder: int


def allocate_revenue(
    holders: Sequence[TokenHolder],
    total_amount_minor: int,
) -> list[DistributionAllocation]:
    """Allocate minor currency units proportionally, assigning residual cents by largest remainder."""
    if total_amount_minor <= 0:
        raise ValueError("The total amount must be positive")
    if (
        not holders
        or any(holder.token_amount <= 0 for holder in holders)
        or sum(holder.token_amount for holder in holders) != 100
    ):
        raise ValueError("Positive token holdings must sum to exactly 100")

    pending = [
        _PendingAllocation(
            holder=holder,
            amount_minor=total_amount_minor * holder.token_amount // 100,
            remainder=total_amount_minor * holder.token_amount % 100,
        )
        for holder in holders
    ]
    pending.sort(key=lambda item: (-item.remainder, item.holder.hedera_id))

    residual_cents = total_amount_minor - sum(
        item.amount_minor for item in pending
    )
    for item in pending[:residual_cents]:
        item.amount_minor += 1

    return [
        DistributionAllocation(
            token_balance_id=item.holder.token_balance_id,
            user_id=item.holder.user_id,
            hedera_id=item.holder.hedera_id,
            token_amount=item.holder.token_amount,
            amount_minor=item.amount_minor,
        )
        for item in pending
    ]