# Backend — IWM Airline Ticket

Location: `backend/`

Prerequisites
- Python 3.11+ (local dev) or Docker
- Postgres (if running locally)

Environment
- The backend reads settings from a `.env` file (see project root `.env.example`). Required variables:
  - `DATABASE_URL` (example: `postgresql://airuser:airpassword@localhost:5433/airdb`)
  - `SECRET_KEY` (random secret used for JWT)
  - `TICKET_API_KEY` (external ticket API key)
  - `ACCESS_TOKEN_EXPIRE_MINUTES` (optional; default 60)

Run locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# ensure .env exists with DATABASE_URL etc.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run with Docker (recommended for full stack)

```bash
cd infra
docker-compose up --build
```

Useful paths
- API routes: `backend/app/api/`
- Schemas: `backend/app/schemas/`
- Models: `backend/app/models/`
- Services: `backend/app/services/`

Docs
- Developer documentation and examples: `docs/API.md`, `docs/EXAMPLES.md`

Testing
- There are currently no automated tests included. I can add a minimal pytest harness if you want.
