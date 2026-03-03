from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.exchange_rate import ExchangeRate
from app.models.flight_override import FlightOverride


GLOBAL_MARKUP_PERCENT = Decimal("15")
MONEY_Q = Decimal("0.01")


def _money(value: Decimal) -> float:
    return float(value.quantize(MONEY_Q, rounding=ROUND_HALF_UP))


def _get_exchange_rate(db: Session) -> Decimal:
    exchange = db.query(ExchangeRate).filter(ExchangeRate.id == 1).first()

    if not exchange:
        raise HTTPException(
            status_code=500,
            detail="System configuration error: exchange rate not set",
        )

    if exchange.usd_to_mmk <= 0:
        raise HTTPException(
            status_code=500,
            detail="System configuration error: invalid exchange rate",
        )

    return Decimal(str(exchange.usd_to_mmk))


def _find_override(db: Session, airline_code: str | None, flight_number: str | None, departure_time_str: str | None):
    if not airline_code or not flight_number or not departure_time_str:
        return None

    try:
        departure_date = datetime.fromisoformat(departure_time_str).date()
    except Exception:
        return None

    return (
        db.query(FlightOverride)
        .filter(
            FlightOverride.airline_code == airline_code,
            FlightOverride.flight_number == flight_number,
            FlightOverride.departure_date == departure_date,
        )
        .first()
    )


def _with_markup(base_price_usd: Decimal) -> Decimal:
    return base_price_usd * (Decimal("1") + GLOBAL_MARKUP_PERCENT / Decimal("100"))


# ONE WAY PRICING
def apply_pricing_logic(
    db: Session,
    api_flights: List[Dict],
    adults: int = 1,
) -> List[Dict]:
    usd_to_mmk = _get_exchange_rate(db)
    final_flights: List[Dict] = []

    for flight in api_flights:
        try:
            base_price_usd = Decimal(str(flight["base_price_usd"]))
        except (KeyError, ValueError, TypeError):
            continue

        override = _find_override(
            db,
            flight.get("airline_code"),
            flight.get("flight_number"),
            flight.get("departure_time"),
        )

        system_price_usd = _with_markup(base_price_usd)
        if override and override.override_price_usd is not None:
            system_price_usd = max(system_price_usd, Decimal(str(override.override_price_usd)))

        final_price_per_pax_usd = _money(system_price_usd)

        total_price_usd = _money(Decimal(str(final_price_per_pax_usd)) * Decimal(adults))
        total_price_mmk = _money(Decimal(str(total_price_usd)) * usd_to_mmk)

        price_estimate_min_usd = _money(Decimal(str(total_price_usd)) * Decimal("0.9"))
        price_estimate_max_usd = _money(Decimal(str(total_price_usd)) * Decimal("1.1"))

        price_estimate_min_mmk = _money(Decimal(str(price_estimate_min_usd)) * usd_to_mmk)
        price_estimate_max_mmk = _money(Decimal(str(price_estimate_max_usd)) * usd_to_mmk)

        flight["base_price_usd"] = _money(base_price_usd)
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
    adults: int = 1,
) -> List[Dict]:
    usd_to_mmk = _get_exchange_rate(db)
    final_results: List[Dict] = []

    for bundle in bundles:
        try:
            outbound = bundle.get("outbound") or {}
            inbound = bundle.get("inbound") or {}

            outbound_base = Decimal(str(outbound.get("base_price_usd"))) if outbound.get("base_price_usd") is not None else None
            inbound_base = Decimal(str(inbound.get("base_price_usd"))) if inbound.get("base_price_usd") is not None else None

            if outbound_base is not None and inbound_base is not None:
                out_price = _with_markup(outbound_base)
                in_price = _with_markup(inbound_base)

                out_override = _find_override(db, outbound.get("airline_code"), outbound.get("flight_number"), outbound.get("departure_time"))
                in_override = _find_override(db, inbound.get("airline_code"), inbound.get("flight_number"), inbound.get("departure_time"))

                if out_override and out_override.override_price_usd is not None:
                    out_price = max(out_price, Decimal(str(out_override.override_price_usd)))
                if in_override and in_override.override_price_usd is not None:
                    in_price = max(in_price, Decimal(str(in_override.override_price_usd)))

                final_price_per_pax_usd = out_price + in_price
            else:
                base_price_usd = Decimal(str(bundle["base_price_usd"]))
                final_price_per_pax_usd = _with_markup(base_price_usd)
        except (KeyError, ValueError, TypeError):
            continue

        total_price_usd = _money(final_price_per_pax_usd * Decimal(adults))
        total_price_mmk = _money(Decimal(str(total_price_usd)) * usd_to_mmk)

        price_estimate_min_usd = _money(Decimal(str(total_price_usd)) * Decimal("0.9"))
        price_estimate_max_usd = _money(Decimal(str(total_price_usd)) * Decimal("1.1"))

        price_estimate_min_mmk = _money(Decimal(str(price_estimate_min_usd)) * usd_to_mmk)
        price_estimate_max_mmk = _money(Decimal(str(price_estimate_max_usd)) * usd_to_mmk)

        result = {
            "bundle_key": bundle.get("bundle_key"),
            "adults": adults,
            "outbound": bundle.get("outbound"),
            "inbound": bundle.get("inbound"),
            "base_price_usd": _money(final_price_per_pax_usd),
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
