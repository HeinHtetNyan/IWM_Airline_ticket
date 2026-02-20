# IWM Airline Ticket — Monorepo

This repository contains the backend API for the IWM Airline Ticket booking system.

Quick links:
- API documentation: [docs/API.md](docs/API.md)
- API examples: [docs/EXAMPLES.md](docs/EXAMPLES.md)
- Backend service: `backend/`
- Docker compose: `infra/docker-compose.yml`

Getting started (recommended: Docker Compose)

1. Copy the environment example and edit values:

```bash
cp .env.example .env
# edit .env to set SECRET_KEY, TICKET_API_KEY, etc.
```

2. Start the stack (from `infra/`):

```bash
cd infra
docker-compose up --build
```

This starts the `backend` service on port `8000` and a Postgres database on `5433`.

Local development (without Docker)

1. Create a Python virtual environment and install requirements:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

2. Create a `.env` file (see `.env.example`) and ensure your `DATABASE_URL` points to a running Postgres instance.

3. Run the backend:

```bash
uvicorn app.main:app --reload --port 8000 --app-dir backend/app
```

API docs are available as markdown in `docs/` (this project also exposes OpenAPI at runtime at `/docs` when running the server).

If you want, I can also generate an OpenAPI JSON or a Postman collection.
# IWM_Airline_ticket
