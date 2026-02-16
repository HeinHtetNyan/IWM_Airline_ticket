from typing import List, Dict
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.flight_override import FlightOverride
from app.models.exchange_rate import ExchangeRate


GLOBAL_MARKUP_PERCENT = 15  # adjustable later


def apply_pricing_logic(
    db: Session,
    api_flights: List[Dict]
) -> List[Dict]:

    final_flights: List[Dict] = []

    # Get Exchange Rate (once per request)
    exchange = db.query(ExchangeRate).filter(ExchangeRate.id == 1).first()

    if not exchange:
        raise Exception("Exchange rate not configured")

    usd_to_mmk = exchange.usd_to_mmk

    for flight in api_flights:

        # Base API Price (raw reference)
        base_price_usd = flight["base_price_usd"]

        airline_code = flight["airline_code"]
        flight_number = flight["flight_number"]

        # Extract departure_date
        departure_time_str = flight["departure_time"]
        departure_date = datetime.fromisoformat(
            departure_time_str
        ).date()

        # Calculate system price (API + markup)
        system_price_usd = base_price_usd * (1 + GLOBAL_MARKUP_PERCENT / 100)

        # Check Flight Override (price floor)
        override = (
            db.query(FlightOverride)
            .filter(
                FlightOverride.airline_code == airline_code,
                FlightOverride.flight_number == flight_number,
                FlightOverride.departure_date == departure_date,
            )
            .first()
        )

        if override:
            final_price_usd = max(system_price_usd, override.override_price_usd)
        else:
            final_price_usd = system_price_usd

        final_price_usd = round(final_price_usd, 2)

        # Convert USD → MMK
        final_price_mmk = round(final_price_usd * usd_to_mmk, 2)

        # Price Estimate Range (USD based)
        price_estimate_min_usd = round(final_price_usd * 0.9, 2)
        price_estimate_max_usd = round(final_price_usd * 1.1, 2)

        # Price Estimate Range (MMK)
        price_estimate_min_mmk = round(price_estimate_min_usd * usd_to_mmk, 2)
        price_estimate_max_mmk = round(price_estimate_max_usd * usd_to_mmk, 2)

        # Update Flight Response
        flight["base_price_usd"] = round(base_price_usd, 2)  # keep raw API price
        flight["final_price_usd"] = final_price_usd
        flight["final_price_mmk"] = final_price_mmk
        flight["price_estimate_min_usd"] = price_estimate_min_usd
        flight["price_estimate_max_usd"] = price_estimate_max_usd
        flight["price_estimate_min_mmk"] = price_estimate_min_mmk
        flight["price_estimate_max_mmk"] = price_estimate_max_mmk
        flight["requires_admin_confirmation"] = True

        final_flights.append(flight)

    return final_flights
