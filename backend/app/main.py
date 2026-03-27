import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from backend.app.api.router import api_router
from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.core.config import settings
from backend.app.services.booking_auto_cancel import auto_cancel_expired_bookings
from backend.app.services.booking_auto_complete import auto_complete_bookings


# PROMETHEUS IMPORTS 
# ============================================
from prometheus_fastapi_instrumentator import Instrumentator
# Import custom metrics from separate file to avoid duplicates
from backend.app.metrics import (
    bookings_created_total,
    searches_performed_total,
    users_registered_total,
    search_duration_seconds,
    booking_duration_seconds,
    active_users_gauge
)

# Logger
logger = logging.getLogger(__name__)

# Scheduler
scheduler = BackgroundScheduler()


def lifecycle_job():
    db = SessionLocal()
    try:
        cancel_result = auto_cancel_expired_bookings(db, expire_minutes=30)
        complete_result = auto_complete_bookings(db)

        print(
            f"[LIFECYCLE] {datetime.now(timezone.utc)} | "
            f"Cancelled: {cancel_result['cancelled_count']} | "
            f"Completed: {complete_result['completed']}"
        )

    except Exception:
        logger.exception("[LIFECYCLE ERROR] Failed running lifecycle job")

    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):

    # Wait for database
    max_retries = 10
    for attempt in range(max_retries):
        try:
            Base.metadata.create_all(bind=engine)
            print("Database connected and tables created")
            break

        except OperationalError:
            print(f"Database not ready... retry {attempt + 1}/10")
            time.sleep(2)

    else:
        raise RuntimeError("Could not connect to database")

    # Start scheduler
    if not scheduler.running:
        scheduler.add_job(
            lifecycle_job,
            "interval",
            minutes=5,
            id="lifecycle_job",
            replace_existing=True,
        )

        scheduler.start()
        print("Lifecycle scheduler started (every 5 minutes)")

    yield

    # Shutdown scheduler
    if scheduler.running:
        scheduler.shutdown(wait=False)



# FASTAPI APP CREATION

app = FastAPI(
    title="Air Ticket Booking API",
    description="Backend API for flight search and booking system",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)



# PROMETHEUS METRICS SETUP -


# Initialize Prometheus instrumentation
# This automatically tracks all HTTP requests
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=False,
    should_instrument_requests_inprogress=True,  # Tracks active requests
    excluded_handlers=["/metrics", "/api/health", "/health"],
)

# Attach metrics to app - ONLY ONCE!
instrumentator.instrument(app).expose(
    app, 
    endpoint="/metrics", 
    include_in_schema=False
)

print("✅ Prometheus metrics enabled")



# CORS MIDDLEWARE

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ROUTERS

app.include_router(api_router, prefix="/api")



# ROOT ENDPOINTS

@app.get("/")
def root():
    """Root endpoint - API information"""
    return {
        "message": "Airline Ticket Booking API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs",
        "health": "/api/health",
        "metrics": "/metrics"
    }


@app.get("/api/health")
def health_check():
    """Health check for monitoring"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "airline-backend",
        "version": "1.0.0"
    }