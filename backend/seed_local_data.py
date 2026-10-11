"""Populate a local EnerX database through the HTTP API and Hedera testnet."""

import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from typing import Any


OWNER_ID = 1
INVESTOR_IDS = (2, 3)
MARKETPLACE_SELLER_ID = OWNER_ID
MARKETPLACE_BUYER_ID = INVESTOR_IDS[1]
OPENING_BALANCE = "10000.00"
PROJECT_TARGET = 10_000
TOKENS_PER_INVESTOR = 35
MARKETPLACE_TOKENS = 5
MARKETPLACE_UNIT_PRICE = "100.00"
REQUEST_TIMEOUT_SECONDS = 120
API_HOST = "http://localhost:8000"


class SeedError(RuntimeError):
    """An API call or seed precondition failed."""


def request_api(
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            response_body = response.read()
    except HTTPError as exc:
        response_body = exc.read()
        try:
            detail = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            detail = response_body.decode("utf-8", errors="replace")
        raise SeedError(f"{method} {path} returned HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError) as exc:
        raise SeedError(f"Could not reach {base_url}: {exc}") from exc

    if not response_body:
        return None
    try:
        return json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SeedError(f"{method} {path} returned a non-JSON response") from exc


def require_loopback_url(base_url: str, allow_remote: bool) -> None:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SeedError("Base URL must be an absolute http:// or https:// URL")
    if not allow_remote and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise SeedError(
            "This seed script creates Hedera transactions and changes user balances. "
            "By default it only targets localhost; pass --allow-remote to override."
        )


def run_seed(
    base_url: str,
    project_name: str,
    opening_balance: str,
    confirmed: bool,
) -> dict[str, Any]:
    health = request_api(base_url, "GET", "/")
    if not isinstance(health, dict) or health.get("status") != "online":
        raise SeedError("The API root did not report status=online")
    print(f"API online: {base_url}")

    portal_users = {}
    for user_id in (OWNER_ID, *INVESTOR_IDS):
        portal_user = request_api(base_url, "GET", f"/auth/{user_id}")
        if not isinstance(portal_user, dict) or portal_user.get("user_id") != user_id:
            raise SeedError(f"Could not validate simulated portal user {user_id}")
        portal_users[user_id] = portal_user
        print(f"Validated simulated portal user {user_id}")

    projects = request_api(base_url, "GET", "/project/")
    if not isinstance(projects, list):
        raise SeedError("GET /project/ did not return a project list")
    if any(project.get("name") == project_name for project in projects):
        raise SeedError(
            f"Project name {project_name!r} already exists. Choose another "
            "--project-name; the script will not duplicate it or repeat HTS transactions."
        )

    print(
        "\nThis seed run will set the virtual balances of users "
        f"{INVESTOR_IDS[0]} and {INVESTOR_IDS[1]} to {opening_balance}, create a new "
        "HTS token and perform two primary token transfers, then sell "
        f"{MARKETPLACE_TOKENS} owner-held tokens to user {MARKETPLACE_BUYER_ID}."
    )
    if not confirmed and input("Type 'seed' to continue: ") != "seed":
        raise SeedError("Seed cancelled.")

    # The demo-user rows must already exist; PATCH fails before any Hedera transaction
    # is requested if the database migrations have not seeded them.
    for user_id in INVESTOR_IDS:
        updated_user = request_api(
            base_url,
            "PATCH",
            "/user",
            {"id": user_id, "balance": opening_balance},
        )
        if not isinstance(updated_user, dict) or updated_user.get("id") != user_id:
            raise SeedError(f"Could not set the virtual balance for user {user_id}")
        print(f"Set virtual balance for user {user_id}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    token_symbol = f"ENX{timestamp[-9:]}"
    project = request_api(
        base_url,
        "POST",
        "/project/",
        {
            "user_id": OWNER_ID,
            "name": project_name,
            "description": "Local API seed project; created with live Hedera testnet transactions.",
            "target_amount": PROJECT_TARGET,
            "token_name": f"EnerX Seed {timestamp}",
            "token_symbol": token_symbol,
        },
    )
    if not isinstance(project, dict) or not project.get("id") or not project.get("token_id"):
        raise SeedError("Project creation returned no project or token ID")
    project_id = int(project["id"])
    token_id = int(project["token_id"])
    hedera_token_id = project.get("hedera_token_id")
    print(
        f"Created project {project_id}; HTS token ID: {hedera_token_id}. "
        "The project-create endpoint creates and transfers tokens on Hedera."
    )

    investments = []
    for user_id in INVESTOR_IDS:
        investment = request_api(
            base_url,
            "POST",
            "/investment/",
            {
                "user_id": user_id,
                "project_id": project_id,
                "token_amount": TOKENS_PER_INVESTOR,
            },
        )
        if not isinstance(investment, dict) or not investment.get("transaction_id"):
            raise SeedError(f"Investment for user {user_id} returned no Hedera transaction")
        investments.append(investment)
        print(
            f"User {user_id} invested {TOKENS_PER_INVESTOR} tokens "
            f"(HTS transaction {investment['transaction_id']})"
        )

    listing = request_api(
        base_url,
        "POST",
        "/marketplace/list",
        {
            "user_id": MARKETPLACE_SELLER_ID,
            "token_id": token_id,
            "u_price": MARKETPLACE_UNIT_PRICE,
            "amount": MARKETPLACE_TOKENS,
        },
    )
    if not isinstance(listing, dict) or not listing.get("id"):
        raise SeedError("Marketplace listing creation returned no listing ID")

    purchase = request_api(
        base_url,
        "POST",
        "/marketplace/list/buy",
        {
            "user_id": MARKETPLACE_BUYER_ID,
            "listing_id": int(listing["id"]),
            "amount": MARKETPLACE_TOKENS,
        },
    )
    if not isinstance(purchase, dict) or not purchase.get("transaction_id"):
        raise SeedError("Marketplace purchase returned no Hedera transaction")
    print(
        f"Completed marketplace purchase (HTS transaction {purchase['transaction_id']})"
    )

    owned_projects = request_api(base_url, "GET", f"/project/{OWNER_ID}")
    if not any(item.get("id") == project_id for item in owned_projects):
        raise SeedError("Created project was not returned by GET /project/{owner_id}")
    investor_history = {
        user_id: request_api(base_url, "GET", f"/investment/{user_id}")
        for user_id in INVESTOR_IDS
    }

    return {
        "project_id": project_id,
        "token_id": token_id,
        "hedera_token_id": hedera_token_id,
        "project_status": investments[-1].get("project_status"),
        "token_supply": investments[-1].get("total_supply"),
        "investments": investments,
        "listing_id": listing["id"],
        "marketplace_purchase": purchase,
        "investor_history_counts": {
            str(user_id): sum(
                1
                for record in records
                if record.get("project_id") == project_id
            )
            for user_id, records in investor_history.items()
        },
        "portal_accounts": {
            str(user_id): portal_users[user_id].get("hedera_account_id")
            for user_id in (OWNER_ID, *INVESTOR_IDS)
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Seed a local EnerX project using the API and live Hedera transactions. "
            "Does not call POST /prod."
        )
    )
    parser.add_argument(
        "--base-url",
        default=API_HOST,
        help="FastAPI base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--project-name",
        default="EnerX Local API Seed Project",
        help="Unique project name; reusing an existing name is refused",
    )
    parser.add_argument(
        "--opening-balance",
        default=OPENING_BALANCE,
        help="Virtual balance to set for both investor accounts (default: 10000.00)",
    )
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow a non-local API URL (not recommended for a seed run)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt before changing balances and sending HTS transactions",
    )
    args = parser.parse_args()

    try:
        require_loopback_url(args.base_url, args.allow_remote)
        opening_balance = Decimal(args.opening_balance)
        balance_exponent = opening_balance.as_tuple().exponent
        if (
            not opening_balance.is_finite()
            or opening_balance <= 0
            or not isinstance(balance_exponent, int)
            or balance_exponent < -2
        ):
            raise SeedError("--opening-balance must be positive with at most two decimals")
        result = run_seed(
            args.base_url.rstrip("/"),
            args.project_name,
            f"{opening_balance:.2f}",
            args.yes,
        )
    except (SeedError, OSError, ValueError, InvalidOperation) as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1

    print("\nSeed completed. No production or revenue-distribution request was made.")
    print(json.dumps(result, indent=2, default=str))
    print(
        "\nThe resulting project's live ownership should total 100 tokens, "
        "so it is eligible for POST /prod."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
