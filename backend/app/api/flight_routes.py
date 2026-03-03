from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.services.external_flight_api import (
    fetch_flights_from_external_api,
    fetch_round_trip_from_external_api,
)
from app.services.pricing_engine import apply_pricing_logic, apply_round_trip_pricing_logic

router = APIRouter(prefix="/flights", tags=["flights"])


def _parse_date(value: str, field_name: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field_name} must be YYYY-MM-DD")
    if parsed < date.today():
        raise HTTPException(status_code=400, detail=f"{field_name} cannot be in the past")
    return parsed


@router.get("/search")
def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    page: int = Query(1, ge=1),
    adults: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    _parse_date(departure_date, "departure_date")
    api_flights = fetch_flights_from_external_api(origin=origin, destination=destination, departure_date=departure_date, page=page)
    return apply_pricing_logic(db, api_flights, adults)


@router.get("/search-round-trip")
def search_round_trip(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    page: int = Query(1, ge=1),
    adults: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    dep = _parse_date(departure_date, "departure_date")
    ret = _parse_date(return_date, "return_date")
    if ret < dep:
        raise HTTPException(status_code=400, detail="return_date must be on/after departure_date")

    bundles = fetch_round_trip_from_external_api(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        page=page,
    )
    return apply_round_trip_pricing_logic(db, bundles, adults)
