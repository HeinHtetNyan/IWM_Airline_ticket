from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from backend.app.models.flight_override import FlightOverride
from backend.app.schemas.flight_override import FlightOverrideCreate


def create_override(db: Session, override: FlightOverrideCreate):
    db_override = FlightOverride(
        airline_code=override.airline_code,
        flight_number=override.flight_number,
        departure_date=override.departure_date,
        override_price_usd=override.override_price_usd,
    )
    db.add(db_override)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Override already exists for this flight and date")
    db.refresh(db_override)
    return db_override


def get_all_overrides(db: Session):
    return db.query(FlightOverride).all()


def get_override_by_id(db: Session, override_id: str):
    return db.query(FlightOverride).filter(
        FlightOverride.id == override_id
    ).first()


def update_override_price(db: Session, override_id: str, new_price: float):
    override = get_override_by_id(db, override_id)
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")

    override.override_price_usd = new_price
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(override)
    return override


def delete_override(db: Session, override_id: str):
    override = get_override_by_id(db, override_id)
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")

    db.delete(override)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return override
