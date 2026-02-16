import time
from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.db.session import engine
from app.db.base import Base

from app.models.admin_user import AdminUser
from app.models.customer_user import CustomerUser
from app.models.booking import Booking
from app.db.deps import get_db
from app.api.router import api_router
from app.api.flight_routes import router as flight_router
from app.models.flight_override import FlightOverride


app = FastAPI(title="Air Ticket Booking API")


@app.on_event("startup")
def on_startup():
    max_retries = 10
    for attempt in range(max_retries):
        try:
            Base.metadata.create_all(bind=engine)
            print("✅ Database connected and tables created")
            return
        except OperationalError:
            print(f"⏳ Database not ready... retry {attempt + 1}/10")
            time.sleep(2)

    raise RuntimeError("Could not connect to database")


app.include_router(api_router)
app.include_router(flight_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "FastAPI running in Docker 🚀"}


@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    return {"ok": bool(db.execute(text("SELECT 1")).scalar())}
