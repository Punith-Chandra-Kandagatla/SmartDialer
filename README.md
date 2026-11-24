# SMARTDIALER
### The Intelligence Behind Every Call

SmartDialer is an intelligent outbound dialing platform designed to improve agent utilization through adaptive predictive pacing, progressive dialing, and independent safety controls.

## Key Features

- Progressive dialing with agent-borrower reservation.
- Predictive pacing using historical answer rates and call duration.
- Independent Safety Controller to approve, reduce, or reject dialing recommendations.
- Concurrent reservation protection using PostgreSQL transactions.
- Multiple mock telecom providers with different reliability characteristics.
- Idempotent call execution and provider event processing.
- Execution recovery and provider reconciliation.
- Real-time campaign and operational dashboard.
- Predictive simulation and performance benchmarking.

## Architecture

Campaign Manager → Borrower Queue → Dialing Strategy → Safety Controller → Call Allocator → Provider Manager → Telecom Providers → Event Processor → PostgreSQL.

See `docs/architecture.md` for the detailed architecture.

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Frontend | React, Vite |
| Charts | Recharts |
| Testing | Pytest, HTTPX |
| Providers | Mock Telecom Providers |

## Project Structure

```text
SMARTDIALER/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── providers/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── src/
├── simulation/
│   ├── run_simulation.py
│   └── load_test.py
├── docs/
│   ├── architecture.md
│   └── performance.md
├── .env.example
└── README.md