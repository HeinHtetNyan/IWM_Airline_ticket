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


# FastAPI app
app = FastAPI(
    title="Air Ticket Booking API",
    description="Backend API for flight search and booking system",
    version="1.0.0",
    root_path="/api",
    lifespan=lifespan,
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers
app.include_router(api_router)


# Root endpoint
@app.get("/")
def root():
    return {"message": "FastAPI running in Docker"}
