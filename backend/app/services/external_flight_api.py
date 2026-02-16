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
) -> List[Dict]:

    headers = {
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": settings.TICKET_API_KEY,
    }

    all_flights: List[Dict] = []
    page = 1

    while True:

        params = {
            "origin": origin.upper(),
            "destination": destination.upper(),
            "departureDate": departure_date,
            "page": page,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.get(RAPIDAPI_URL, headers=headers, params=params)

        if response.status_code != 200:
            print("❌ API error:", response.text)
            break

        data = response.json()
        bundles = data.get("data", {}).get("bundles", [])

        print(f"PAGE {page} → bundles:", len(bundles))

        if not bundles:
            break

        for bundle in bundles:

            # SEGMENT
            outbound_slice = bundle.get("outboundSlice", {})
            segments = outbound_slice.get("segments", [])

            if not segments:
                continue

            first_segment = segments[0]

            # ITINERARY INFO
            itineraries = bundle.get("itineraries", [])
            if not itineraries:
                continue

            itinerary_info = itineraries[0].get("itineraryInfo", {})

            # AIRLINE
            airline_code = itinerary_info.get("ticketingAirline")

            carrier_content = itinerary_info.get("ticketingCarrierContent", {})
            airline_name = carrier_content.get("carrierName")

            # PRICE (FIXED PATH)
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

            # BAGGAGE (FINAL FIXED VERSION)

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

            # BUILD FLIGHT
            flight = {
                "external_flight_id": itinerary_info.get("externalItineraryId"),
                "airline": airline_name,
                "airline_code": airline_code,
                "flight_number": first_segment.get("flightNumber"),

                "origin": origin.upper(),
                "destination": destination.upper(),
                "route": f"{origin.upper()} → {destination.upper()}",

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

        page += 1
        break  # only first page for now becoz i am not sure how to call other pages ;)

    print("TOTAL FETCHED:", len(all_flights))
    return all_flights
