import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from backend.app.api.router import api_router
from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.core.config import settings
from backend.app import models  # noqa: F401
from backend.app.core.redis import redis_client

from backend.app.services.booking_auto_cancel import auto_cancel_expired_bookings
from backend.app.services.booking_auto_complete import auto_complete_bookings
from backend.app.services.booking_deletion import auto_delete_expired_cancelled_bookings
from backend.app.services.price_override_service import deactivate_expired_price_overrides



# PROMETHEUS IMPORTS
# ============================================
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    # Import custom metrics from separate file to avoid duplicates
    from backend.app.metrics import (
        bookings_created_total,
        searches_performed_total,
        users_registered_total,
        search_duration_seconds,
        booking_duration_seconds,
        active_users_gauge,
    )
except ImportError:
    Instrumentator = None


# Logger
logger = logging.getLogger(__name__)

# Scheduler
scheduler = BackgroundScheduler()
_LIFECYCLE_LOCK_KEY = "locks:lifecycle_job"
_LIFECYCLE_LOCK_TTL_SECONDS = 240
_RELEASE_LIFECYCLE_LOCK_SCRIPT = redis_client.register_script(
    """
    if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("DEL", KEYS[1])
    end
    return 0
    """
)


def lifecycle_job():
    lock_value = str(uuid4())
    lock_acquired = False
    db = SessionLocal()
    try:
        try:
            lock_acquired = bool(
                redis_client.set(
                    _LIFECYCLE_LOCK_KEY,
                    lock_value,
                    ex=_LIFECYCLE_LOCK_TTL_SECONDS,
                    nx=True,
                )
            )
        except Exception:
            logger.exception("[LIFECYCLE ERROR] Failed to acquire distributed lifecycle lock")
            return

        if not lock_acquired:
            logger.info("[LIFECYCLE] Skipping run because another instance holds the job lock")
            return

        cancel_result = auto_cancel_expired_bookings(
            db,
            expire_minutes=settings.BOOKING_AUTO_CANCEL_EXPIRE_MINUTES,
        )
        complete_result = auto_complete_bookings(db)
        delete_result = auto_delete_expired_cancelled_bookings(
            db,
            delete_days=settings.CANCELLED_BOOKING_DELETE_DAYS,
        )
        expired_overrides = deactivate_expired_price_overrides(db)
        logger.info(
            "[LIFECYCLE] %s | Cancelled: %s | Completed: %s | Deleted: %s | Expired overrides: %s",
            datetime.now(timezone.utc),
            cancel_result["cancelled_count"],
            complete_result["completed"],
            delete_result["deleted_count"],
            expired_overrides,
        )

    except Exception:
        logger.exception("[LIFECYCLE ERROR] Failed running lifecycle job")

    finally:
        if lock_acquired:
            try:
                _RELEASE_LIFECYCLE_LOCK_SCRIPT(
                    keys=[_LIFECYCLE_LOCK_KEY],
                    args=[lock_value],
                )
            except Exception:
                logger.exception("[LIFECYCLE WARNING] Failed to release distributed lifecycle lock")
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):

    # Wait for database
    max_retries = settings.STARTUP_DB_MAX_RETRIES
    for attempt in range(max_retries):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database connected and tables created")
            break

        except OperationalError:
            logger.warning(
                "Database not ready... retry %s/%s",
                attempt + 1,
                max_retries,
            )
            time.sleep(settings.STARTUP_DB_RETRY_DELAY_SECONDS)

    else:
        raise RuntimeError("Could not connect to database")

    # Start scheduler
    if not scheduler.running:
        scheduler.add_job(
            lifecycle_job,
            "interval",
            minutes=settings.LIFECYCLE_JOB_INTERVAL_MINUTES,
            id="lifecycle_job",
            replace_existing=True,
        )

        scheduler.start()
        logger.info(
            "Lifecycle scheduler started (every %s minutes)",
            settings.LIFECYCLE_JOB_INTERVAL_MINUTES,
        )

    yield

    # Shutdown scheduler
    if scheduler.running:
        scheduler.shutdown(wait=False)


# FastAPI app
_is_production = settings.ENVIRONMENT.lower() in {"production", "prod"}

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url=None if _is_production else "/api/docs",
    redoc_url=None if _is_production else "/api/redoc",
    openapi_url=None if _is_production else "/api/openapi.json",
    lifespan=lifespan,
)

if settings.STORAGE_TYPE.lower() == "local":
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


# PROMETHEUS METRICS SETUP -
if Instrumentator is not None:
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
        include_in_schema=False,
    )
    logger.info("Prometheus metrics enabled")
else:
    logger.warning(
        "Prometheus instrumentation package is not installed; continuing without /metrics exposure"
    )

print("✅ Prometheus metrics enabled")



# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers
app.include_router(api_router, prefix="/api")

# Root endpoint
@app.get("/")
def root():
    return {"message": settings.APP_ROOT_MESSAGE}


@app.get("/api/health")
def health_check():
    """Health check for monitoring"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "airline-backend",
        "version": "1.0.0"
    }
