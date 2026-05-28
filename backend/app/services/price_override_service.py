from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.models.price_override import PriceOverride
from backend.app.schemas.price_override import PriceOverrideCreate


def create_price_override(db: Session, payload: PriceOverrideCreate) -> PriceOverride:
    now = datetime.now(timezone.utc)

    db.query(PriceOverride).filter(
        PriceOverride.airline_code == payload.airline_code,
        PriceOverride.flight_number == payload.flight_number,
        PriceOverride.departure_date == payload.departure_date,
        PriceOverride.is_active.is_(True),
    ).update({"is_active": False}, synchronize_session=False)

    expires_at = None
    if payload.duration_hours is not None:
        expires_at = now + timedelta(hours=payload.duration_hours)

    override = PriceOverride(
        airline_code=payload.airline_code,
        flight_number=payload.flight_number,
        departure_date=payload.departure_date,
        override_price_usd=payload.override_price_usd,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(override)
    db.commit()
    db.refresh(override)
    return override


def list_price_overrides(db: Session) -> list[PriceOverride]:
    return (
        db.query(PriceOverride)
        .order_by(PriceOverride.created_at.desc(), PriceOverride.id.desc())
        .all()
    )


def get_active_price_override(
    db: Session,
    airline_code: str | None,
    flight_number: str | None,
    departure_date: date | None,
    now: datetime | None = None,
) -> PriceOverride | None:
    if not airline_code or not flight_number or departure_date is None:
        return None

    current_time = now or datetime.now(timezone.utc)
    return (
        db.query(PriceOverride)
        .filter(
            PriceOverride.airline_code == airline_code.strip().upper(),
            PriceOverride.flight_number == flight_number.strip().upper(),
            PriceOverride.departure_date == departure_date,
            PriceOverride.is_active.is_(True),
            or_(
                PriceOverride.expires_at.is_(None),
                PriceOverride.expires_at > current_time,
            ),
        )
        .order_by(PriceOverride.created_at.desc(), PriceOverride.id.desc())
        .first()
    )


def deactivate_price_override(db: Session, override_id: UUID) -> PriceOverride | None:
    override = db.query(PriceOverride).filter(PriceOverride.id == override_id).first()
    if override is None:
        return None

    override.is_active = False
    db.commit()
    db.refresh(override)
    return override


def deactivate_expired_price_overrides(
    db: Session,
    now: datetime | None = None,
) -> int:
    current_time = now or datetime.now(timezone.utc)
    updated = (
        db.query(PriceOverride)
        .filter(
            PriceOverride.is_active.is_(True),
            PriceOverride.expires_at.is_not(None),
            PriceOverride.expires_at <= current_time,
        )
        .update({"is_active": False}, synchronize_session=False)
    )
    if updated:
        db.commit()
    return updated
