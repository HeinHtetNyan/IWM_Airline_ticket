from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.exchange_rate import ExchangeRate
from backend.app.models.flight_override import FlightOverride

GLOBAL_MARKUP_PERCENT = Decimal("15")


def _quantize_money(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _to_decimal(value: Any, *, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"Invalid {field} in flight_snapshot")


def _get_exchange_rate(db: Session) -> Decimal:
    exchange = db.query(ExchangeRate).filter(ExchangeRate.id == 1).first()
    if not exchange or exchange.usd_to_mmk <= 0:
        raise HTTPException(status_code=500, detail="System configuration error: exchange rate not set")
    return Decimal(str(exchange.usd_to_mmk))


def _calc_final_price(base_price_usd: Decimal, override_price_usd: Decimal | None = None) -> Decimal:
    system_price_usd = base_price_usd * (Decimal("1") + (GLOBAL_MARKUP_PERCENT / Decimal("100")))
    if override_price_usd is not None:
        return _quantize_money(max(system_price_usd, override_price_usd))
    return _quantize_money(system_price_usd)


def apply_pricing_logic(db: Session, api_flights: List[Dict], adults: int = 1) -> List[Dict]:
    usd_to_mmk = _get_exchange_rate(db)
    final_flights: List[Dict] = []

    for flight in api_flights:
        try:
            base_price_usd = Decimal(str(flight["base_price_usd"]))
        except (KeyError, InvalidOperation, TypeError, ValueError):
            continue

        airline_code = flight.get("airline_code")
        flight_number = flight.get("flight_number")
        departure_time_str = flight.get("departure_time")
        try:
            departure_date = datetime.fromisoformat(departure_time_str).date()
        except Exception:
            continue

        override = db.query(FlightOverride).filter(
            FlightOverride.airline_code == airline_code,
            FlightOverride.flight_number == flight_number,
            FlightOverride.departure_date == departure_date,
        ).first()

        final_price_per_pax_usd = _calc_final_price(
            base_price_usd,
            Decimal(str(override.override_price_usd)) if override else None,
        )
        total_price_usd = _quantize_money(final_price_per_pax_usd * Decimal(adults))
        total_price_mmk = _quantize_money(total_price_usd * usd_to_mmk)

        flight["base_price_usd"] = float(_quantize_money(base_price_usd))
        flight["adults"] = adults
        flight["final_price_usd"] = float(total_price_usd)
        flight["final_price_mmk"] = float(total_price_mmk)
        flight["price_estimate_min_usd"] = float(_quantize_money(total_price_usd * Decimal("0.9")))
        flight["price_estimate_max_usd"] = float(_quantize_money(total_price_usd * Decimal("1.1")))
        flight["price_estimate_min_mmk"] = float(_quantize_money(Decimal(str(flight["price_estimate_min_usd"])) * usd_to_mmk))
        flight["price_estimate_max_mmk"] = float(_quantize_money(Decimal(str(flight["price_estimate_max_usd"])) * usd_to_mmk))
        flight["requires_admin_confirmation"] = True
        final_flights.append(flight)

    return final_flights


def apply_round_trip_pricing_logic(db: Session, bundles: List[Dict], adults: int = 1) -> List[Dict]:
    usd_to_mmk = _get_exchange_rate(db)
    final_results: List[Dict] = []

    for bundle in bundles:
        try:
            base_price_usd = Decimal(str(bundle["base_price_usd"]))
        except (KeyError, InvalidOperation, TypeError, ValueError):
            continue

        outbound = bundle.get("outbound") or {}
        override = None
        try:
            departure_date = datetime.fromisoformat(outbound.get("departure_time", "")).date()
            override = db.query(FlightOverride).filter(
                FlightOverride.airline_code == outbound.get("airline_code"),
                FlightOverride.flight_number == outbound.get("flight_number"),
                FlightOverride.departure_date == departure_date,
            ).first()
        except Exception:
            override = None

        final_price_per_pax_usd = _calc_final_price(
            base_price_usd,
            Decimal(str(override.override_price_usd)) if override else None,
        )
        total_price_usd = _quantize_money(final_price_per_pax_usd * Decimal(adults))
        total_price_mmk = _quantize_money(total_price_usd * usd_to_mmk)

        final_results.append({
            "bundle_key": bundle.get("bundle_key"),
            "adults": adults,
            "outbound": bundle.get("outbound"),
            "inbound": bundle.get("inbound"),
            "base_price_usd": float(_quantize_money(base_price_usd)),
            "final_price_usd": float(total_price_usd),
            "final_price_mmk": float(total_price_mmk),
            "price_estimate_min_usd": float(_quantize_money(total_price_usd * Decimal("0.9"))),
            "price_estimate_max_usd": float(_quantize_money(total_price_usd * Decimal("1.1"))),
            "price_estimate_min_mmk": float(_quantize_money(total_price_mmk * Decimal("0.9"))),
            "price_estimate_max_mmk": float(_quantize_money(total_price_mmk * Decimal("1.1"))),
            "requires_admin_confirmation": True,
        })

    return final_results


def calculate_booking_totals(db: Session, snapshot: Dict[str, Any], adults: int, booking_type: str) -> Dict[str, Decimal]:
    usd_to_mmk = _get_exchange_rate(db)
    base_price_usd = _to_decimal(snapshot.get("base_price_usd"), field="base_price_usd")

    override = None
    if booking_type == "ONE_WAY":
        departure_time = snapshot.get("departure_time")
        if departure_time:
            try:
                departure_date = datetime.fromisoformat(departure_time).date()
                override = db.query(FlightOverride).filter(
                    FlightOverride.airline_code == snapshot.get("airline_code"),
                    FlightOverride.flight_number == snapshot.get("flight_number"),
                    FlightOverride.departure_date == departure_date,
                ).first()
            except Exception:
                override = None
    else:
        outbound = snapshot.get("outbound") or {}
        departure_time = outbound.get("departure_time")
        if departure_time:
            try:
                departure_date = datetime.fromisoformat(departure_time).date()
                override = db.query(FlightOverride).filter(
                    FlightOverride.airline_code == outbound.get("airline_code"),
                    FlightOverride.flight_number == outbound.get("flight_number"),
                    FlightOverride.departure_date == departure_date,
                ).first()
            except Exception:
                override = None

    final_price_per_pax_usd = _calc_final_price(
        base_price_usd,
        Decimal(str(override.override_price_usd)) if override else None,
    )
    total_price_usd = _quantize_money(final_price_per_pax_usd * Decimal(adults))
    total_price_mmk = _quantize_money(total_price_usd * usd_to_mmk)
    return {
        "base_price_usd": _quantize_money(base_price_usd),
        "final_price_usd": total_price_usd,
        "final_price_mmk": total_price_mmk,
    }
