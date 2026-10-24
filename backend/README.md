# EnerX Backend

**EnerX** is a solar project crowdfunding and secondary marketplace platform built for the **Hedera** ecosystem.

This repository contains the **modular monolith FastAPI backend** designed for the hackathon MVP.

---

## ☀️ Project Business Model & Rules

1. **Solar Project Creation**:
   - An owner creates a solar project.
   - Each project has **100 tokens = 100% ownership** (indivisible shares, 0 decimals).
   - The owner automatically receives **30 tokens = 30% ownership**.
   - The remaining **70 tokens** are available for investor funding.
   - Project creation writes a public, immutable **Hedera File Service (HFS)** commitment file. For this hackathon MVP, its solar equipment information and owner acknowledgement are explicitly simulated and are not independently verified or signed by the owner's private key.
   - The project's fractional shares are minted on **Hedera Token Service (HTS)**.

2. **Simulated Authentication & Portal Users**:
   - For hackathon demonstration reliability, real wallet popups / QR extensions are avoided.
   - Simulated Portal users are defined in [`data/hedera_portal_users.json`](data/hedera_portal_users.json).
   - Each portal user has an associated `hedera_account_id` and verified status.
   - `POST /auth/did` accepts `user_id`, `legal_name`, `email`, and `hedera_id`, creates a DID operation on HCS, and stores the DID in that user's `users.did` field. The identity values must match the database user. This mock flow uses a request-body `user_id`; it is not a substitute for production authentication.
   - DIDs created by this endpoint are controlled by the configured backend Ed25519 operator key. The DID document is public on HCS; legal name and email are not published.

3. **Primary Investment**:
   - Investors purchase available campaign tokens using simulated virtual balance (`/balance`).
   - Tokens transfer from treasury to investor on **Hedera HTS**.
   - Investment increases the project's collected funding.

4. **Secondary Marketplace**:
   - Token holders can sell tokens to other users.
   - Virtual USD transfers directly: **Buyer → Seller** (does *not* increase project funding).
   - Tokens transfer on **Hedera HTS**: **Seller → Buyer**.

5. **Solar Production & Smart Contract Revenue Distribution**:
   - `POST /prod` records the project's production (kWh) and revenue.
   - The backend snapshots live `token_balances`; distribution requires all 100 project tokens to be held by users.
   - The revenue allocation is submitted to **`RevenueDistribution.sol`** on **Hedera Smart Contract Service (HSCS)** before user balances and distribution rows are updated.
   - Payouts use two decimal places. Any residual cents are assigned by largest fractional remainder so the allocations sum to the full revenue.
   - Production, payout records, and user balance changes are stored in PostgreSQL after the contract transaction succeeds.

---

## 🛠️ Technology Stack

- **Python 3.12+**
- **FastAPI**: Modern, fast web framework with interactive OpenAPI documentation.
- **PostgreSQL**: Application database for fast queries, history, balances, and Hedera IDs.
- **psycopg3**: **Synchronous** PostgreSQL driver using `psycopg.connect` and `dict_row`.
- **Alembic**: Database schema migrations framework (configured to read from `.env`).
- **Hiero SDK Python (`hiero-sdk-python`)**: Official Python SDK for Hedera Hashgraph (HTS, HFS, HSCS).

---

## 📁 Project Structure

