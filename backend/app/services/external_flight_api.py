import logging
from typing import Dict, List

import httpx
from fastapi import HTTPException

from app.core.config import settings

RAPIDAPI_URL = "https://ago-travel.p.rapidapi.com/flights/search-one-way"
RAPIDAPI_ROUND_TRIP_URL = "https://ago-travel.p.rapidapi.com/flights/search-roundtrip"
RAPIDAPI_HOST = "ago-travel.p.rapidapi.com"

logger = logging.getLogger(__name__)


def _request_json(url: str, headers: Dict[str, str], params: Dict[str, object]) -> Dict:
    attempts = 3
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url, headers=headers, params=params)

            if resp.status_code != 200:
                logger.warning("External API status=%s attempt=%s body=%s", resp.status_code, attempt, resp.text)
                continue

            return resp.json()
        except Exception as exc:
            last_error = exc
            logger.warning("External API request failed attempt=%s error=%s", attempt, exc)

    raise HTTPException(status_code=502, detail="External flight API request failed") from last_error


def fetch_flights_from_external_api(
    *,
    origin: str,
    destination: str,
    departure_date: str,
    page: int = 1,
) -> List[Dict]:
    headers = {
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": settings.TICKET_API_KEY,
    }

    user_origin = origin.upper()
    user_destination = destination.upper()

    params = {
        "origin": user_origin,
        "destination": user_destination,
        "departureDate": departure_date,
        "page": page,
    }

    data = _request_json(RAPIDAPI_URL, headers, params)
    bundles = data.get("data", {}).get("bundles", [])
    all_flights: List[Dict] = []

    for bundle in bundles:
        outbound_slice = bundle.get("outboundSlice", {})
        segments = outbound_slice.get("segments", [])

        if not segments:
            continue

        first_segment = segments[0]
        segment_origin = first_segment.get("originAirport")
        segment_destination = first_segment.get("destinationAirport")

        if segment_origin != user_origin or segment_destination != user_destination:
            continue

        itineraries = bundle.get("itineraries", [])
        if not itineraries:
            continue

        itinerary_info = itineraries[0].get("itineraryInfo", {})
        airline_code = itinerary_info.get("ticketingAirline")
        carrier_content = itinerary_info.get("ticketingCarrierContent", {})
        airline_name = carrier_content.get("carrierName")

        price = (
            itinerary_info.get("price", {})
            .get("usd", {})
            .get("display", {})
            .get("averagePerPax", {})
            .get("allInclusive")
        )

        if price is None:
            continue

        free_bags = outbound_slice.get("freeBags", [])
        carry_on_kg = 0
        checked_kg = 0

        for bag in free_bags:
            baggage_type = bag.get("baggageType")
            restrictions = bag.get("restrictions", [])
            if restrictions and isinstance(restrictions, list):
                value = restrictions[0].get("value")
                if baggage_type == "CARRY_ON" and value:
                    carry_on_kg = value
                if baggage_type == "CHECKED" and value:
                    checked_kg = value

        baggage_fee = first_segment.get("baggageFee")
        baggage_url = itinerary_info.get("baggageUrlWithScope", {}).get("baggageUrls", [{}])[0].get("url")

        all_flights.append(
            {
                "external_flight_id": itinerary_info.get("externalItineraryId"),
                "airline": airline_name,
                "airline_code": airline_code,
                "flight_number": first_segment.get("flightNumber"),
                "origin": segment_origin,
                "destination": segment_destination,
                "route": f"{segment_origin} → {segment_destination}",
                "departure_time": first_segment.get("departDateTime"),
                "arrival_time": first_segment.get("arrivalDateTime"),
                "duration_minutes": first_segment.get("duration"),
                "baggage_carry_on_kg": carry_on_kg,
                "baggage_checked_kg": checked_kg,
                "baggage_fee": baggage_fee,
                "baggage_info_url": baggage_url,
                "base_price_usd": float(price),
            }
        )

    return all_flights


