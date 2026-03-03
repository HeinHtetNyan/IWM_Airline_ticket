import logging
from typing import Dict, List

import httpx

from app.core.config import settings

RAPIDAPI_URL = "https://ago-travel.p.rapidapi.com/flights/search-one-way"
ROUND_TRIP_URL = "https://ago-travel.p.rapidapi.com/flights/search-roundtrip"
RAPIDAPI_HOST = "ago-travel.p.rapidapi.com"
logger = logging.getLogger(__name__)


def _request(url: str, headers: dict, params: dict) -> dict:
    last_error = None
    for _ in range(3):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
    logger.error("External flight API failed", exc_info=last_error)
    raise RuntimeError("External flight API unavailable")


def fetch_flights_from_external_api(*, origin: str, destination: str, departure_date: str, page: int = 1) -> List[Dict]:
    headers = {"x-rapidapi-host": RAPIDAPI_HOST, "x-rapidapi-key": settings.TICKET_API_KEY}
    user_origin = origin.upper()
    user_destination = destination.upper()
    params = {"origin": user_origin, "destination": user_destination, "departureDate": departure_date, "page": page}

    data = _request(RAPIDAPI_URL, headers, params)
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
        price = itinerary_info.get("price", {}).get("usd", {}).get("display", {}).get("averagePerPax", {}).get("allInclusive")
        if price is None:
            continue

        all_flights.append(
            {
                "external_flight_id": itinerary_info.get("externalItineraryId"),
                "airline": itinerary_info.get("ticketingCarrierContent", {}).get("carrierName"),
                "airline_code": itinerary_info.get("ticketingAirline"),
                "flight_number": first_segment.get("flightNumber"),
                "origin": segment_origin,
                "destination": segment_destination,
                "route": f"{segment_origin} → {segment_destination}",
                "departure_time": first_segment.get("departDateTime"),
                "arrival_time": first_segment.get("arrivalDateTime"),
                "duration_minutes": first_segment.get("duration"),
                "baggage_carry_on_kg": 0,
                "baggage_checked_kg": 0,
                "baggage_fee": first_segment.get("baggageFee"),
                "baggage_info_url": itinerary_info.get("baggageUrlWithScope", {}).get("baggageUrls", [{}])[0].get("url"),
                "base_price_usd": float(price),
            }
        )

    return all_flights


def fetch_round_trip_from_external_api(*, origin: str, destination: str, departure_date: str, return_date: str, page: int = 1) -> List[Dict]:
    headers = {"x-rapidapi-host": RAPIDAPI_HOST, "x-rapidapi-key": settings.TICKET_API_KEY}
    user_origin = origin.upper()
    user_destination = destination.upper()
    params = {
        "origin": user_origin,
        "destination": user_destination,
        "departureDate": departure_date,
        "returnDate": return_date,
        "page": page,
    }

    data = _request(ROUND_TRIP_URL, headers, params)
    bundles = data.get("data", {}).get("bundles", [])
    results: List[Dict] = []

    for bundle in bundles:
        outbound_segments = bundle.get("outboundSlice", {}).get("segments", [])
        itineraries = bundle.get("itineraries", [])
        if not itineraries:
            continue
        inbound_segments = itineraries[0].get("inboundSlice", {}).get("segments", [])
        bundle_price = bundle.get("bundlePrice", [])
        if not outbound_segments or not inbound_segments or not bundle_price:
            continue

        price = bundle_price[0].get("price", {}).get("usd", {}).get("display", {}).get("averagePerPax", {}).get("allInclusive")
        if price is None:
            continue

        out_first, out_last = outbound_segments[0], outbound_segments[-1]
        in_first, in_last = inbound_segments[0], inbound_segments[-1]
        if out_first.get("originAirport") != user_origin or out_last.get("destinationAirport") != user_destination:
            continue
        if in_first.get("originAirport") != user_destination or in_last.get("destinationAirport") != user_origin:
            continue

        results.append(
            {
                "bundle_key": bundle.get("key"),
                "base_price_usd": float(price),
                "outbound": {
                    "airline": out_first.get("carrierContent", {}).get("carrierName"),
                    "airline_code": out_first.get("carrierContent", {}).get("carrierCode"),
                    "flight_number": out_first.get("flightNumber"),
                    "origin": out_first.get("originAirport"),
                    "destination": out_last.get("destinationAirport"),
                    "route": f"{out_first.get('originAirport')} → {out_last.get('destinationAirport')}",
                    "departure_time": out_first.get("departDateTime"),
                    "arrival_time": out_last.get("arrivalDateTime"),
                    "duration_minutes": bundle.get("outboundSlice", {}).get("duration"),
                },
                "inbound": {
                    "airline": in_first.get("carrierContent", {}).get("carrierName"),
                    "airline_code": in_first.get("carrierContent", {}).get("carrierCode"),
                    "flight_number": in_first.get("flightNumber"),
                    "origin": in_first.get("originAirport"),
                    "destination": in_last.get("destinationAirport"),
                    "route": f"{in_first.get('originAirport')} → {in_last.get('destinationAirport')}",
                    "departure_time": in_first.get("departDateTime"),
                    "arrival_time": in_last.get("arrivalDateTime"),
                    "duration_minutes": itineraries[0].get("inboundSlice", {}).get("duration"),
                },
            }
        )

    return results