```text
backend/
├── app/
│   ├── main.py                     # FastAPI application setup, middleware, and health endpoints
│   ├── config.py                   # Pydantic Settings configuration from .env
│   │
│   ├── db/
│   │   ├── database.py             # Synchronous psycopg3 connection & FastAPI dependency (get_db)
│   │
│   ├── repositories/               # Synchronous SQL queries via psycopg3
│   │   ├── user_repository.py
│   │   ├── project_repository.py
│   │   ├── token_repository.py
│   │   ├── marketplace_repository.py
│   │   ├── production_repository.py
│   │   └── distribution_repository.py
│   │
│   ├── services/                   # Business orchestration (Repo + Hedera)
│   │   ├── auth_service.py
│   │   ├── project_service.py
│   │   ├── investment_service.py
│   │   ├── marketplace_service.py
│   │   ├── production_service.py
│   │   └── distribution_service.py
│   │
│   ├── hedera/                     # Hedera Hashgraph integration services
│   │   ├── client.py               # Hiero SDK client configured from environment
│   │   ├── wallet_service.py       # Simulated Portal user account lookup
│   │   ├── token_service.py        # Hedera Token Service (HTS) (100 total, 30 owner, 70 investor)
│   │   ├── did_service.py          # Decentralized Identity (DID) verification check
│   │   ├── contract_service.py     # HSCS Revenue distribution contract caller
│   │   └── file_service.py         # HFS Owner commitment agreement storage
│   │
│   ├── api/
│   │   └── routes/                 # FastAPI HTTP endpoints
│   │       ├── auth.py             # /auth/login, /auth/me, /balance, /balance/top-up
│   │       ├── projects.py         # /projects (GET, POST, GET {id})
│   │       ├── investments.py      # /projects/{id}/invest, /investments/me
│   │       ├── marketplace.py      # /marketplace/listings (GET, POST, BUY, DELETE)
│       │       ├── production.py       # POST /prod
│   │       └── distributions.py    # /projects/{id}/distribute, /projects/{id}/distributions
│   │
│   └── schemas/                    # Pydantic request/response validation schemas
│       ├── auth.py
│       ├── project.py
│       ├── investment.py
│       ├── marketplace.py
│       ├── production.py
│       └── distribution.py
│
├── alembic/                        # Database migration scripts
│   ├── env.py                      # Configured to use app.config.settings
│   └── versions/
├── alembic.ini
│
├── contracts/
│   └── RevenueDistribution.sol     # Hedera HSCS Smart Contract for revenue distribution
├── deploy_net.py                   # Validates, compiles, and deploys the HSCS contract
│
├── data/
│   ├── hedera_portal_users.json    # Simulated Hedera Portal directory
│   └── simulated_production.json   # Simulated solar kWh output data
│
├── tests/
│   ├── test_foundation.py          # Foundation unit and integration tests
│   └── test_db_direct.py           # Standalone PostgreSQL connectivity test
│
├── .env.example                    # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites

- Python 3.12+
- PostgreSQL 14+ running locally or remotely
- `uv` (recommended) or standard `pip`

### 2. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Ensure your PostgreSQL credentials in `.env` match your local setup:

```ini
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=enerx
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
```

After deploying `contracts/RevenueDistribution.sol` to the same Hedera network as `HEDERA_NETWORK`, set `HEDERA_REVENUE_CONTRACT_ID` in `.env` to its `0.0.x` contract ID. The contract must have been deployed by the configured `OPERATOR_KEY`, since it authorizes that deployer as its operator. Until this setting is present, `POST /prod` returns HTTP 503.

Install the Solidity compiler (`solc` 0.8.20 or newer) and deploy from the backend directory using the same `.env` operator account the API uses:

```bash
python deploy_net.py --check-only
python deploy_net.py
```

The check-only command validates the source contract name, operator restrictions, distribution function and payout events, then compiles it and checks the compiled ABI before any Hedera connection is attempted. Deployment displays the selected network and operator and requires typing `deploy`; after confirmation, it prints the new contract ID and the `.env` setting to copy. Use `--source PATH` to validate a different source file, `--solc PATH` to select the compiler executable, or `--yes` only when running in a trusted non-interactive environment.

`POST /prod` accepts `project_id`, `energy_kwh`, and `revenue`, for example:

```json
{
  "project_id": 1,
  "energy_kwh": "500.00",
  "revenue": "100.00"
}
```

### 3. Verify PostgreSQL Connection

Run the direct database connectivity test:

```bash
python tests/test_db_direct.py
```

Expected output:
```text
============================================================
Testing EnerX PostgreSQL Connection (psycopg3 synchronous)
============================================================
Target Database Host: localhost
Target Database Port: 5433
Target Database Name: enerx
Target Database User: rayen
Connection URL:       postgresql://rayen:postgres@localhost:5433/enerx
------------------------------------------------------------
✅ SUCCESS: Successfully connected to PostgreSQL!
Database:   enerx
User:       rayen
Latency:    15.2 ms
```

### 4. Database Migrations (Alembic)

**Use a development or test database.** The migration chain includes demo records for the API endpoints. The endpoint-test migration inserts projects and token metadata with `TEST_ONLY_NOT_ON_HEDERA_*` token IDs; these are database fixtures, not real HTS tokens. It does not alter user balances or submit Hedera transactions.

Verify migration status:

```bash
alembic upgrade head
alembic current
```

After migration, call `GET /project/` and use the returned `id` for the project named `TEST FIXTURE - Revenue Distribution` when testing `POST /prod`. The separate `TEST FIXTURE - Funding` project is for endpoints that need a project in `funding` status. The migration seeds matching token balances, investment history, token transaction history, and a marketplace listing.

The migration does not make Hedera-backed token transfers succeed: `POST /investment/`, project creation, and marketplace purchases need a real, live HTS token and valid operator/user account setup. In particular, do not replace a real project token ID with a `TEST_ONLY_NOT_ON_HEDERA_*` value. `POST /prod` also requires the deployed `HEDERA_REVENUE_CONTRACT_ID` and access to the configured Hedera network; its production and distribution rows are created by the endpoint itself.

To populate a separate local demo project through the API using live Hedera transactions, start the backend and run:

```bash
python seed_local_data.py
```

The script defaults to `http://localhost:8000` and is restricted to loopback URLs unless `--allow-remote` is explicitly supplied. It checks the API and simulated portal accounts, and refuses to reuse its project name. After confirmation, it sets the virtual balances of users 2 and 3 to 10,000, creates a project owned by user 1, has users 2 and 3 each invest in 35 tokens, then lists and sells 5 of the owner's tokens to user 3. These operations create real HTS transactions; the balances are only demo virtual currency. It does not call `/prod`; afterward, the new project has 100 owned tokens and can be used to test that route. Database rows for users 1-3 must already exist (run the migrations). An interrupted run may leave changed virtual balances, a partial project, or an on-chain transaction; inspect the API and HashScan before retrying, and choose a different `--project-name` if the previous project was created.

