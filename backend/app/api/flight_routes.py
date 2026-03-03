from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.services.external_flight_api import (
    fetch_flights_from_external_api,
    fetch_round_trip_from_external_api,
)
from app.services.pricing_engine import (
    apply_pricing_logic,
    apply_round_trip_pricing_logic,
)

router = APIRouter(prefix="/flights", tags=["flights"])


# One Way Search
@router.get("/search")
def search_flights(
    origin: str,
    destination: str,
    departure_date: date,
    page: int = Query(1, ge=1),
    adults: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    api_flights = fetch_flights_from_external_api(
        origin=origin,
        destination=destination,
        departure_date=departure_date.isoformat(),
        page=page,
    )

    final_flights = apply_pricing_logic(db, api_flights, adults)

    return final_flights


# Round Trip Search
@router.get("/search-round-trip")
def search_round_trip(
    origin: str,
    destination: str,
    departure_date: date,
    return_date: date,
    page: int = Query(1, ge=1),
    adults: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    if return_date < departure_date:
        raise HTTPException(status_code=400, detail="return_date must be on or after departure_date")

    bundles = fetch_round_trip_from_external_api(
        origin=origin,
        destination=destination,
        departure_date=departure_date.isoformat(),
        return_date=return_date.isoformat(),
        page=page,
    )

    final_results = apply_round_trip_pricing_logic(db, bundles, adults)

    return final_results
