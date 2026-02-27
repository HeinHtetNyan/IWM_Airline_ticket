from sqlalchemy.orm import Session
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
    db.commit()
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
    if override:
        override.override_price_usd = new_price
        db.commit()
        db.refresh(override)
    return override


def delete_override(db: Session, override_id: str):
    override = get_override_by_id(db, override_id)
    if override:
        db.delete(override)
        db.commit()
    return override
