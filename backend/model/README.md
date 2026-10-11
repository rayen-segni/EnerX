# EnerX — AI Agent (solar yield forecasting + auditable reports on Hedera)

EnerX is a decentralized platform that finances residential solar plants in Tunisia through tokenized real-world assets on Hedera. Investors buy EnerTokens (HTS), funds are escrowed in a smart contract (HSCS), owners prove roof ownership with a Hedera DID, and dividends come from the electricity sold to the national utility (STEG).

This repository contains the **AI agent module**: it forecasts the daily production of any solar roof in Tunisia, converts it into an expected dividend per token, adjusts the figure with a news-risk agent, and anchors a hash of every report on **Hedera Consensus Service (HCS)** so that forecasts are immutable and auditable.

> Hackathon: ISGT Campus Edition — Hedera Cross Campus Challenge 2026 (themes: Real-World Assets, DeFi, Digital Identity, AI × Web3 Agents).
> Team: [TODO: team members and roles]

## How it works

```
 roof (lat, lon, kW)
        |
        v
 Open-Meteo forecast --> daily temperature + irradiance
        |
        v
 Neural network (MLP 64-32-1) --> kWh/day  (+ 80 % error range)
        |
        v
 News agent (keywords or Claude LLM) --> coefficient 0.90 - 1.10 + risk level
        |
        v
 Aggregator: kWh x STEG tariff x news coefficient / number of tokens
        |
        v
 JSON report + SHA-256 hash --> anchored on Hedera Consensus Service
        ^
        |
 FastAPI  (/forecast, /news, /health)  <-- called by the dashboard / backend
```

## Results

Trained on 12 Tunisian cities, 2019–2023 (daily data). Split by date: train 2019–2021, dev 2022, test 2023.

| Metric (test year 2023) | Result |
|---|---|
| MAE | 0.65 kWh/day (about 1.4 % of mean production) |
| R² | 0.995 |
| Linear regression baseline | 0.87 kWh/day |
| "Yesterday = today" baseline | 6.99 kWh/day |
| Error range coverage (10th–90th percentile of dev errors) | 80 % of test days |
| **Cities never seen in training** (Tataouine, Kasserine, Bizerte, Tozeur; test year only) | **0.85 kWh/day** (linear regression: 1.11) |

Reproduce the last row with `python test_ville_cachee.py`.

## Limitations (please read)

- **Training data is simulated.** Production values come from the PVGIS photovoltaic simulation (10 kWp system, 14 % losses, optimal angles), not from measured plants. The scores measure agreement with that simulation. The model is meant to be retrained on real STEG meter data.
- **The error range reflects model error when the weather is known.** Weather forecasts beyond 2–3 days are less reliable, so the real uncertainty is larger.
- The tilt/azimuth requested from Open-Meteo are read from the PVGIS responses (`check_pvgis_tilt.py` -> `pvgis_tilts.json`) and interpolated on latitude. [TODO: confirm the file was generated and committed; without it the code falls back to an unverified 30°]
- **End-to-end error.** The 0.65 kWh/day figure uses PVGIS weather as input. With Open-Meteo weather (what the API really uses) the error is measured by `evaluate_chain.py`: [TODO: paste MAE, bias and interval coverage from the script output]. This measures the weather-source mismatch on historical data, not the (larger) error of a multi-day forecast.
- The model was trained on latitudes 32.9–37.3 and longitudes 8.1–10.9. Outside this area (+0.5°) the report carries a warning (or the API refuses with `ENERX_STRICT_RANGE=1`).
- **The news coefficient (max ±10 %) is a design choice, not a calibrated value.** In the default mode the news agent applies keyword rules to fictitious example headlines; the LLM mode is optional. [TODO: update once the LLM mode has been tested with a real API key]
- STEG purchase tariff: 0.217 DT/kWh (excl. tax) for plants under 1 MW, taken from the 2024 JORT decree as reported by the press; to be re-checked against the official text.

## Quick start

Requires Python 3.10+.

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in your values (see below)

# 1. (optional) rebuild the dataset and retrain
python collect_data.py      # downloads PVGIS data -> dataset_solar_global_tunisie.csv
python model.py             # trains the network -> solar_agent.pkl

