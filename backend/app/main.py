import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
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

        cancel_result = auto_cancel_expired_bookings(db, expire_minutes=30)
        complete_result = auto_complete_bookings(db)
        delete_result = auto_delete_expired_cancelled_bookings(
            db,
            delete_days=settings.CANCELLED_BOOKING_DELETE_DAYS,
        )

        print(
            f"[LIFECYCLE] {datetime.now(timezone.utc)} | "
            f"Cancelled: {cancel_result['cancelled_count']} | "
            f"Completed: {complete_result['completed']} | "
            f"Deleted: {delete_result['deleted_count']}"
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


# FastAPI app
app = FastAPI(
    title="Air Ticket Booking API",
    description="Backend API for flight search and booking system",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


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
    return {"message": "FastAPI running in Docker"}