def fetch_round_trip_from_external_api(
    *,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    page: int = 1,
) -> List[Dict]:
    headers = {
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": settings.TICKET_API_KEY,
    }

    user_origin = origin.upper()
    user_destination = destination.upper()

    params = {
        "origin": user_origin,
        "destination": user_destination,
        "departureDate": departure_date,
        "returnDate": return_date,
        "page": page,
    }

    data = _request_json(RAPIDAPI_ROUND_TRIP_URL, headers, params)
    bundles = data.get("data", {}).get("bundles", [])

    results: List[Dict] = []

    for bundle in bundles:
        outbound_slice = bundle.get("outboundSlice", {})
        outbound_segments = outbound_slice.get("segments", [])

        itineraries = bundle.get("itineraries", [])
        if not itineraries:
            continue

        itinerary = itineraries[0]
        inbound_slice = itinerary.get("inboundSlice", {})
        inbound_segments = inbound_slice.get("segments", [])

        bundle_price = bundle.get("bundlePrice", [])
        if not bundle_price:
            continue

        price = (
            bundle_price[0].get("price", {})
            .get("usd", {})
            .get("display", {})
            .get("averagePerPax", {})
            .get("allInclusive")
        )

        if price is None or not outbound_segments or not inbound_segments:
            continue

        outbound_first = outbound_segments[0]
        outbound_last = outbound_segments[-1]
        inbound_first = inbound_segments[0]
        inbound_last = inbound_segments[-1]

        if (
            outbound_first.get("originAirport") != user_origin
            or outbound_last.get("destinationAirport") != user_destination
            or inbound_first.get("originAirport") != user_destination
            or inbound_last.get("destinationAirport") != user_origin
        ):
            continue

        def _extract_baggage(slice_data: Dict) -> tuple[int, int]:
            carry, checked = 0, 0
            for bag in slice_data.get("freeBags", []):
                restrictions = bag.get("restrictions", [])
                value = restrictions[0].get("value", 0) if restrictions else 0
                if bag.get("baggageType") == "CARRY_ON":
                    carry = value
                if bag.get("baggageType") == "CHECKED":
                    checked = value
            return carry, checked

        outbound_carry, outbound_checked = _extract_baggage(outbound_slice)
        inbound_carry, inbound_checked = _extract_baggage(inbound_slice)

        results.append(
            {
                "bundle_key": bundle.get("key"),
                "base_price_usd": float(price),
                "outbound": {
                    "airline": outbound_first.get("carrierContent", {}).get("carrierName"),
                    "airline_code": outbound_first.get("carrierContent", {}).get("carrierCode"),
                    "flight_number": outbound_first.get("flightNumber"),
                    "origin": outbound_first.get("originAirport"),
                    "destination": outbound_last.get("destinationAirport"),
                    "route": f"{outbound_first.get('originAirport')} → {outbound_last.get('destinationAirport')}",
                    "departure_time": outbound_first.get("departDateTime"),
                    "arrival_time": outbound_last.get("arrivalDateTime"),
                    "duration_minutes": outbound_slice.get("duration"),
                    "baggage_carry_on_kg": outbound_carry,
                    "baggage_checked_kg": outbound_checked,
                    "base_price_usd": float(price) / 2,
                },
                "inbound": {
                    "airline": inbound_first.get("carrierContent", {}).get("carrierName"),
                    "airline_code": inbound_first.get("carrierContent", {}).get("carrierCode"),
                    "flight_number": inbound_first.get("flightNumber"),
                    "origin": inbound_first.get("originAirport"),
                    "destination": inbound_last.get("destinationAirport"),
                    "route": f"{inbound_first.get('originAirport')} → {inbound_last.get('destinationAirport')}",
                    "departure_time": inbound_first.get("departDateTime"),
                    "arrival_time": inbound_last.get("arrivalDateTime"),
                    "duration_minutes": inbound_slice.get("duration"),
                    "baggage_carry_on_kg": inbound_carry,
                    "baggage_checked_kg": inbound_checked,
                    "base_price_usd": float(price) / 2,
                },
            }
        )

    return results
