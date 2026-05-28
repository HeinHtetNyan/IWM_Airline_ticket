# Air Ticket Booking System — IWM

A full-stack airline ticket booking platform with a FastAPI backend, Nginx reverse proxy, PostgreSQL database, Redis cache, and a Prometheus/Grafana monitoring stack. Supports customer self-service booking, admin management, real-time flight search via an external API, email notifications, and automated booking lifecycle management.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Directory Structure](#directory-structure)
- [Prerequisites](#prerequisites)
- [Quick Start (Docker)](#quick-start-docker)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Authentication & Authorization](#authentication--authorization)
- [Database Schema](#database-schema)
- [Background Jobs](#background-jobs)
- [File Storage](#file-storage)
- [Email Service](#email-service)
- [Monitoring](#monitoring)
- [Running Tests](#running-tests)
- [CI/CD Pipelines](#cicd-pipelines)
- [Deployment](#deployment)
- [Rate Limiting](#rate-limiting)

---

## Architecture Overview

```
Client (Browser / Mobile)
        │
        ▼
  Nginx (port 8080)
  ├── /api/*  ──────────► FastAPI Backend (port 8000)
  │                               │
  │                       ┌───────┼────────┐
  │                       ▼       ▼        ▼
  │                  PostgreSQL  Redis  External
  │                  (port 5432) (6379)  Flight API
  │
  └── /files/* ─────────► Nginx static (uploads)

Monitoring (isolated network)
  Prometheus (9090) ◄── /metrics ── FastAPI
  Grafana    (3003) ◄── Prometheus
```

**Networks:**
- `app_network` — backend, db, redis, nginx
- `monitoring_network` — backend, prometheus, grafana

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Web Framework | FastAPI 0.115+ |
| ASGI Server | Uvicorn 0.30+ |
| Database | PostgreSQL 15-alpine |
| ORM | SQLAlchemy 2.0+ (async) |
| Migrations | Alembic 1.13+ *(schema managed via `create_all` at startup)* |
| Cache / Sessions | Redis 7-alpine |
| Authentication | JWT (PyJWT 2.8+) + Bcrypt (passlib) |
| HTTP Client | httpx 0.27+ (with retry) |
| Email | Mailtrap (primary) / SMTP2GO (fallback) |
| Templates | Jinja2 3.1+ |
| File Storage | Local filesystem or AWS S3 (Boto3 1.35+) |
| Scheduling | APScheduler 3.11+ |
| Metrics | prometheus-fastapi-instrumentator 6.1+ |
| Reverse Proxy | Nginx (alpine) |
| Containerization | Docker & Docker Compose |
| CI/CD | GitHub Actions |
| Testing | Pytest 7.4+ / pytest-cov |

---

## Directory Structure

```
IWM_Bug_Fix_V1/
├── backend/
│   ├── app/
│   │   ├── api/              # Route handlers (endpoints)
│   │   ├── auth/             # JWT & security utilities
│   │   ├── core/             # App config, Redis client, rate limiter
│   │   ├── crud/             # Database CRUD operations
│   │   ├── db/               # SQLAlchemy session & base
│   │   ├── health/           # Health check logic
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic layer
│   │   │   ├── external_flight_api.py
│   │   │   ├── pricing_engine.py
│   │   │   ├── email_service.py
│   │   │   ├── auth_token_service.py
│   │   │   ├── booking_auto_cancel.py
│   │   │   ├── booking_auto_complete.py
│   │   │   ├── booking_deletion.py
│   │   │   ├── storage_service.py
│   │   │   ├── rate_limit_service.py
│   │   │   ├── content_service.py
│   │   │   ├── contact_service.py
│   │   │   └── price_override_service.py
│   │   ├── templates/        # Jinja2 email templates
│   │   ├── main.py           # FastAPI application entry point
│   │   └── metrics.py        # Prometheus metric definitions
│   ├── requirements.txt
│   └── tests/
│       └── test_smoke.py
├── infra/
│   ├── Dockerfile
│   ├── Dockerfile.test
│   ├── docker-compose.yml          # Local development
│   ├── docker-compose.staging.yml  # Staging overrides
│   ├── docker-compose.prod.yml     # Production overrides
│   ├── prometheus.yml
│   ├── nginx/
│   │   ├── default.conf            # Development Nginx config
│   │   └── staging.conf            # Staging Nginx config
│   ├── grafana/
│   │   └── provisioning/           # Grafana datasource & dashboard configs
│   └── frontend/
│       └── build/                  # Pre-built frontend static files
├── .github/
│   └── workflows/
│       ├── ci.yml                  # Test & Docker build
│       ├── cd-staging.yml          # Deploy to staging
│       └── cd-production.yml       # Deploy to production
├── .env.example                    # Environment variable template
└── README.md
```

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/) v2+
- Git

For local development without Docker:
- Python 3.12+
- PostgreSQL 15+
- Redis 7+

---

## Quick Start (Docker)

### 1. Clone and configure environment

```bash
git clone <repository-url>
cd IWM_Bug_Fix_V1

cp .env.example .env
```

Open `.env` and fill in the required values (see [Environment Variables](#environment-variables) below). At minimum:

```bash
# Generate a secure JWT secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Start all services

```bash
cd infra
docker compose up -d
```

This starts:

| Service | URL | Notes |
|---|---|---|
| App (via Nginx) | http://localhost:8080 | Main entry point |
| API Docs (Swagger) | http://localhost:8000/api/docs | Dev only |
| API ReDoc | http://localhost:8000/api/redoc | Dev only |
| Health Check | http://localhost:8000/api/health | |
| PostgreSQL | localhost:5433 | Host-accessible |
| Prometheus | http://localhost:9090 | |
| Grafana | http://localhost:3003 | See env for credentials |

### 3. Verify the stack

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{"status": "ok"}
```

### 4. Stop services

```bash
# Stop without removing volumes
docker compose down

# Stop and remove all data volumes
docker compose down -v
```

---

## Environment Variables

Copy `.env.example` to `.env` and configure the following. **Never commit `.env` to version control.**

### Application

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `Air Ticket Booking API` | Application display name |
| `APP_VERSION` | `1.0.0` | API version |
| `ENVIRONMENT` | `development` | `development` / `staging` / `production` |
| `BASE_URL` | `http://localhost:8000` | Backend base URL for generated file links |
| `BACKEND_PORT` | `8000` | Internal FastAPI port |
| `NGINX_PORT` | `8080` | Nginx host-exposed port |
| `FRONTEND_BASE_URL` | `http://localhost:5173` | Frontend URL for email links |
| `CORS_ALLOW_ORIGINS` | — | Comma-separated allowed origins |

### PostgreSQL

| Variable | Description |
|---|---|
| `POSTGRES_USER` | Database username |
| `POSTGRES_PASSWORD` | Database password |
| `POSTGRES_DB` | Database name |
| `POSTGRES_HOST` | Hostname (use `db` inside Docker) |
| `POSTGRES_PORT` | Internal port (default `5432`) |
| `POSTGRES_HOST_PORT` | Host-exposed port (default `5433`) |
| `DB_POOL_SIZE` | SQLAlchemy pool size |
| `DB_MAX_OVERFLOW` | Pool overflow limit |
| `DB_POOL_TIMEOUT` | Pool checkout timeout (seconds) |
| `DB_POOL_RECYCLE` | Connection recycle interval (seconds) |

### Redis

| Variable | Default | Description |
|---|---|---|
| `REDIS_PASSWORD` | — | Redis authentication password |
| `REDIS_HOST` | `redis` | Hostname (use `redis` inside Docker) |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `0` | Redis logical database index |
| `FLIGHT_CACHE_TTL` | `900` | Flight search cache TTL (seconds) |
| `TRUSTED_PROXY_CIDRS` | — | Comma-separated CIDR blocks for trusted proxies |

### JWT / Authentication

| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET` | — | **Required.** Secret key for signing tokens |
| `ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Access token lifetime |
| `TOKEN_EXPIRE_MINUTES_RESET` | `15` | Password reset token lifetime |
| `TOKEN_EXPIRE_MINUTES_VERIFY` | `15` | Email verification token lifetime |

### Email (Mailtrap — Primary)

| Variable | Description |
|---|---|
| `EMAIL_ENABLED` | `true` to enable email sending |
| `EMAIL_HOST` | SMTP host (`send.api.mailtrap.io`) |
| `EMAIL_PORT` | SMTP port (`587`) |
| `EMAIL_USERNAME` | SMTP username |
| `EMAIL_PASSWORD` | SMTP password |
| `MAILTRAP_API_TOKEN` | Mailtrap API token |
| `EMAIL_FROM` | Sender email address |
| `EMAIL_FROM_NAME` | Sender display name |

> **Fallback (SMTP2GO):** Uncomment the SMTP2GO block in `.env.example` and set matching credentials to switch providers.

### File Storage

| Variable | Default | Description |
|---|---|---|
| `STORAGE_TYPE` | `local` | `local` or `s3` |
| `UPLOAD_DIR` | `/app/uploads` | Local storage path inside container |
| `S3_BUCKET` | — | S3 bucket name (when `STORAGE_TYPE=s3`) |
| `S3_REGION` | — | AWS region |
| `S3_ACCESS_KEY` | — | AWS access key ID |
| `S3_SECRET_KEY` | — | AWS secret access key |
| `S3_BASE_URL` | — | CDN base URL for S3 files |

### External APIs

| Variable | Description |
|---|---|
| `TICKET_API_KEY` | RapidAPI key for flight search (AGO Travel) |
| `CURRENCY_API_KEY` | Currency conversion API key |

### Booking Lifecycle

| Variable | Default | Description |
|---|---|---|
| `BOOKING_AUTO_CANCEL_EXPIRE_MINUTES` | `30` | Auto-cancel PROCESSING bookings after this many minutes |
| `CANCELLED_BOOKING_DELETE_DAYS` | `7` | Delete CANCELLED bookings after this many days |
| `LIFECYCLE_JOB_INTERVAL_MINUTES` | `5` | How often the lifecycle scheduler runs |
| `STARTUP_DB_MAX_RETRIES` | `10` | DB connection retry attempts at startup |
| `STARTUP_DB_RETRY_DELAY_SECONDS` | `2` | Delay between DB retry attempts |

### Rate Limiting

| Variable | Default | Description |
|---|---|---|
| `RATE_LIMIT_FORGOT_PASSWORD` | `5` | Max forgot-password requests per window |
| `RATE_LIMIT_RESEND_EMAIL` | `5` | Max resend-verification requests per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `3600` | Rate limit window duration (seconds) |

### Monitoring

| Variable | Description |
|---|---|
| `GF_SECURITY_ADMIN_PASSWORD` | Grafana admin panel password |

---

## API Reference

All endpoints are prefixed with `/api` (enforced by Nginx in production). In local dev the backend is also directly accessible on port `8000`.

### Health

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/health` | None | Service health check |

### Authentication

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/customer/signup` | None | Register a customer account |
| POST | `/auth/customer/login` | None | Customer login (returns JWT) |
| POST | `/auth/customer/token` | None | OAuth2 token endpoint |
| POST | `/auth/admin/signup` | SUPER_ADMIN | Register admin/staff |
| POST | `/auth/admin/token` | None | Admin login (returns JWT) |
| POST | `/auth/verify-email` | None | Verify email with token |
| POST | `/auth/resend-verification` | None | Resend verification email |
| POST | `/auth/forgot-password` | None | Request password reset email |
| POST | `/auth/reset-password` | None | Complete password reset |
| POST | `/auth/change-password` | Customer | Change authenticated user's password |

### Flights

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/flights/search` | None | One-way flight search |
| GET | `/flights/search-round-trip` | None | Round-trip flight search |

**Query parameters:** `origin`, `destination`, `departure_date`, `return_date` (round-trip), `adults`, `page`

Results are cached in Redis for `FLIGHT_CACHE_TTL` seconds.

### Bookings

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/bookings/` | Customer | Create a new booking |
| POST | `/bookings/{booking_id}/passengers` | Customer | Add passengers to booking |
| GET | `/bookings/me` | Customer | List customer's own bookings |
| GET | `/bookings/{booking_id}` | Customer | Get booking details |

### Customers

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/customers/me` | Customer | Get own profile |
| PATCH | `/customers/me` | Customer | Update own profile |

### Contact

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/contact/` | Customer | Submit contact information |
| GET | `/contact/me` | Customer | Get saved contact info |
| PUT | `/contact/me` | Customer | Update contact info |

### Admin — Bookings

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/me` | Staff / SUPER_ADMIN | Get current admin profile |
| GET | `/admin/dashboard` | Staff / SUPER_ADMIN | Dashboard statistics |
| GET | `/admin/bookings` | Staff / SUPER_ADMIN | List all bookings (filterable) |
| POST | `/admin/bookings/auto-cancel` | Staff / SUPER_ADMIN | Manually trigger auto-cancel job |
| GET | `/admin/bookings/{booking_id}` | Staff / SUPER_ADMIN | Booking detail view |
| PUT | `/admin/bookings/{booking_id}` | Staff / SUPER_ADMIN | Update booking status |
| PUT | `/admin/bookings/{booking_id}/payment-status` | Staff / SUPER_ADMIN | Mark booking as paid |
| PUT | `/admin/bookings/{booking_id}/upload-ticket` | Staff / SUPER_ADMIN | Upload ticket file |
| GET | `/admin/bookings/{booking_id}/audit` | Staff / SUPER_ADMIN | Booking audit trail |
| DELETE | `/admin/bookings/{booking_id}` | SUPER_ADMIN | Delete booking |

### Admin — Exchange Rate & Pricing

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/exchange-rate` | Staff / SUPER_ADMIN | Get USD → MMK exchange rate |
| PUT | `/admin/exchange-rate` | SUPER_ADMIN | Update exchange rate |
| GET | `/pricing-config` | Staff / SUPER_ADMIN | Get global markup percentage |
| PUT | `/pricing-config` | SUPER_ADMIN | Update global markup |
| POST | `/price-overrides` | SUPER_ADMIN | Create a price override |
| GET | `/price-overrides` | Staff / SUPER_ADMIN | List price overrides |
| DELETE | `/price-overrides/{override_id}` | SUPER_ADMIN | Delete a price override |

### Content Management

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/content/background` | None | Get active website background |
| PUT | `/content/background` | SUPER_ADMIN | Upload new website background |
| GET | `/content/banners` | None | Get active banners |
| GET | `/content/banners/all` | Staff / SUPER_ADMIN | Get all banners (including inactive) |
| POST | `/content/banners` | SUPER_ADMIN | Create banner |
| PUT | `/content/banners/{banner_id}` | SUPER_ADMIN | Update banner |
| DELETE | `/content/banners/{banner_id}` | SUPER_ADMIN | Soft-delete banner |
| DELETE | `/content/banners/{banner_id}/permanent` | SUPER_ADMIN | Permanently delete banner |

### Files (Tickets)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/files/status/{booking_id}` | Customer / Staff | Check ticket upload status |
| PUT | `/files/replace/{booking_id}` | Staff / SUPER_ADMIN | Replace an uploaded ticket |
| GET | `/files/tickets/{booking_id}` | Customer / Staff | Download ticket (signed URL) |
| DELETE | `/files/{booking_id}` | SUPER_ADMIN | Delete ticket file |

### Metrics

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/metrics` | None | Prometheus metrics endpoint |

---

## Authentication & Authorization

### Mechanism

Bearer JWT tokens are used for all protected endpoints.

```
Authorization: Bearer <token>
```

### Token Structure

```json
{
  "sub": "<user-uuid>",
  "role": "CUSTOMER | STAFF | SUPER_ADMIN",
  "exp": <unix-timestamp>
}
```

### Role Hierarchy

| Role | Capabilities |
|---|---|
| `CUSTOMER` | Search flights, create/view own bookings, manage profile |
| `STAFF` | All customer capabilities + view all bookings, upload tickets, update payment status |
| `SUPER_ADMIN` | All STAFF capabilities + manage admins, pricing, exchange rates, content, delete operations |

### Token Lifetimes

| Token Type | Duration |
|---|---|
| Access token | 60 minutes (configurable) |
| Email verification | 15 minutes (configurable) |
| Password reset | 15 minutes (configurable) |

---

## Database Schema

The database is auto-created at startup using SQLAlchemy `create_all()`. The following tables are created:

| Table | Description |
|---|---|
| `customer_users` | Customer accounts (UUID PK, email, bcrypt hash, verification flag) |
| `admin_users` | Admin/staff accounts with role (`STAFF` / `SUPER_ADMIN`) |
| `bookings` | Flight bookings with status/payment lifecycle fields and JSON flight snapshot |
| `booking_passengers` | Passenger details linked to a booking (unique per passport + booking) |
| `auth_tokens` | Email verification and password reset tokens (hashed, single-use) |
| `booking_deletion_logs` | Audit log for deleted bookings |
| `pricing_config` | Singleton row — global markup percentage |
| `price_overrides` | Per-flight price overrides with optional expiry |
| `exchange_rates` | USD to MMK exchange rate |
| `airport` | Airport reference data (IATA code, name) |
| `customer_contact` | Saved contact details per customer |
| `website_background` | Active background image for the frontend |
| `website_banner` | Promotional banners with ordering and soft-delete support |

### Booking Status Flow

```
PROCESSING  ──(auto-cancel after 30 min or admin cancel)──► CANCELLED
     │
     │ (admin confirms + marks paid)
     ▼
CONFIRMED  ──(admin completes or auto-complete)──► COMPLETED
```

### Payment Status

`PENDING` → `PAID` (or `FAILED`)

---

## Background Jobs

APScheduler runs background tasks on a configurable interval (`LIFECYCLE_JOB_INTERVAL_MINUTES`, default 5 min). A Redis-based distributed lock ensures only one instance executes the jobs in multi-replica deployments.

| Job | Trigger | Action |
|---|---|---|
| Auto-cancel | Booking is PROCESSING for > `BOOKING_AUTO_CANCEL_EXPIRE_MINUTES` | Sets status to CANCELLED |
| Auto-complete | Booking is CONFIRMED and flight has departed | Sets status to COMPLETED |
| Delete old bookings | Booking is CANCELLED for > `CANCELLED_BOOKING_DELETE_DAYS` days | Soft-deletes record and logs deletion |
| Deactivate overrides | `price_overrides.expires_at` < now | Sets `is_active = false` |

---

## File Storage

Two storage backends are supported, selected by `STORAGE_TYPE`:

### Local (default)

Files are stored in `UPLOAD_DIR` (`/app/uploads` inside the container), backed by a named Docker volume (`uploads_data`). Nginx serves files at `/files/*`.

### S3

Set `STORAGE_TYPE=s3` and configure `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, and `S3_BASE_URL`. The application will upload directly to S3 and return CDN URLs.

---

## Email Service

Email is sent via Mailtrap (configurable). The service sends:

- **Email verification** — on customer signup
- **Password reset** — on forgot-password request
- **Booking confirmation** — when a booking is created

Set `EMAIL_ENABLED=false` to disable all outgoing email (useful in local/CI environments).

Email templates are Jinja2 HTML templates located in `backend/app/templates/`.

---

## Monitoring

### Prometheus

Prometheus scrapes the `/metrics` endpoint every 15 seconds. Custom metrics exported:

| Metric | Type | Description |
|---|---|---|
| `bookings_created_total` | Counter | Total bookings created |
| `searches_performed_total` | Counter | Total flight searches |
| `users_registered_total` | Counter | Total customer registrations |
| `search_duration_seconds` | Histogram | Flight search response time |
| `booking_duration_seconds` | Histogram | Booking creation duration |
| `active_users_current` | Gauge | Currently active sessions |

Access Prometheus at: http://localhost:9090

### Grafana

Grafana is pre-provisioned with Prometheus as a datasource. Access at http://localhost:3003 (login with the password set in `GF_SECURITY_ADMIN_PASSWORD`).

---

## Running Tests

### Via Docker (recommended)

```bash
cd infra

# Requires .env.test file (see .env.example for reference variables)
docker compose --profile test up test_runner --build
```

Test results are written to a named volume at `/app/test_results/results.xml`.

### Via GitHub Actions

Tests run automatically on every push and pull request targeting `main` or `Bug_Fix_V1`. See `.github/workflows/ci.yml`.

### Locally (without Docker)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Set minimum required environment variables
export ENVIRONMENT=test
export JWT_SECRET=test-secret
export POSTGRES_USER=testuser
# ... (other vars)

pytest tests/ -v --tb=short
```

---

## CI/CD Pipelines

### `ci.yml` — Continuous Integration

**Triggers:** Push to `main` / `Bug_Fix_V1`, PRs targeting `main`

Steps:
1. Setup Python 3.11
2. Cache pip packages
3. Run smoke tests against ephemeral Postgres + Redis services
4. Build Docker image
5. Validate `docker-compose.yml` configuration
6. Push image to Docker Hub as `flyqm/air_ticket:<git-sha>` (on push only)

### `cd-staging.yml` — Staging Deployment

**Trigger:** Successful CI run on the `Bug_Fix_V1` branch

Steps:
1. SSH into the staging server
2. Pull the new Docker image
3. Pull latest code from `Bug_Fix_V1`
4. Restart backend and Nginx containers
5. Run health-check loop (30 attempts × 2 s)
6. Automatic rollback to the previous image on failure

### `cd-production.yml` — Production Deployment

**Trigger:** Successful CI run on the `main` branch

Same flow as staging, targeting the production server and `.env` file.

---

## Deployment

### Local Development

```bash
cd infra
docker compose up -d
```

### Staging

```bash
cd infra
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d
```

Staging uses `.env.staging` on the server and exposes Nginx on port `8081`, Prometheus on `9091`, Grafana on `3004`.

### Production

```bash
cd infra
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Production uses `.env` (or `.env.prod`) on the server. Swagger/ReDoc UI is disabled in production (`DOCS_URL=null`).

---

## Rate Limiting

Rate limits are enforced per IP address using Redis counters.

| Endpoint | Limit | Window |
|---|---|---|
| `POST /auth/forgot-password` | 5 requests | 3600 seconds |
| `POST /auth/resend-verification` | 5 requests | 3600 seconds |
| `GET /flights/search` | 30 requests | 60 seconds |
| `POST /auth/customer/signup` | 5 requests | 60 seconds |

Limits are configurable via environment variables. Clients that exceed the limit receive `429 Too Many Requests`.

---

## Security Notes

- All passwords are hashed with Bcrypt before storage — plaintext passwords are never persisted.
- JWT secrets must be strong random values; generate with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.
- Password reset and email verification tokens are stored as SHA-256 hashes and are single-use.
- The Postgres port (`5433`) is bound to `127.0.0.1` only — not publicly accessible.
- Swagger UI and ReDoc are disabled in production via `DOCS_URL=null` / `REDOC_URL=null`.
- CORS origins are explicitly whitelisted via `CORS_ALLOW_ORIGINS`.
- Trusted proxy CIDRs should be configured via `TRUSTED_PROXY_CIDRS` for accurate IP-based rate limiting behind Nginx.
