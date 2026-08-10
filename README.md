# HAWK SCANNER

HAWK SCANNER is a modular quantitative crypto-intelligence platform. It ranks assets with a dynamically calibrated Hawk Score, records the full scoring lineage, learns similarity to historic breakouts, and delivers threshold alerts. It uses public market and on-chain data only.

## What is included

- Next.js 15 / React 19 dark, responsive dashboard built with Tailwind and reusable shadcn-style primitives.
- FastAPI REST API at `/api/v1`, JWT authentication, Redis rate limiting, Redis response caching, OpenAPI/Swagger at `/docs`.
- PostgreSQL schema managed by Prisma: 40+ normalized entities, time-series indexes, alert delivery audit and ML lineage.
- A worker that performs an immediate scan and then runs every 10 minutes through the scheduler.
- Daily XGBoost learning jobs for 90-day/300% and 30-day/500% breakout targets, storing feature snapshots, training metadata, artifacts and similarity scores.
- Strict, audited availability checks for CoinGecko, CoinGlass, DefiLlama, Binance, Coinbase, Hyperliquid, Bitquery, Covalent, Alchemy, Moralis, Etherscan, BscScan, Arbiscan, Basescan and Solscan.
- Automatic initial universe bootstrap from CoinGecko and Binance spot-market discovery.
- Candidate universe restricted to liquid, non-pegged, non-meme assets with market cap between US$30M and US$100M.
- Telegram, Discord and SMTP-email alert channels with per-delivery audit rows.
- Docker Compose services for PostgreSQL, Redis, Prisma migration, API, worker, scheduler and web.

## Run locally

Prerequisites: Docker Desktop with Compose enabled, and API credentials for the commercial data sources you intend to use.

1. Copy `.env.example` to `.env`.
2. Replace every placeholder secret. `JWT_SECRET` and `INTERNAL_SCHEDULER_TOKEN` must be different random values of at least 32 characters.
3. Set `POSTGRES_PASSWORD` and update the same password in `DATABASE_URL`.
4. Populate the required provider keys. Keep `REQUIRE_ALL_DATA_SOURCES=true` for live use.
5. Set `BOOTSTRAP_ADMIN_EMAIL` to your own address before registering the first account.
6. Start the platform:

```bash
docker compose up --build
```

Open the dashboard at `http://localhost:3000`, Swagger at `http://localhost:8000/docs`, API readiness at `http://localhost:8000/health/ready`, and worker readiness at `http://localhost:8001/health/ready`.

The `migrate` service applies `packages/database/prisma/migrations/202608080001_initial_schema` before the API or worker starts. The first worker scan imports the configured CoinGecko universe and Binance USDT spot pairs. Hawk Score remains deliberately in warm-up until enough cross-sectional return observations exist to estimate evidence and uncertainty; it will not emit fabricated scores.

## Operational contract

`REQUIRE_ALL_DATA_SOURCES=true` is fail-closed. A scan records one `logs` row per provider consultation and fails rather than publishing a partial ranking if a required source is unconfigured or unavailable. This setting may be turned off only for local interface development; resulting outputs are incomplete and must not be used for decisions.

The current ingestion path normalizes CoinGecko market data and Binance order-book/spot data into the first live score features, while the remaining mandatory providers are consulted and audited through the source registry. Their metric-specific adapters are intentionally isolated behind this registry so each provider's entitlement, rate limit and payload contract can be enabled independently without changing the score engine.

Automated alerting uses a strict `score > HAWK_ALERT_THRESHOLD` condition. A scanner run, alert, and each channel delivery are persisted independently. Configure only the channels you use; unconfigured channels are not sent.

## API surface

All resource endpoints are versioned below `/api/v1`.

| Area | Endpoints |
| --- | --- |
| Market | `GET /coins`, `/coin/{id}`, `/ranking`, `/metrics`, `/funding`, `/openinterest`, `/liquidations`, `/holders`, `/score`, `/similarity` |
| Authentication | `POST /auth/register`, `/auth/login`, `/auth/refresh`; `GET /auth/me` |
| User data | Watchlist and alert CRUD; `GET /subscription` |
| Administration | `GET /admin`, `/admin/users`, `/admin/plans`, `/admin/subscriptions`; `POST /admin/plans`, `/admin/subscriptions` |

Swagger is the authoritative request/response contract. All admin endpoints require an `ADMIN` or `SUPER_ADMIN` JWT. The email matching `BOOTSTRAP_ADMIN_EMAIL` receives `SUPER_ADMIN` only at first registration; remove that value after setup.

Subscription records and entitlements are operationally usable through admin grants. A payment-processor checkout/webhook integration is not enabled because no payment-provider account or signing secret was supplied; do not expose a paid checkout until one is configured.

## Architecture

```text
.
├── apps
│   ├── api
│   │   └── src/{application,config,domain,infrastructure,presentation}
│   ├── scheduler/hawk_scheduler
│   ├── web/{app,components,lib}
│   └── worker/hawk_worker/{ml,providers,repository,scanner}
├── packages/database
│   └── prisma/{migrations,schema.prisma}
├── docs/{operations,scoring}
├── docker-compose.yml
└── .env.example
```

The API follows a clean boundary: presentation routes → application/security and domain scoring → infrastructure adapters. The worker owns orchestration, provider clients and persistence. Prisma is the sole schema/migration authority; the Python services use parameterized SQL through a small repository boundary against that schema.

## Development and verification

```bash
# Prisma schema validation (from packages/database)
pnpm install
pnpm validate

# API/worker Python tests (after installing the relevant requirements)
PYTHONPATH=apps/api pytest apps/api/tests

# Frontend checks (from apps/web)
pnpm install
pnpm typecheck
pnpm build
```

See `docs/operations/scanner.md` for scanner lifecycle, `docs/operations/data-sources.md` for data-source responsibilities, `docs/scoring/hawk-score.md` for the adaptive score mathematics, and `docs/scoring/ml-similarity.md` for the daily learning workflow.

## Security and deployment notes

- `.env` is ignored; do not commit tokens, passwords or provider credentials.
- Keep PostgreSQL and Redis on the private Compose network. Only web (`3000`) and API (`8000`) are published by default.
- Put a TLS reverse proxy, secret manager, backup policy, central log sink and production-grade monitoring in front of an Internet-facing deployment.
- Public-data analytics are informational and not investment advice. Evaluate data licensing, geographic restrictions, market risk and model performance independently.
