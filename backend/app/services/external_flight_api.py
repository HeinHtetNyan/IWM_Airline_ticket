from urllib import response
import httpx
from typing import List, Dict
from app.core.config import settings

RAPIDAPI_URL = "https://ago-travel.p.rapidapi.com/flights/search-one-way"
RAPIDAPI_HOST = "ago-travel.p.rapidapi.com"


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

    all_flights: List[Dict] = []

    # Use requested page directly
    params = {
        "origin": user_origin,
        "destination": user_destination,
        "departureDate": departure_date,
        "page": page,
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.get(RAPIDAPI_URL, headers=headers, params=params)

    if response.status_code != 200:
        print("API error:", response.text)
        return []

    data = response.json()
    bundles = data.get("data", {}).get("bundles", [])

    print(f"PAGE {page} → bundles:", len(bundles))

    if not bundles:
        return []

    for bundle in bundles:

        outbound_slice = bundle.get("outboundSlice", {})
        segments = outbound_slice.get("segments", [])

        if not segments:
            continue

        first_segment = segments[0]

        # Extract real origin/destination
        segment_origin = first_segment.get("originAirport")
        segment_destination = first_segment.get("destinationAirport")

        # Strict route filter
        if segment_origin != user_origin:
            continue

        if segment_destination != user_destination:
            continue

        # ITINERARY INFO
        itineraries = bundle.get("itineraries", [])
        if not itineraries:
            continue

        itinerary_info = itineraries[0].get("itineraryInfo", {})

        airline_code = itinerary_info.get("ticketingAirline")

        carrier_content = itinerary_info.get("ticketingCarrierContent", {})
        airline_name = carrier_content.get("carrierName")

        price = (
            itinerary_info
            .get("price", {})
            .get("usd", {})
            .get("display", {})
            .get("averagePerPax", {})
            .get("allInclusive")
        )

        if price is None:
            continue

        # BAGGAGE
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

        baggage_url = (
            itinerary_info
            .get("baggageUrlWithScope", {})
            .get("baggageUrls", [{}])[0]
            .get("url")
        )

        flight = {
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

        all_flights.append(flight)

    print("TOTAL FETCHED:", len(all_flights))
    return all_flights

#for round trip
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

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            "https://ago-travel.p.rapidapi.com/flights/search-roundtrip",
            headers=headers,
            params=params,
        )

    if response.status_code != 200:
        print("API error:", response.text)
        return []

    data = response.json()
    bundles = data.get("data", {}).get("bundles", [])

    results: List[Dict] = []

    for bundle in bundles:

        # OUTBOUND (bundle level)
        outbound_slice = bundle.get("outboundSlice", {})
        outbound_segments = outbound_slice.get("segments", [])

        # INBOUND (inside itineraries)
        itineraries = bundle.get("itineraries", [])
        if not itineraries:
            continue

        itinerary = itineraries[0]
        inbound_slice = itinerary.get("inboundSlice", {})
        inbound_segments = inbound_slice.get("segments", [])

        # PRICE (bundlePrice level)
        bundle_price = bundle.get("bundlePrice", [])
        if not bundle_price:
            continue

        price = (
            bundle_price[0]
            .get("price", {})
            .get("usd", {})
            .get("display", {})
            .get("averagePerPax", {})
            .get("allInclusive")
        )

        if price is None:
            continue

        if not outbound_segments or not inbound_segments:
            continue

        outbound_first = outbound_segments[0]
        outbound_last = outbound_segments[-1]

        inbound_first = inbound_segments[0]
        inbound_last = inbound_segments[-1]

        # STRICT ROUTE FILTER
        if outbound_first.get("originAirport") != user_origin:
            continue

        if outbound_last.get("destinationAirport") != user_destination:
            continue

        if inbound_first.get("originAirport") != user_destination:
            continue

        if inbound_last.get("destinationAirport") != user_origin:
            continue

        # BAGGAGE (Outbound)
        outbound_free_bags = outbound_slice.get("freeBags", [])
        outbound_carry = 0
        outbound_checked = 0

        for bag in outbound_free_bags:
            if bag.get("baggageType") == "CARRY_ON":
                restrictions = bag.get("restrictions", [])
                if restrictions:
                    outbound_carry = restrictions[0].get("value", 0)
            if bag.get("baggageType") == "CHECKED":
                restrictions = bag.get("restrictions", [])
                if restrictions:
                    outbound_checked = restrictions[0].get("value", 0)

        # BAGGAGE (Inbound)
        inbound_free_bags = inbound_slice.get("freeBags", [])
        inbound_carry = 0
        inbound_checked = 0

        for bag in inbound_free_bags:
            if bag.get("baggageType") == "CARRY_ON":
                restrictions = bag.get("restrictions", [])
                if restrictions:
                    inbound_carry = restrictions[0].get("value", 0)
            if bag.get("baggageType") == "CHECKED":
                restrictions = bag.get("restrictions", [])
                if restrictions:
                    inbound_checked = restrictions[0].get("value", 0)

        results.append({
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
            },
        })

    return results
