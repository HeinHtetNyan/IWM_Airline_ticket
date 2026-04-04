from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.exchange_rate import ExchangeRate
from backend.app.services.price_override_service import get_active_price_override
from backend.app.services.pricing_config_service import get_global_markup


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


def _get_markup_price(base_price_usd: Decimal, markup_percentage: Decimal) -> Decimal:
    # VERIFIED: markup applied once at pricing calculation
    return _quantize_money(base_price_usd * (Decimal("1") + (markup_percentage / Decimal("100"))))


def _get_override_price(
    db: Session,
    airline_code: str | None,
    flight_number: str | None,
    departure_date: date | None,
) -> Decimal | None:
    override = get_active_price_override(db, airline_code, flight_number, departure_date)
    if override is None:
        return None
    return _quantize_money(Decimal(str(override.override_price_usd)))


def _calc_final_price(
    db: Session,
    base_price_usd: Decimal,
    airline_code: str | None,
    flight_number: str | None,
    departure_date: date | None,
    markup_percentage: Decimal,
) -> Decimal:
    override_price_usd = _get_override_price(db, airline_code, flight_number, departure_date)
    if override_price_usd is not None:
        return override_price_usd
    return _get_markup_price(base_price_usd, markup_percentage)


def _calc_round_trip_final_price(
    base_price_usd: Decimal,
    markup_percentage: Decimal,
) -> Decimal:
    # Round-trip pricing should not reuse one-way price overrides.
    return _get_markup_price(base_price_usd, markup_percentage)


def _extract_departure_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _resolve_flight_override_keys(flight: dict[str, Any]) -> tuple[str | None, str | None, date | None]:
    departure_time = _extract_departure_date(flight.get("departure_time"))
    if departure_time is None:
        return None, None, None
    return flight.get("airline_code"), flight.get("flight_number"), departure_time.date()


def apply_pricing_logic(db: Session, api_flights: list[dict[str, Any]], adults: int = 1) -> list[dict[str, Any]]:
    usd_to_mmk = _get_exchange_rate(db)
    markup_percentage = get_global_markup(db)
    final_flights: list[dict[str, Any]] = []

    for flight in api_flights:
        try:
            base_price_usd = Decimal(str(flight["base_price_usd"]))
        except (KeyError, InvalidOperation, TypeError, ValueError):
            continue

        airline_code, flight_number, departure_date = _resolve_flight_override_keys(flight)

        final_price_per_pax_usd = _calc_final_price(
            db,
            base_price_usd,
            airline_code,
            flight_number,
            departure_date,
            markup_percentage,
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


def apply_round_trip_pricing_logic(db: Session, bundles: list[dict[str, Any]], adults: int = 1) -> list[dict[str, Any]]:
    usd_to_mmk = _get_exchange_rate(db)
    markup_percentage = get_global_markup(db)
    final_results: list[dict[str, Any]] = []

    for bundle in bundles:
        try:
            base_price_usd = Decimal(str(bundle["base_price_usd"]))
        except (KeyError, InvalidOperation, TypeError, ValueError):
            continue

        final_price_per_pax_usd = _calc_round_trip_final_price(
            base_price_usd,
            markup_percentage,
        )
        total_price_usd = _quantize_money(final_price_per_pax_usd * Decimal(adults))
        total_price_mmk = _quantize_money(total_price_usd * usd_to_mmk)

        final_results.append(
            {
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
            }
        )

    return final_results


def calculate_booking_totals(
    db: Session,
    snapshot: dict[str, Any],
    adults: int,
    booking_type: str,
) -> dict[str, Decimal]:
    usd_to_mmk = _get_exchange_rate(db)
    markup_percentage = get_global_markup(db)
    base_price_usd = _to_decimal(snapshot.get("base_price_usd"), field="base_price_usd")

    if booking_type == "ONE_WAY":
        departure_time = _extract_departure_date(snapshot.get("departure_time"))
        airline_code = snapshot.get("airline_code")
        flight_number = snapshot.get("flight_number")
        final_price_per_pax_usd = _calc_final_price(
            db,
            base_price_usd,
            airline_code,
            flight_number,
            departure_time.date() if departure_time else None,
            markup_percentage,
        )
    else:
        final_price_per_pax_usd = _calc_round_trip_final_price(
            base_price_usd,
            markup_percentage,
        )
    total_price_usd = _quantize_money(final_price_per_pax_usd * Decimal(adults))
    total_price_mmk = _quantize_money(total_price_usd * usd_to_mmk)
    return {
        "base_price_usd": _quantize_money(base_price_usd),
        "final_price_usd": total_price_usd,
        "final_price_mmk": total_price_mmk,
    }
