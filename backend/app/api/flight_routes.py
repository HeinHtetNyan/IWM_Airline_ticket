from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.services.external_flight_api import fetch_flights_from_external_api
from app.services.pricing_engine import apply_pricing_logic

router = APIRouter(prefix="/flights", tags=["flights"])


@router.get("/search")
def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    db: Session = Depends(get_db),
):

    api_flights = fetch_flights_from_external_api(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
    )

    final_flights = apply_pricing_logic(db, api_flights)

    return final_flights
