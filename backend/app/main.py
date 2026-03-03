import logging
import time
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.flight_routes import router as flight_router
from app.api.router import api_router
from app.db.base import Base
from app.db.deps import get_db
from app.db.session import SessionLocal, engine
from app.services.booking_auto_cancel import auto_cancel_expired_bookings
from app.services.booking_auto_complete import auto_complete_bookings

app = FastAPI(title="Air Ticket Booking API")
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def lifecycle_job():
    db = SessionLocal()
    try:
        cancel_result = auto_cancel_expired_bookings(db, expire_minutes=30)
        complete_result = auto_complete_bookings(db)

        logger.info(
            "[LIFECYCLE] %s | Cancelled: %s | Confirmed: %s | Completed: %s",
            datetime.now(timezone.utc).isoformat(),
            cancel_result["cancelled_count"],
            cancel_result.get("confirmed_count", 0),
            complete_result["completed"],
        )

    except Exception as e:
        logger.exception("[LIFECYCLE ERROR] %s", e)

    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    max_retries = 10
    for attempt in range(max_retries):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database connected and tables created")
            break
        except OperationalError:
            logger.warning("Database not ready... retry %s/10", attempt + 1)
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
        logger.info("Lifecycle scheduler started (every 5 minutes)")


@app.on_event("shutdown")
def on_shutdown():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Lifecycle scheduler stopped")


app.include_router(api_router)
app.include_router(flight_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "FastAPI running in Docker"}


@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    return {"ok": bool(db.execute(text("SELECT 1")).scalar())}
