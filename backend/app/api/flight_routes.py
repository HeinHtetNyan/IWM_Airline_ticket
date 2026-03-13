from collections import defaultdict, deque
import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from threading import Lock
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from backend.app.db.deps import get_db
from backend.app.core.redis import redis_client
from backend.app.core.config import settings
from backend.app.services.external_flight_api import (
    fetch_flights_from_external_api,
    fetch_round_trip_from_external_api,
)
from backend.app.services.pricing_engine import (
    apply_pricing_logic,
    apply_round_trip_pricing_logic,
)

router = APIRouter(prefix="/flights", tags=["flights"])
logger = logging.getLogger(__name__)

_RATE_LIMIT_REQUESTS = 30 # max 30 search requests per minute per IP
_RATE_LIMIT_SECONDS = 60 # 60 seconds window for rate limiting
_MAX_TRACKED_IPS = 10_000 # To prevent unbounded memory growth

_rate_limit_lock = Lock()
_request_history: dict[str, deque[datetime]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    client = request.client.host if request.client else "unknown"
    return client


def _enforce_search_rate_limit(request: Request) -> None:
    key = _client_key(request)
    now = datetime.now(timezone.utc)

    with _rate_limit_lock:
        if len(_request_history) >= _MAX_TRACKED_IPS and key not in _request_history:
            oldest_key = next(iter(_request_history))
            del _request_history[oldest_key]

        history = _request_history[key]

        while history and (now - history[0]).total_seconds() > _RATE_LIMIT_SECONDS:
            history.popleft()

        if len(history) >= _RATE_LIMIT_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail="Too many search requests. Please try again shortly.",
            )

        history.append(now)


def _parse_date(value: str, field_name: str, request: Request) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field_name} must be YYYY-MM-DD")

    tz_name = request.headers.get("X-Timezone", "UTC")
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid X-Timezone header")

    today = datetime.now(tz).date()
    if parsed < today:
        raise HTTPException(status_code=400, detail=f"{field_name} cannot be in the past")

    return parsed


@router.get("/search")
def search_flights(
    request: Request,
    origin: str,
    destination: str,
    departure_date: str,
    page: int = Query(1, ge=1, le=100),
    adults: int = Query(1, ge=1, le=50),
    db: Session = Depends(get_db),
):
    _enforce_search_rate_limit(request)
    _parse_date(departure_date, "departure_date", request)

    cache_key = f"flight:{origin}:{destination}:{departure_date}:{page}:{adults}"

    try:
        cached = redis_client.get(cache_key)
    except Exception:
        logger.exception("Redis cache read failure")
        cached = None

    if cached:
        if isinstance(cached, bytes):
            cached = cached.decode()
        api_flights = json.loads(cached)
    else:
        api_flights = fetch_flights_from_external_api(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            page=page,
        )

        try:
            redis_client.set(cache_key, json.dumps(api_flights), ex=settings.FLIGHT_CACHE_TTL)
        except Exception:
            logger.exception("Redis cache write failure")

    return apply_pricing_logic(db, api_flights, adults)


@router.get("/search-round-trip")
def search_round_trip(
    request: Request,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    page: int = Query(1, ge=1, le=100),
    adults: int = Query(1, ge=1, le=50),
    db: Session = Depends(get_db),
):
    _enforce_search_rate_limit(request)

    dep = _parse_date(departure_date, "departure_date", request)
    ret = _parse_date(return_date, "return_date", request)

    if ret < dep:
        raise HTTPException(
            status_code=400,
            detail="return_date must be on/after departure_date",
        )

    cache_key = f"roundtrip:{origin}:{destination}:{departure_date}:{return_date}:{page}"

    try:
        cached = redis_client.get(cache_key)
    except Exception:
        logger.exception("Redis cache read failure")
        cached = None

    if cached:
        if isinstance(cached, bytes):
            cached = cached.decode()
        bundles = json.loads(cached)
    else:
        bundles = fetch_round_trip_from_external_api(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            page=page,
        )

        try:
            redis_client.set(cache_key, json.dumps(bundles), ex=settings.FLIGHT_CACHE_TTL) # redis 15 minutes cache 
        except Exception:
            logger.exception("Redis cache write failure")

    return apply_round_trip_pricing_logic(db, bundles, adults)