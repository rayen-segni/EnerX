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
   - The owner commits to an on-chain legal agreement recorded on **Hedera File Service (HFS)**.
   - The project's fractional shares are minted on **Hedera Token Service (HTS)**.

2. **Simulated Authentication & Portal Users**:
   - For hackathon demonstration reliability, real wallet popups / QR extensions are avoided.
   - Simulated Portal users are defined in [`data/hedera_portal_users.json`](data/hedera_portal_users.json).
   - Each portal user has an associated `hedera_account_id` and verified status.

3. **Primary Investment**:
   - Investors purchase available campaign tokens using simulated virtual balance (`/balance`).
   - Tokens transfer from treasury to investor on **Hedera HTS**.
   - Investment increases the project's collected funding.

4. **Secondary Marketplace**:
   - Token holders can sell tokens to other users.
   - Virtual USD transfers directly: **Buyer → Seller** (does *not* increase project funding).
   - Tokens transfer on **Hedera HTS**: **Seller → Buyer**.

5. **Solar Production & Smart Contract Revenue Distribution**:
   - Historical production (kWh) and tariff rates generate simulated solar revenue.
   - Revenue distribution is executed by calculating current dynamic token ownership (100% total).
   - Distribution is submitted to the **`RevenueDistribution.sol`** Smart Contract on **Hedera Smart Contract Service (HSCS)**.
   - All results and receipts are archived in PostgreSQL.

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
│   │       ├── production.py       # /projects/{id}/production
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

Verify migration status:

```bash
alembic current
```

### 5. Start the FastAPI Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or using `fastapi dev`:

```bash
fastapi dev app/main.py
```

### 6. Interactive API Documentation

Once the server is running, open your browser:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **API Root**: [http://localhost:8000/](http://localhost:8000/)

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
| **DID** (Identity) | `app/hedera/did_service.py` | Verifies user credentials before creating projects, investing, or trading. |
| **Simulated Portal** | `app/hedera/wallet_service.py` | Deterministic user account & Hedera Account ID lookup for hackathon demo. |
