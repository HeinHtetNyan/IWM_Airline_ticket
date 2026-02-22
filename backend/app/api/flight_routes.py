from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.deps import get_db
from backend.app.services.external_flight_api import (
    fetch_flights_from_external_api,
    fetch_round_trip_from_external_api
)
from backend.app.services.pricing_engine import (
    apply_pricing_logic,
    apply_round_trip_pricing_logic
)

router = APIRouter(prefix="/flights", tags=["flights"])


# One Way Search
@router.get("/search")
def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    page: int = 1,
    adults: int = 1,
    db: Session = Depends(get_db),
):

    if adults < 1:
        raise HTTPException(status_code=400, detail="Adults must be at least 1")

    api_flights = fetch_flights_from_external_api(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        page=page,
    )

    final_flights = apply_pricing_logic(db, api_flights, adults)

    return final_flights


# Round Trip Search
@router.get("/search-round-trip")
def search_round_trip(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    page: int = 1,
    adults: int = 1,
    db: Session = Depends(get_db),
):

    if adults < 1:
        raise HTTPException(status_code=400, detail="Adults must be at least 1")

    bundles = fetch_round_trip_from_external_api(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        page=page,
    )

    final_results = apply_round_trip_pricing_logic(db, bundles, adults)

    return final_results