# 1b. recommended checks (internet needed)
python check_pvgis_tilt.py  # real PVGIS tilt per city -> pvgis_tilts.json
python evaluate_chain.py    # end-to-end error + calibrated interval -> chain_calibration.json
python test_hash.py         # Python and JavaScript hashes must match

# 2. run the API
uvicorn api:app --reload    # docs: http://127.0.0.1:8000/docs

# 3. run the end-to-end demo
python demo.py
```

The trained model `solar_agent.pkl` is included, so steps 1 can be skipped.

### Configuration (`.env`)

| Variable | Used for |
|---|---|
| `OPERATOR_ID`, `OPERATOR_KEY`, `OPERATOR_KEY_TYPE`, `NETWORK` | Hedera testnet account that pays for HCS messages (free account at https://portal.hedera.com) |
| `HCS_TOPIC_ID` | The HCS topic where report hashes are published |
| `GEMINI_API_KEY` | Optional: enables the LLM mode of the news agent (free key from Google AI Studio) |
| `ANTHROPIC_API_KEY` | Optional alternative LLM provider (used only if `GEMINI_API_KEY` is absent) |
| `ENERX_STRICT_RANGE` | Optional: `1` makes the API refuse roofs outside the training area |

Never commit `.env`. Only `.env.example` (placeholders) belongs in the repository.

## API

`GET /forecast?lat=32.9297&lon=10.4518&capacity_kw=10&days=7&use_news=true`

| Parameter | Meaning | Default |
|---|---|---|
| `lat`, `lon` | Roof position (Tunisia) | required |
| `capacity_kw` | Plant size | 10 |
| `days` | Forecast horizon, 1–14 | 7 |
| `n_tokens` | Tokens issued for the plant | 1000 |
| `tariff` | DT/kWh | STEG tariff for the plant size (0.217 under 1 MW) |
| `use_news` | Let the news agent set the coefficient | false |
| `news_coef` | Manual coefficient (ignored if `use_news=true`) | 1.0 |

The response contains, per day, `kwh`, `kwh_low`, `kwh_high`, `revenue_dt`, `dividend_per_token_dt` (+ low/high), then `totals`, an optional `news` block and `report_hash`. `GET /news` returns the news analysis alone, `GET /health` a status check.

## Hedera integration (HCS)

Every report has a SHA-256 hash, computed over the canonical JSON: `report_hash` removed, every number replaced by a fixed-decimal string (6 decimals, trailing zeros removed: `5939.0` → `"5939"`, `0.00001` → `"0.00001"`), keys sorted, compact separators, UTF-8 (reference implementations: `aggregator.hash_report` in Python and `verify_hash.js` in Node.js; `python test_hash.py` checks both agree). `hcs_anchor.py` publishes this hash, with a few readable fields, as a message in an HCS topic:

```bash
python hcs_anchor.py create-topic              # once: creates the topic
python hcs_anchor.py anchor demo_report.json   # anchors a report
python hcs_anchor.py verify demo_report.json 1 # checks the report against message #1 (Mirror Node)
```

Anyone can verify a report later: recompute its hash and compare it with the message on the Mirror Node. If a single number was changed, the hashes differ.

Anchoring is deliberately **not exposed as a public API route**, because it spends HBAR from the operator account. It is triggered by the backend or by the demo script.

Example anchored message: [TODO: paste the HashScan link after the first successful run]

## Repository layout

| File | Role |
|---|---|
| `collect_data.py` | Downloads PVGIS hourly data for the 12 cities |
| `model.py` | Aggregates by day, trains and saves the neural network |
| `test_ville_cachee.py` | Leave-one-city-out generalization test |
| `forecast.py` | Open-Meteo forecast -> daily features -> model prediction |
| `aggregator.py` | Dividend per token, report and hash |
| `news_agent.py` | News -> coefficient and risk level (keyword mode or Claude) |
| `api.py` | FastAPI server used by the dashboard |
| `check_pvgis_tilt.py` | Reads the real PVGIS tilt/azimuth per city |
| `evaluate_chain.py` | Error with Open-Meteo weather + calibrated interval |
| `verify_hash.js`, `test_hash.py` | Hash verification in JavaScript and Python cross-check |
| `hcs_anchor.py` | Anchoring and verification on Hedera Consensus Service |
| `demo.py` | End-to-end terminal demo |
| `solar_agent.pkl` | Trained model, scalers and error range |