### 5. Start the FastAPI Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or using `fastapi dev`:

```bash
fastapi dev app/main.py
```

## 🌐 API Reference for Front-End Developers

The examples below use `https://enerxv.fastapicloud.dev` as the base URL. The API currently has no bearer-token authentication; `/auth/{user_id}` is a simulated portal-user lookup, not an authorization mechanism. Send and receive JSON with `Content-Type: application/json` for requests with a body. IDs and token counts are integers; monetary amounts and energy measurements support decimal values.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | API status and documentation URL |
| `GET` | `/auth/{user_id}` | Find a simulated portal user |
| `POST` | `/auth/did` | Create a DID (currently not implemented; see limitations below) |
| `POST` | `/project/` | Create a project and its token |
| `GET` | `/project/` | List all projects |
| `GET` | `/project/{owner_id}` | List projects owned by a user |
| `POST` | `/investment/` | Buy project tokens with virtual balance |
| `GET` | `/investment/{investor_id}` | List an investor's investments |
| `PATCH` | `/user` | Update user fields |
| `POST` | `/marketplace/list` | Offer tokens for secondary-market sale |
| `POST` | `/marketplace/list/buy` | Buy tokens from a listing |
| `POST` | `/prod` | Record production and distribute revenue |

### System and simulated sign-in

`GET /` returns `{"app":"EnerX Backend","status":"online","docs":"/docs"}`. There is no `/health` endpoint.

`GET /auth/{user_id}` returns the matching simulated portal user:

```json
{
  "user_id": 1,
  "account_type": "ECDSA",
  "hedera_account_id": "0.0.123456",
  "name": "Example User",
  "email": "user@example.com"
}
```

Unknown IDs return `404`. The returned `user_id` is the app's simulated identity; the portal record is not proof that the caller is that user.

`POST /auth/did` accepts `user_id`, `legal_name`, `email`, and `hedera_id` (a Hedera account ID such as `0.0.123456`). For the hackathon MVP, matching these values creates or reuses the DID and marks the User identity as verified. The same single verification enables both investing and project-owner actions; separate investor/owner credentials are not required in this MVP.

### Projects and investments

`POST /project/` creates a project. `target_amount` is the funding target in the app's monetary unit; the owner receives the initial 30 tokens.

```json
{
  "user_id": 1,
  "name": "Community Solar",
  "description": "A local rooftop solar project",
  "target_amount": 10000,
  "token_name": "Community Solar Share",
  "token_symbol": "CSS"
}
```

Returns `201` with `id`, `owner_id`, `name`, `description`, `target_amount`, `status`, `token_id`, `hedera_token_id`, `token_name`, `token_symbol`, `total_supply`, `commitment_file_id`, and `commitment_transaction_id`. A missing user returns `404`; Hedera token/HFS failures return `502`.

Project creation also creates a public, immutable Hedera File Service record containing the project/token data, a simulated 12-panel solar installation proposal, and simulated owner commitment terms. The file clearly says no supplier or site is confirmed and the panels are not proven purchased or installed. The response includes `commitment_file_id` and `commitment_transaction_id`; project GET responses include those values as well. Project descriptions are limited to 512 characters to keep the complete immutable record within one HFS create transaction. Apply migrations with `alembic upgrade head` before using the updated route. This API uses the configured operator to create the file; it does not collect or verify a cryptographic signature from the owner.

`GET /project/` returns an array of projects. `GET /project/{owner_id}` returns the same project shape filtered by owner; it returns `404` if that owner has no projects. Each item contains `id`, `owner_id`, `name`, `description`, `token_name`, `token_symbol`, `token_id`, `token_supply`, `target_amount`, and `status`.

`POST /investment/` purchases a positive integer number of tokens:

```json
{"user_id": 2, "project_id": 1, "token_amount": 5}
```

