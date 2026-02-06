from datetime import datetime
from typing import List, Dict
from uuid import uuid4


def _parse_route(route: str) -> tuple[str, str]:
    origin, destination = route.split("→")
    return origin.strip(), destination.strip()


def _to_int(value) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _map_flight(item: Dict, *, price_usd: float, external_flight_id: str) -> Dict:
    origin, destination = _parse_route(item["route"])

    return {
        # internal id
        "id": str(uuid4()),

        # stable identity from external API
        "external_flight_id": external_flight_id,

        # core flight data
        "airline_code": item["airlineCode"],
        "flight_number": item["flightNumber"],
        "origin": origin,
        "destination": destination,
        "departure_time": datetime.fromisoformat(item["departTime"]),
        "arrival_time": datetime.fromisoformat(item["arriveTime"]),

        # pricing
        "base_price_usd": float(price_usd),
    }


def fetch_flights_from_external_api(
    *,
    origin: str,
    destination: str,
    departure_date: str,
) -> List[Dict]:
    """
    Adapter for Agoda VibePro API.
    This function must return normalized flight dictionaries.
    """

    # replace this with the real HTTP API call
    raw_response = get_external_api_response()

    flights: List[Dict] = []

    for item in raw_response:
        # One-way flight
        if "outbound" not in item:
            flights.append(
                _map_flight(
                    item,
                    price_usd=item["priceUSD"],
                    external_flight_id=f'{item["flightNumber"]}-{item["departTime"]}',
                )
            )

        # Round-trip bundle
        else:
            bundle_key = item["bundleKey"]

            flights.append(
                _map_flight(
                    item["outbound"],
                    price_usd=item["priceUSD"],
                    external_flight_id=f"{bundle_key}-OUT",
                )
            )

            flights.append(
                _map_flight(
                    item["inbound"],
                    price_usd=item["priceUSD"],
                    external_flight_id=f"{bundle_key}-IN",
                )
            )

    return flights
