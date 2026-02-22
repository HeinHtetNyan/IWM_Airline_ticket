import time
from datetime import datetime
from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from apscheduler.schedulers.background import BackgroundScheduler

from backend.app.db.session import engine, SessionLocal
from backend.app.db.base import Base
from backend.app.db.deps import get_db

from backend.app.models.admin_user import AdminUser
from backend.app.models.customer_user import CustomerUser
from backend.app.models.booking import Booking
from backend.app.models.flight_override import FlightOverride

from backend.app.services.booking_auto_cancel import auto_cancel_expired_bookings
from backend.app.services.booking_auto_complete import auto_complete_bookings

from backend.app.api.router import api_router
from backend.app.api.flight_routes import router as flight_router

app = FastAPI(
    title="Air Ticket Booking API",
    description="Backend API for flight search and booking system",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc"
)

scheduler = BackgroundScheduler()

# LIFECYCLE JOB
def lifecycle_job():
    db = SessionLocal()
    try:
        # Auto Cancel PROCESSING → CANCELLED
        cancel_result = auto_cancel_expired_bookings(db, expire_minutes=30)

        # Auto Complete CONFIRMED → COMPLETED
        complete_result = auto_complete_bookings(db)

        print(
            f"[LIFECYCLE] {datetime.utcnow()} | "
            f"Cancelled: {cancel_result['cancelled_count']} | "
            f"Completed: {complete_result['completed']}"
        )

    except Exception as e:
        print(f"[LIFECYCLE ERROR] {e}")

    finally:
        db.close()


# STARTUP
@app.on_event("startup")
def on_startup():
    # Wait for DB
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

    # Start Scheduler
    if not scheduler.running:
        scheduler.add_job(
            lifecycle_job,
            "interval",
            minutes=5,  # runs every 5 minutes
            id="lifecycle_job",
            replace_existing=True,
        )
        scheduler.start()
        print("Lifecycle scheduler started (every 5 minutes)")


# SHUTDOWN (clean up scheduler)
@app.on_event("shutdown")
def on_shutdown():
    if scheduler.running:
        scheduler.shutdown()
        print("Lifecycle scheduler shut down")


# Include all routers
app.include_router(api_router)
app.include_router(flight_router, prefix="/api")