On success, returns `201` with `investment_id`, `project_id`, `user_id`, `token_amount`, `amount_paid`, `transaction_id`, `total_supply`, and `project_status`. The project must still be accepting funding, the user must have enough virtual balance, and total supply cannot exceed 100. A missing project or user returns `404`; an inactive project, insufficient balance, or excess supply returns `400`; Hedera transfer failures return `502`.

`GET /investment/{investor_id}` returns an array of investment records with `id`, `project_id`, `investor_id`, `token_amount`, `amount_paid`, `transaction_id`, and `created_at`. An investor with no investments receives an empty array.

### User profile

`PATCH /user` requires the user `id` and at least one field to update. Omitted fields are unchanged; fields that accept `null` can be explicitly cleared.

```json
{
  "id": 2,
  "phone": "+1-555-0100",
  "did": "did:hedera:example"
}
```

Updatable fields are `hedera_id`, `did`, `legal_name`, `email`, `phone`, and `balance`. The response contains `id`, `hedera_id`, `did`, `legal_name`, `email`, `phone`, `balance`, and `created_at`. No fields to update returns `400`, an unknown user returns `404`, and a database constraint conflict returns `409`.

### Secondary marketplace

`POST /marketplace/list` creates a listing using the seller's `user_id`, `token_id`, unit price `u_price`, and positive token `amount`:

```json
{"user_id": 1, "token_id": 1, "u_price": 12.50, "amount": 3}
```

Returns `201` with the new listing's `id`, `user_id`, `token_id`, `u_price`, and `amount`. Insufficient token balance returns `400`. There is currently no endpoint to retrieve or cancel listings.

`POST /marketplace/list/buy` buys some or all of a listing:

```json
{"user_id": 2, "listing_id": 1, "amount": 2}
```

The `201` response contains `investment_id`, `listing_id`, `buyer_id`, `seller_id`, `token_id`, `amount`, `amount_paid`, `transaction_id`, and `remaining_offered_tokens`. Buyers cannot purchase their own listing; requested quantity must not exceed the listed or remaining seller balance, and the buyer must have enough virtual balance. Validation errors return `422`; business-rule errors include `400`/`409`; Hedera transfer failures return `502`.

### Production and revenue distributions

`POST /prod` records a positive energy output and revenue for a project:

```json
{
  "project_id": 1,
  "energy_kwh": "500.00",
  "revenue": "100.00"
}
```

The project must have exactly 100 tokens held in user balances. On success, returns `201` with `production_id`, `project_id`, `production_date`, `energy_kwh`, `revenue`, `contract_transaction_id`, `contract_status`, and `distributions`. Each distribution contains `distribution_id`, `token_balance_id`, `user_id`, `token_amount`, and `amount`. The contract must be configured (`503` otherwise); a missing project/token returns `404`, an ownership total other than 100 returns `409`, and a Hedera contract failure returns `502`.

### Errors and integration notes

FastAPI validation errors use status `422`; application errors generally return a JSON body shaped like `{"detail":"..."}`. Handle non-2xx responses and display or log the `detail` rather than assuming every request succeeds. CORS is currently enabled for all origins. There is no pagination, filtering, or dedicated endpoint for reading a user's balance; the balance is included in the response from `PATCH /user`.

### 6. Interactive API Documentation

Once the server is running, open your browser:

- **Swagger UI**: [https://enerxv.fastapicloud.dev/docs](https://enerxv.fastapicloud.dev/docs)
- **ReDoc**: [https://enerxv.fastapicloud.dev/redoc](https://enerxv.fastapicloud.dev/redoc)
- **API Status**: [https://enerxv.fastapicloud.dev/](https://enerxv.fastapicloud.dev/)
- **API Root**: [https://enerxv.fastapicloud.dev/](https://enerxv.fastapicloud.dev/)

---

## 🧪 Testing

Run the test suite:

```bash
pytest tests/
```

---

## 🔗 Hedera Integration Overview

| Hedera Service | File | Purpose in EnerX |
| :--- | :--- | :--- |
| **HTS** (Token Service) | `app/hedera/token_service.py` | Fractional project tokens (100 total: 30 owner, 70 investors). |
| **HFS** (File Service) | `app/hedera/file_service.py` | Immutable owner-project commitment agreement. |
| **HSCS** (Smart Contracts) | `app/hedera/contract_service.py` | Executes revenue distribution according to current token holdings. |
| **DID** (Identity) | `app/hedera/did_service.py` | One MVP User verification enables creating projects, investing, and trading. |
| **Simulated Portal** | `app/hedera/wallet_service.py` | Deterministic user account & Hedera Account ID lookup for hackathon demo. |
