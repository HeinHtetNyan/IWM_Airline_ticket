import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.flight_routes import router as flight_router
from app.api.router import api_router
from app.db.base import Base
from app.db.deps import get_db
from app.db.session import SessionLocal, engine
from app.core.config import settings
from app.models.admin_user import AdminUser
from app.models.booking import Booking
from app.models.customer_user import CustomerUser
from app.models.flight_override import FlightOverride
from app.services.booking_auto_cancel import auto_cancel_expired_bookings
from app.services.booking_auto_complete import auto_complete_bookings

scheduler = BackgroundScheduler()
logger = logging.getLogger(__name__)


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

    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Air Ticket Booking API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(flight_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "FastAPI running in Docker"}


@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    return {"ok": bool(db.execute(text("SELECT 1")).scalar())}
