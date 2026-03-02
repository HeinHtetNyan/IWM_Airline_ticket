from typing import List, Dict
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import HTTPException

from app.models.flight_override import FlightOverride
from app.models.exchange_rate import ExchangeRate


GLOBAL_MARKUP_PERCENT = 15


def _get_exchange_rate(db: Session) -> float:
    exchange = db.query(ExchangeRate).filter(ExchangeRate.id == 1).first()

    if not exchange:
        raise HTTPException(
            status_code=500,
            detail="System configuration error: exchange rate not set"
        )

    if exchange.usd_to_mmk <= 0:
        raise HTTPException(
            status_code=500,
            detail="System configuration error: invalid exchange rate"
        )

    return exchange.usd_to_mmk


# ONE WAY PRICING
def apply_pricing_logic(
    db: Session,
    api_flights: List[Dict],
    adults: int = 1
) -> List[Dict]:

    usd_to_mmk = _get_exchange_rate(db)
    final_flights: List[Dict] = []

    for flight in api_flights:

        try:
            base_price_usd = float(flight["base_price_usd"])
        except (KeyError, ValueError, TypeError):
            continue

        airline_code = flight.get("airline_code")
        flight_number = flight.get("flight_number")

        departure_time_str = flight.get("departure_time")

        try:
            departure_date = datetime.fromisoformat(
                departure_time_str
            ).date()
        except Exception:
            continue

        system_price_usd = base_price_usd * (1 + GLOBAL_MARKUP_PERCENT / 100)

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
            final_price_per_pax_usd = max(
                system_price_usd,
                override.override_price_usd
            )
        else:
            final_price_per_pax_usd = system_price_usd

        final_price_per_pax_usd = round(final_price_per_pax_usd, 2)

        total_price_usd = round(final_price_per_pax_usd * adults, 2)
        total_price_mmk = round(total_price_usd * usd_to_mmk, 2)

        price_estimate_min_usd = round(total_price_usd * 0.9, 2)
        price_estimate_max_usd = round(total_price_usd * 1.1, 2)

        price_estimate_min_mmk = round(price_estimate_min_usd * usd_to_mmk, 2)
        price_estimate_max_mmk = round(price_estimate_max_usd * usd_to_mmk, 2)

        flight["base_price_usd"] = round(base_price_usd, 2)
        flight["adults"] = adults
        flight["final_price_usd"] = total_price_usd
        flight["final_price_mmk"] = total_price_mmk
        flight["price_estimate_min_usd"] = price_estimate_min_usd
        flight["price_estimate_max_usd"] = price_estimate_max_usd
        flight["price_estimate_min_mmk"] = price_estimate_min_mmk
        flight["price_estimate_max_mmk"] = price_estimate_max_mmk
        flight["requires_admin_confirmation"] = True

        final_flights.append(flight)

    return final_flights


# ROUND TRIP PRICING
def apply_round_trip_pricing_logic(
    db: Session,
    bundles: List[Dict],
    adults: int = 1
) -> List[Dict]:

    usd_to_mmk = _get_exchange_rate(db)
    final_results: List[Dict] = []

    for bundle in bundles:

        try:
            base_price_usd = float(bundle["base_price_usd"])
        except (KeyError, ValueError, TypeError):
            continue

        final_price_per_pax_usd = base_price_usd * (
            1 + GLOBAL_MARKUP_PERCENT / 100
        )
        final_price_per_pax_usd = round(final_price_per_pax_usd, 2)

        total_price_usd = round(final_price_per_pax_usd * adults, 2)
        total_price_mmk = round(total_price_usd * usd_to_mmk, 2)

        price_estimate_min_usd = round(total_price_usd * 0.9, 2)
        price_estimate_max_usd = round(total_price_usd * 1.1, 2)

        price_estimate_min_mmk = round(price_estimate_min_usd * usd_to_mmk, 2)
        price_estimate_max_mmk = round(price_estimate_max_usd * usd_to_mmk, 2)

        result = {
            "bundle_key": bundle.get("bundle_key"),
            "adults": adults,
            "outbound": bundle.get("outbound"),
            "inbound": bundle.get("inbound"),
            "base_price_usd": base_price_usd,
            "final_price_usd": total_price_usd,
            "final_price_mmk": total_price_mmk,
            "price_estimate_min_usd": price_estimate_min_usd,
            "price_estimate_max_usd": price_estimate_max_usd,
            "price_estimate_min_mmk": price_estimate_min_mmk,
            "price_estimate_max_mmk": price_estimate_max_mmk,
            "requires_admin_confirmation": True,
        }

        final_results.append(result)

    return final_results