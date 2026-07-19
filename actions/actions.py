from datetime import datetime, date, timedelta
from difflib import get_close_matches
from typing import Any, Dict, List, Text
from concurrent.futures import ThreadPoolExecutor

import dateparser
import math
import os
import re
import requests
import unicodedata

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FollowupAction


API_TIMEOUT_SECONDS = 0.8

CLIMATIQ_BASE_URL = "https://api.climatiq.io"
CLIMATIQ_ESTIMATE_URL = f"{CLIMATIQ_BASE_URL}/data/v1/estimate"
OPENCAGE_GEOCODE_URL = "https://api.opencagedata.com/geocode/v1/json"
OPENCAGE_TIMEOUT_SECONDS = 2
OPENCAGE_CACHE = {}

OSRM_ROUTE_BASE_URL = (
    "https://router.project-osrm.org/route/v1/driving"
)
OSRM_TIMEOUT_SECONDS = 2
OSRM_ROUTE_CACHE = {}

# Transparent prototype assumptions for a typical petrol car.
DEFAULT_CAR_FUEL_L_PER_100_KM = 6.5
DEFAULT_FUEL_PRICE_EUR_PER_L = 1.80

# OSRM can expose ferry sections through route steps.  The explicit
# Mallorca corridor below also keeps the prototype useful if the public
# router cannot return a connected island route at runtime.
KNOWN_FERRY_CORRIDORS = {
    "mallorca": {
        "mainland_port": "Barcelona Ferry Port",
        "mainland_port_coords": (41.3525, 2.1587),
        "island_port": "Palma de Mallorca Port",
        "island_port_coords": (39.5528, 2.6267),
        "ferry_distance_km": 205.0,
        "ferry_duration_minutes": 450,
        "route_name": "Barcelona to Palma de Mallorca",
    },
    "palma de mallorca": {
        "mainland_port": "Barcelona Ferry Port",
        "mainland_port_coords": (41.3525, 2.1587),
        "island_port": "Palma de Mallorca Port",
        "island_port_coords": (39.5528, 2.6267),
        "ferry_distance_km": 205.0,
        "ferry_duration_minutes": 450,
        "route_name": "Barcelona to Palma de Mallorca",
    },
}


CITY_ALIASES = {
    "istanbul": "Istanbul",
    "paris": "Paris",
    "amsterdam": "Amsterdam",
    "berlin": "Berlin",
    "barcelona": "Barcelona",
    "rome": "Rome",
    "roma": "Rome",
    "copenhagen": "Copenhagen",
    "vienna": "Vienna",
    "wien": "Vienna",
    "zurich": "Zurich",
    "prague": "Prague",
    "praha": "Prague",
    "lisbon": "Lisbon",
    "madrid": "Madrid",
    "milan": "Milan",
    "brussels": "Brussels",
    "dublin": "Dublin",
    "oslo": "Oslo",
    "stockholm": "Stockholm",
    "helsinki": "Helsinki",
    "athens": "Athens",
    "warsaw": "Warsaw",
    "budapest": "Budapest",
    "london": "London",
    "ankara": "Ankara",
    "izmir": "İzmir",
    "cesme": "Çeşme",
    "munich": "München",
    "munchen": "München",
    "koln": "Köln",
    "cologne": "Köln",
    "mallorca": "Mallorca",
    "majorca": "Mallorca",
    "palma": "Palma de Mallorca",
    "palma de mallorca": "Palma de Mallorca",
}


CITY_COORDS = {
    "Istanbul": (41.0082, 28.9784),
    "Paris": (48.8566, 2.3522),
    "Amsterdam": (52.3676, 4.9041),
    "Berlin": (52.5200, 13.4050),
    "Barcelona": (41.3874, 2.1686),
    "Rome": (41.9028, 12.4964),
    "Copenhagen": (55.6761, 12.5683),
    "Vienna": (48.2082, 16.3738),
    "Zurich": (47.3769, 8.5417),
    "Prague": (50.0755, 14.4378),
    "Lisbon": (38.7223, -9.1393),
    "Madrid": (40.4168, -3.7038),
    "Milan": (45.4642, 9.1900),
    "Brussels": (50.8503, 4.3517),
    "Dublin": (53.3498, -6.2603),
    "Oslo": (59.9139, 10.7522),
    "Stockholm": (59.3293, 18.0686),
    "Helsinki": (60.1699, 24.9384),
    "Athens": (37.9838, 23.7275),
    "Warsaw": (52.2297, 21.0122),
    "Budapest": (47.4979, 19.0402),
    "London": (51.5074, -0.1278),
    "Ankara": (39.9334, 32.8597),
    "İzmir": (38.4237, 27.1428),
    "Çeşme": (38.3236, 26.3028),
    "München": (48.1351, 11.5820),
    "Köln": (50.9375, 6.9603),
    "Mallorca": (39.6953, 3.0176),
    "Palma de Mallorca": (39.5696, 2.6502),
}


CARBON_FACTORS_KG_PER_KM = {
    "Train": 0.035,
    "Bus": 0.055,
    "Car": 0.180,
    "Flight": 0.255,
}


MODE_PRICE_RULES = {
    "Train": {"base": 24, "per_km": 0.095},
    "Bus": {"base": 14, "per_km": 0.045},
    "Car": {"base": 35, "per_km": 0.135},
    "Flight": {"base": 70, "per_km": 0.115},
}


HOTEL_DATABASE = {
    "Paris": [
        {
            "name": "GreenLeaf Eco Hotel",
            "price": 110,
            "features": "renewable energy, low-waste breakfast, linen reuse programme",
            "source": "prototype eco-certified accommodation dataset",
        },
        {
            "name": "Canal Low Impact Stay",
            "price": 92,
            "features": "public transport access, refill stations, local suppliers",
            "source": "prototype eco-certified accommodation dataset",
        },
    ],
    "Amsterdam": [
        {
            "name": "Canal Side Sustainable Stay",
            "price": 95,
            "features": "bike rental, solar heating, local food suppliers",
            "source": "prototype eco-certified accommodation dataset",
        },
        {
            "name": "North Dock Eco Rooms",
            "price": 88,
            "features": "waste sorting, low-flow water systems, tram access",
            "source": "prototype eco-certified accommodation dataset",
        },
    ],
    "Berlin": [
        {
            "name": "Urban Green Berlin Hotel",
            "price": 89,
            "features": "energy-efficient rooms, vegan breakfast options, U-Bahn access",
            "source": "prototype eco-certified accommodation dataset",
        },
    ],
    "Barcelona": [
        {
            "name": "Solar Stay Barcelona",
            "price": 104,
            "features": "solar energy, refill water points, local employment policy",
            "source": "prototype eco-certified accommodation dataset",
        },
    ],
    "Rome": [
        {
            "name": "Mediterranean Responsible Inn",
            "price": 100,
            "features": "organic restaurant, energy-efficient lighting, community tours",
            "source": "prototype eco-certified accommodation dataset",
        },
    ],
    "default": [
        {
            "name": "Responsible City Stay",
            "price": 98,
            "features": "public transport access, waste reduction policy, local sourcing",
            "source": "prototype eco-certified accommodation dataset",
        },
    ],
}


CULTURAL_EXPERIENCES = {
    "Paris": [
        "community-led walking tour",
        "local food market visit",
        "repair cafe workshop",
    ],
    "Amsterdam": [
        "bike-based canal tour",
        "local craft market",
        "urban farming visit",
    ],
    "Berlin": [
        "public-transit street art route",
        "independent museum evening",
        "community food project visit",
    ],
    "Barcelona": [
        "neighbourhood tapas walk with local hosts",
        "low-impact coastal clean-up activity",
        "artisan market visit",
    ],
    "Rome": [
        "heritage walking route",
        "local cooking class",
        "artisan neighbourhood visit",
    ],
    "default": [
        "community-led walking tour",
        "local market visit",
        "low-impact cultural workshop",
    ],
}


TRIP_TYPE_LABELS = {
    "city_break": "City break",
    "rural_eco_tour": "Rural eco-tour",
    "business_trip": "Business trip",
    "general_trip": "General trip",
}


TRIP_TYPE_ALIASES = {
    "city break": "city_break",
    "short city trip": "city_break",
    "weekend city break": "city_break",
    "rural eco tour": "rural_eco_tour",
    "rural eco-tour": "rural_eco_tour",
    "nature focused trip": "rural_eco_tour",
    "countryside eco tour": "rural_eco_tour",
    "business": "business_trip",
    "business trip": "business_trip",
    "work trip": "business_trip",
    "general": "general_trip",
    "general trip": "general_trip",
    "general leisure trip": "general_trip",
    "regular holiday": "general_trip",
}


def normalise_trip_type(value: Any) -> str:
    text = str(value or "").strip().casefold()

    payload_match = re.search(
        r'"trip_type"\s*:\s*"([^"]+)"',
        text,
    )

    if payload_match:
        text = payload_match.group(1)

    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if text in TRIP_TYPE_ALIASES:
        return TRIP_TYPE_ALIASES[text]

    if "business" in text or "work" in text:
        return "business_trip"

    if "rural" in text or "countryside" in text or "nature" in text:
        return "rural_eco_tour"

    if "city" in text or "weekend" in text:
        return "city_break"

    if "general" in text or "holiday" in text:
        return "general_trip"

    return ""


def trip_type_label(value: Any) -> str:
    normalised_value = normalise_trip_type(value)

    return TRIP_TYPE_LABELS.get(
        normalised_value,
        "General trip",
    )


TRIP_TYPE_ACTIVITY = {
    "city_break": "compact walking and public-transport city itinerary",
    "rural_eco_tour": "regional nature excursion using shared transport",
    "business_trip": "public-transport route to the main business district",
    "general_trip": "flexible community-supported local experience",
}


def extract_city_text(value: Any) -> str:
    text = str(value or "").strip()

    payload_match = re.search(
        r'"(?:origin|destination)"\s*:\s*"([^"]+)"',
        text,
    )

    if payload_match:
        return payload_match.group(1).strip()

    return text


def city_search_key(value: Any) -> str:
    text = extract_city_text(value).casefold()
    text = text.replace("ı", "i")

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    return "".join(
        character
        for character in text
        if character.isalnum()
    )


def get_city_search_index() -> Dict[str, str]:
    city_index = {}

    for canonical_city in CITY_COORDS:
        key = city_search_key(canonical_city)
        city_index[key] = canonical_city

    for alias, canonical_city in CITY_ALIASES.items():
        key = city_search_key(alias)
        city_index[key] = canonical_city

    return city_index

def geocode_city_with_opencage(value: Any):
    api_key = os.getenv("OPENCAGE_API_KEY")
    query = extract_city_text(value).strip()

    if not api_key or not query:
        return None, None

    cache_key = city_search_key(query)

    if len(cache_key) < 4:
        return None, None

    if cache_key in OPENCAGE_CACHE:
        return OPENCAGE_CACHE[cache_key]

    try:
        response = requests.get(
            OPENCAGE_GEOCODE_URL,
            params={
                "q": query,
                "key": api_key,
                "limit": 1,
                "no_annotations": 1,
                "no_record": 1,
                "language": "en",
            },
            timeout=OPENCAGE_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:
            OPENCAGE_CACHE[cache_key] = (None, None)
            return None, None

        data = response.json()
        results = data.get("results", [])

        if not results:
            OPENCAGE_CACHE[cache_key] = (None, None)
            return None, None

        first_result = results[0]
        geometry = first_result.get("geometry", {})
        components = first_result.get("components", {})

        city_name = (
            components.get("city")
            or components.get("town")
            or components.get("village")
            or components.get("municipality")
            or components.get("county")
            or query.title()
        )

        city_name = normalise_city_name_only(city_name)

        lat = geometry.get("lat")
        lng = geometry.get("lng")

        if lat is None or lng is None:
            OPENCAGE_CACHE[cache_key] = (None, None)
            return None, None

        CITY_COORDS[city_name] = (float(lat), float(lng))
        CITY_ALIASES[city_search_key(query)] = city_name

        result = (city_name, None)
        OPENCAGE_CACHE[cache_key] = result

        return result

    except Exception:
        OPENCAGE_CACHE[cache_key] = (None, None)
        return None, None


def resolve_city_input(value: Any):
    search_key = city_search_key(value)

    if not search_key:
        return None, None

    city_index = get_city_search_index()

    if search_key in city_index:
        return city_index[search_key], None

    if len(search_key) >= 3:
        matches = get_close_matches(
            search_key,
            list(city_index.keys()),
            n=1,
            cutoff=0.70,
        )

        if matches:
            suggested_city = city_index[matches[0]]
            return None, suggested_city

    resolved_city, suggested_city = geocode_city_with_opencage(value)

    if resolved_city:
        return resolved_city, None

    return None, suggested_city


def normalise_city_name_only(value: Any) -> str:
    text = str(value or "").strip()

    if not text:
        return ""

    search_key = city_search_key(text)

    city_index = get_city_search_index()

    if search_key in city_index:
        return city_index[search_key]

    return text.title()


def normalise_city(value: Any) -> str:
    resolved_city, _ = resolve_city_input(value)

    if resolved_city:
        return resolved_city

    return extract_city_text(value).strip().title()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def haversine_distance_km(origin: str, destination: str) -> float:
    origin_coords = CITY_COORDS.get(origin)
    destination_coords = CITY_COORDS.get(destination)

    if not origin_coords or not destination_coords:
        return 900.0

    lat1, lon1 = origin_coords
    lat2, lon2 = destination_coords

    radius = 6371.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(delta_lambda / 2) ** 2
    )

    return radius * 2 * math.atan2(
        math.sqrt(value),
        math.sqrt(1 - value),
    )


def format_drive_duration(total_minutes: float) -> str:
    rounded_minutes = max(
        int(round(total_minutes)),
        1,
    )
    hours, minutes = divmod(rounded_minutes, 60)

    if hours and minutes:
        return f"{hours} hr {minutes} min"

    if hours:
        return f"{hours} hr"

    return f"{minutes} min"


def split_ferry_route_name(route_name: str):
    clean_name = str(route_name or "").strip()

    for separator in (
        " - ",
        " – ",
        " — ",
        " to ",
        " → ",
    ):
        if separator in clean_name:
            departure, arrival = clean_name.split(
                separator,
                1,
            )
            return departure.strip(), arrival.strip()

    return "", ""


def request_osrm_route(
    origin_coords,
    destination_coords,
):
    if not origin_coords or not destination_coords:
        return None

    origin_lat, origin_lon = origin_coords
    destination_lat, destination_lon = destination_coords

    coordinates = (
        f"{origin_lon},{origin_lat};"
        f"{destination_lon},{destination_lat}"
    )

    try:
        response = requests.get(
            f"{OSRM_ROUTE_BASE_URL}/{coordinates}",
            params={
                "overview": "false",
                "steps": "true",
                "alternatives": "false",
            },
            headers={
                "User-Agent": (
                    "Eco-Travel-Advisor-Portfolio/1.0"
                ),
            },
            timeout=OSRM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        data = response.json()
        routes = data.get("routes", [])

        if data.get("code") != "Ok" or not routes:
            return None

        route = routes[0]
        route_steps = []

        for leg in route.get("legs", []):
            route_steps.extend(leg.get("steps", []))

        ferry_steps = []

        for step in route_steps:
            step_mode = str(
                step.get("mode", "")
            ).strip().casefold()
            step_name = str(
                step.get("name", "")
            ).strip()

            if (
                step_mode == "ferry"
                or "ferry" in step_mode
                or "ferry" in step_name.casefold()
            ):
                ferry_steps.append(step)

        total_distance_km = (
            float(route.get("distance", 0)) / 1000.0
        )
        total_duration_minutes = (
            float(route.get("duration", 0)) / 60.0
        )
        ferry_distance_km = sum(
            float(step.get("distance", 0))
            for step in ferry_steps
        ) / 1000.0
        ferry_duration_minutes = sum(
            float(step.get("duration", 0))
            for step in ferry_steps
        ) / 60.0

        ferry_names = []

        for step in ferry_steps:
            ferry_name = str(step.get("name", "")).strip()

            if ferry_name and ferry_name not in ferry_names:
                ferry_names.append(ferry_name)

        ferry_route_name = (
            " / ".join(ferry_names)
            if ferry_names
            else "Vehicle ferry segment"
        )
        ferry_departure_port, ferry_arrival_port = (
            split_ferry_route_name(ferry_names[0])
            if ferry_names
            else ("", "")
        )

        return {
            "total_distance_km": total_distance_km,
            "total_duration_minutes": total_duration_minutes,
            "road_distance_km": max(
                total_distance_km - ferry_distance_km,
                0.0,
            ),
            "road_duration_minutes": max(
                total_duration_minutes - ferry_duration_minutes,
                0.0,
            ),
            "ferry_distance_km": ferry_distance_km,
            "ferry_duration_minutes": ferry_duration_minutes,
            "has_ferry": bool(ferry_steps),
            "ferry_route_name": ferry_route_name,
            "ferry_departure_port": ferry_departure_port,
            "ferry_arrival_port": ferry_arrival_port,
        }

    except (
        requests.exceptions.RequestException,
        KeyError,
        TypeError,
        ValueError,
    ):
        return None


def fallback_route_between_coords(
    origin_coords,
    destination_coords,
):
    if not origin_coords or not destination_coords:
        return {
            "distance_km": 0.0,
            "duration_minutes": 0.0,
        }

    origin_lat, origin_lon = origin_coords
    destination_lat, destination_lon = destination_coords
    radius = 6371.0
    phi1 = math.radians(origin_lat)
    phi2 = math.radians(destination_lat)
    delta_phi = math.radians(destination_lat - origin_lat)
    delta_lambda = math.radians(destination_lon - origin_lon)
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(delta_lambda / 2) ** 2
    )
    direct_distance_km = radius * 2 * math.atan2(
        math.sqrt(value),
        math.sqrt(1 - value),
    )
    road_distance_km = direct_distance_km * 1.22

    return {
        "distance_km": road_distance_km,
        "duration_minutes": road_distance_km / 80.0 * 60.0,
    }


def road_section_estimate(
    origin_coords,
    destination_coords,
):
    live_route = request_osrm_route(
        origin_coords,
        destination_coords,
    )

    if live_route:
        return {
            "distance_km": (
                live_route["road_distance_km"]
                + live_route["ferry_distance_km"]
            ),
            "duration_minutes": (
                live_route["road_duration_minutes"]
                + live_route["ferry_duration_minutes"]
            ),
            "live_route": True,
        }

    fallback = fallback_route_between_coords(
        origin_coords,
        destination_coords,
    )
    fallback["live_route"] = False
    return fallback


def known_ferry_route_estimate(
    origin: str,
    destination: str,
):
    origin_key = str(origin).strip().casefold()
    destination_key = str(destination).strip().casefold()
    origin_corridor = KNOWN_FERRY_CORRIDORS.get(origin_key)
    destination_corridor = KNOWN_FERRY_CORRIDORS.get(
        destination_key
    )

    if bool(origin_corridor) == bool(destination_corridor):
        return None

    travelling_to_island = bool(destination_corridor)
    corridor = destination_corridor or origin_corridor
    origin_coords = CITY_COORDS.get(origin)
    destination_coords = CITY_COORDS.get(destination)

    if travelling_to_island:
        mainland_section = road_section_estimate(
            origin_coords,
            corridor["mainland_port_coords"],
        )
        island_section = road_section_estimate(
            corridor["island_port_coords"],
            destination_coords,
        )
        ferry_departure_port = corridor["mainland_port"]
        ferry_arrival_port = corridor["island_port"]
        ferry_route_name = corridor["route_name"]
    else:
        island_section = road_section_estimate(
            origin_coords,
            corridor["island_port_coords"],
        )
        mainland_section = road_section_estimate(
            corridor["mainland_port_coords"],
            destination_coords,
        )
        ferry_departure_port = corridor["island_port"]
        ferry_arrival_port = corridor["mainland_port"]
        route_parts = corridor["route_name"].split(
            " to ",
            1,
        )
        ferry_route_name = (
            f"{route_parts[1]} to {route_parts[0]}"
            if len(route_parts) == 2
            else corridor["route_name"]
        )

    road_distance_km = (
        mainland_section["distance_km"]
        + island_section["distance_km"]
    )
    road_duration_minutes = (
        mainland_section["duration_minutes"]
        + island_section["duration_minutes"]
    )
    ferry_distance_km = corridor["ferry_distance_km"]
    ferry_duration_minutes = corridor[
        "ferry_duration_minutes"
    ]
    all_road_sections_live = (
        mainland_section["live_route"]
        and island_section["live_route"]
    )

    return {
        "total_distance_km": (
            road_distance_km + ferry_distance_km
        ),
        "total_duration_minutes": (
            road_duration_minutes + ferry_duration_minutes
        ),
        "road_distance_km": road_distance_km,
        "road_duration_minutes": road_duration_minutes,
        "ferry_distance_km": ferry_distance_km,
        "ferry_duration_minutes": ferry_duration_minutes,
        "has_ferry": True,
        "ferry_route_name": ferry_route_name,
        "ferry_departure_port": ferry_departure_port,
        "ferry_arrival_port": ferry_arrival_port,
        "live_route": all_road_sections_live,
        "route_source": (
            (
                "OSRM road sections using OpenStreetMap data"
                if all_road_sections_live
                else "Fallback road sections based on direct distance"
            )
            + " and a prototype Mallorca ferry corridor"
        ),
    }


def get_car_route_estimate(
    origin: str,
    destination: str,
) -> Dict[str, Any]:
    cache_key = (
        str(origin).strip().casefold(),
        str(destination).strip().casefold(),
    )

    if cache_key in OSRM_ROUTE_CACHE:
        return dict(OSRM_ROUTE_CACHE[cache_key])

    route_data = known_ferry_route_estimate(
        origin,
        destination,
    )

    if not route_data:
        route_data = request_osrm_route(
            CITY_COORDS.get(origin),
            CITY_COORDS.get(destination),
        )

    if route_data:
        road_distance_km = route_data["road_distance_km"]
        road_duration_minutes = route_data[
            "road_duration_minutes"
        ]
        ferry_distance_km = route_data[
            "ferry_distance_km"
        ]
        ferry_duration_minutes = route_data[
            "ferry_duration_minutes"
        ]
        total_duration_minutes = route_data[
            "total_duration_minutes"
        ]
        route_source = route_data.get(
            "route_source",
            "OSRM route using OpenStreetMap data",
        )
        live_route = route_data.get("live_route", True)
        has_ferry = route_data.get("has_ferry", False)
        ferry_route_name = route_data.get(
            "ferry_route_name",
            "",
        )
        ferry_departure_port = route_data.get(
            "ferry_departure_port",
            "",
        )
        ferry_arrival_port = route_data.get(
            "ferry_arrival_port",
            "",
        )
    else:
        direct_distance_km = haversine_distance_km(
            origin,
            destination,
        )
        road_distance_km = direct_distance_km * 1.22
        road_duration_minutes = (
            road_distance_km / 80.0 * 60.0
        )
        ferry_distance_km = 0.0
        ferry_duration_minutes = 0.0
        total_duration_minutes = road_duration_minutes
        route_source = (
            "Fallback road estimate based on direct distance"
        )
        live_route = False
        has_ferry = False
        ferry_route_name = ""
        ferry_departure_port = ""
        ferry_arrival_port = ""

    fuel_litres = (
        road_distance_km
        * DEFAULT_CAR_FUEL_L_PER_100_KM
        / 100.0
    )
    fuel_cost = (
        fuel_litres
        * DEFAULT_FUEL_PRICE_EUR_PER_L
    )

    result = {
        "road_distance_km": round(road_distance_km, 1),
        "duration_minutes": int(round(road_duration_minutes)),
        "duration_display": format_drive_duration(
            road_duration_minutes
        ),
        "total_duration_minutes": int(
            round(total_duration_minutes)
        ),
        "total_duration_display": format_drive_duration(
            total_duration_minutes
        ),
        "fuel_litres": round(fuel_litres, 1),
        "fuel_cost": round(fuel_cost, 2),
        "fuel_consumption": DEFAULT_CAR_FUEL_L_PER_100_KM,
        "fuel_price": DEFAULT_FUEL_PRICE_EUR_PER_L,
        "toll_note": (
            "Not included; check the live route before travel"
        ),
        "route_source": route_source,
        "live_route": live_route,
        "has_ferry": has_ferry,
        "ferry_route_name": ferry_route_name,
        "ferry_departure_port": ferry_departure_port,
        "ferry_arrival_port": ferry_arrival_port,
        "ferry_distance_km": round(ferry_distance_km, 1),
        "ferry_duration_minutes": int(
            round(ferry_duration_minutes)
        ),
        "ferry_duration_display": (
            format_drive_duration(ferry_duration_minutes)
            if has_ferry
            else ""
        ),
        "ferry_fare_note": (
            "Not included; check a live vehicle fare and schedule"
            if has_ferry
            else "Not applicable"
        ),
        "ferry_emissions_note": (
            "Not included in this prototype estimate"
            if has_ferry
            else "Not applicable"
        ),
    }

    OSRM_ROUTE_CACHE[cache_key] = dict(result)

    return result


def carbon_label(carbon_kg: float, distance_km: float) -> str:
    carbon_intensity = carbon_kg / max(distance_km, 1.0)

    if carbon_intensity <= 0.060:
        return "green"

    if carbon_intensity <= 0.200:
        return "amber"

    return "red"


def calculate_trip_nights(departure_date: Any, return_date: Any) -> int:
    try:
        departure = datetime.strptime(
            str(departure_date),
            "%Y-%m-%d",
        ).date()

        returning = datetime.strptime(
            str(return_date),
            "%Y-%m-%d",
        ).date()

    except (TypeError, ValueError):
        return 1

    return max(
        (returning - departure).days,
        1,
    )


CLIMATIQ_ACTIVITY_IDS = {
    "Train": "passenger_train-route_type_na-fuel_source_na",
    "Bus": "passenger_vehicle-vehicle_type_coach-fuel_source_diesel-engine_size_na-vehicle_age_na-vehicle_weight_na",
    "Car": "passenger_vehicle-vehicle_type_car-fuel_source_na-distance_na-engine_size_na",
}

def climatiq_activity_id_for_mode(
    mode: str,
    distance_km: float,
) -> str:
    if mode != "Flight":
        return CLIMATIQ_ACTIVITY_IDS.get(mode)

    if distance_km < 1000:
        return (
            "passenger_flight-route_type_na-aircraft_type_na-"
            "distance_short_medium_haul_lt_1000km-class_na-"
            "rf_included-distance_uplift_na"
        )

    if distance_km < 4000:
        return (
            "passenger_flight-route_type_na-aircraft_type_na-"
            "distance_short_long_haul_lt_4000km-class_na-"
            "rf_included-distance_uplift_na"
        )

    return (
        "passenger_flight-route_type_na-aircraft_type_na-"
        "distance_long_haul_gt_4000km-class_na-"
        "rf_included-distance_uplift_na"
    )


CLIMATIQ_REASONABLE_KG_PER_KM = {
    "Train": (0.005, 0.090),
    "Bus": (0.015, 0.140),
    "Car": (0.080, 0.300),
    "Flight": (0.100, 0.350),
}


CLIMATIQ_REQUEST_CACHE = {}
CLIMATIQ_DISABLED_BY_MODE = {}


def query_climatiq_transport_estimate(mode: str, distance_km: float):
    api_key = os.getenv("CLIMATIQ_API_KEY")

    if not api_key:
        return (
            None,
            "local prototype factor used because Climatiq API key is not configured",
        )

    if mode in CLIMATIQ_DISABLED_BY_MODE:
        return (
            None,
            (
                "local prototype factor used because Climatiq live estimate "
                f"for {mode.lower()} is unavailable in this session: "
                f"{CLIMATIQ_DISABLED_BY_MODE[mode]}"
            ),
        )

    activity_id = climatiq_activity_id_for_mode(
        mode,
        distance_km,
    )

    if not activity_id:
        return (
            None,
            "local prototype factor used because transport mode is not mapped to Climatiq",
        )

    cache_key = (mode, round(distance_km, 1))

    if cache_key in CLIMATIQ_REQUEST_CACHE:
        return CLIMATIQ_REQUEST_CACHE[cache_key]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "emission_factor": {
            "activity_id": activity_id,
            "data_version": "^34",
        },
        "parameters": {
            "distance": distance_km,
            "distance_unit": "km",
        },
    }

    try:
        response = requests.post(
            CLIMATIQ_ESTIMATE_URL,
            json=payload,
            headers=headers,
            timeout=API_TIMEOUT_SECONDS,
        )

        if response.status_code >= 400:
            reason = f"HTTP {response.status_code}"
            CLIMATIQ_DISABLED_BY_MODE[mode] = reason

            result = (
                None,
                (
                    "local prototype factor used after Climatiq API fallback: "
                    f"{reason}"
                ),
            )

            CLIMATIQ_REQUEST_CACHE[cache_key] = result
            return result

        data = response.json()
        co2e = float(data["co2e"])
        intensity = co2e / max(distance_km, 1)

        min_reasonable, max_reasonable = CLIMATIQ_REASONABLE_KG_PER_KM[mode]

        if not min_reasonable <= intensity <= max_reasonable:
            result = (
                None,
                (
                    "local prototype factor used because Climatiq returned "
                    f"an unrealistic {mode.lower()} intensity"
                ),
            )

            CLIMATIQ_REQUEST_CACHE[cache_key] = result
            return result

        factor_data = data.get("emission_factor", {})

        factor_name = factor_data.get("name") or activity_id
        source_name = factor_data.get("source") or "Climatiq"
        source_year = factor_data.get("year")

        source_text = (
            f"Climatiq API estimate using {factor_name} from {source_name}"
        )

        if source_year:
            source_text += f" ({source_year})"

        result = (round(co2e, 1), source_text)
        CLIMATIQ_REQUEST_CACHE[cache_key] = result

        return result

    except requests.exceptions.Timeout:
        CLIMATIQ_DISABLED_BY_MODE[mode] = "timeout"

        return (
            None,
            "local prototype factor used after Climatiq API fallback: timeout",
        )

    except Exception as error:
        reason = type(error).__name__
        CLIMATIQ_DISABLED_BY_MODE[mode] = reason

        return (
            None,
            (
                "local prototype factor used after Climatiq API fallback: "
                f"{reason}"
            ),
        )


def estimate_carbon_kg(mode: str, distance_km: float):
    api_value, source = query_climatiq_transport_estimate(
        mode,
        distance_km,
    )

    if api_value is not None:
        return round(api_value, 1), source

    local_value = distance_km * CARBON_FACTORS_KG_PER_KM[mode]

    return round(local_value, 1), source


def estimate_price(mode: str, distance_km: float) -> int:
    if mode == "Car":
        fuel_litres = (
            distance_km
            * DEFAULT_CAR_FUEL_L_PER_100_KM
            / 100.0
        )

        return int(round(
            fuel_litres
            * DEFAULT_FUEL_PRICE_EUR_PER_L
        ))

    rule = MODE_PRICE_RULES[mode]

    price = rule["base"] + distance_km * rule["per_km"]

    return int(round(price))


def mode_preference_score(
    mode: str,
    sustainability_level: str,
    trip_type: str,
) -> float:
    low_carbon_modes = ["Train", "Bus"]

    if sustainability_level == "high":
        sustainability_score = 1.0 if mode in low_carbon_modes else 0.35
    elif sustainability_level == "medium":
        sustainability_score = 0.8 if mode in low_carbon_modes else 0.55
    else:
        sustainability_score = 0.65 if mode in low_carbon_modes else 0.75

    scenario_scores = {
        "city_break": {
            "Train": 1.0,
            "Bus": 0.85,
            "Car": 0.35,
            "Flight": 0.45,
        },
        "rural_eco_tour": {
            "Train": 0.90,
            "Bus": 1.0,
            "Car": 0.60,
            "Flight": 0.25,
        },
        "business_trip": {
            "Train": 1.0,
            "Bus": 0.60,
            "Car": 0.45,
            "Flight": 0.75,
        },
        "general_trip": {
            "Train": 0.85,
            "Bus": 0.80,
            "Car": 0.55,
            "Flight": 0.55,
        },
    }

    scenario_score = scenario_scores.get(
        normalise_trip_type(trip_type),
        scenario_scores["general_trip"],
    ).get(mode, 0.50)

    return round(
        sustainability_score * 0.70
        + scenario_score * 0.30,
        3,
    )


def scoring_weights(sustainability_level: str) -> Dict[str, float]:
    if sustainability_level == "high":
        return {
            "carbon": 0.60,
            "price": 0.25,
            "preference": 0.15,
        }

    if sustainability_level == "low":
        return {
            "carbon": 0.35,
            "price": 0.50,
            "preference": 0.15,
        }

    return {
        "carbon": 0.45,
        "price": 0.40,
        "preference": 0.15,
    }


def get_accommodation_options(
    destination: str,
    budget: Any,
    nights: int,
) -> List[Dict[str, Any]]:
    options = HOTEL_DATABASE.get(
        destination,
        HOTEL_DATABASE["default"],
    )

    budget_value = safe_float(
        budget,
        0,
    )

    enriched_options = []

    for hotel in options:
        enriched_hotel = dict(hotel)
        total_price = hotel["price"] * nights

        enriched_hotel["nights"] = nights
        enriched_hotel["total_price"] = total_price
        enriched_hotel["over_budget"] = (
            budget_value > 0
            and total_price > budget_value
        )

        enriched_options.append(enriched_hotel)

    return sorted(
        enriched_options,
        key=lambda hotel: hotel["total_price"],
    )[:2]


def build_transport_options(
    origin: str,
    destination: str,
    budget: Any,
    sustainability_level: str,
    trip_type: str,
    accommodation_total: float,
) -> List[Dict[str, Any]]:
    distance_km = haversine_distance_km(
        origin,
        destination,
    )

    car_route = get_car_route_estimate(
        origin,
        destination,
    )

    budget_value = max(
        safe_float(budget, 1.0),
        1.0,
    )

    modes = [
        "Train",
        "Bus",
        "Car",
        "Flight",
    ]

    mode_distances = {
        mode: (
            car_route["road_distance_km"]
            if mode == "Car"
            else distance_km
        )
        for mode in modes
    }

    with ThreadPoolExecutor(
        max_workers=len(modes),
    ) as executor:
        carbon_estimates = dict(
            zip(
                modes,
                executor.map(
                    lambda mode: estimate_carbon_kg(
                        mode,
                        mode_distances[mode],
                    ),
                    modes,
                ),
            )
        )

    options = []
    weights = scoring_weights(sustainability_level)

    for mode in modes:
        mode_distance_km = mode_distances[mode]

        price = estimate_price(
            mode,
            mode_distance_km,
        )

        carbon, source = carbon_estimates[mode]

        label = carbon_label(
            carbon,
            mode_distance_km,
        )

        estimated_trip_total = price + accommodation_total

        carbon_component = 1 / (1 + carbon / 100)
        price_component = 1 / (1 + estimated_trip_total / budget_value)

        preference_component = mode_preference_score(
            mode,
            sustainability_level,
            trip_type,
        )

        score = (
            carbon_component * weights["carbon"]
            + price_component * weights["price"]
            + preference_component * weights["preference"]
        )

        if label == "green":
            explanation = (
                "Low-emission option compared with the other available modes."
            )
        elif label == "amber":
            explanation = (
                "Moderate-emission option; consider train or bus if available."
            )
        else:
            explanation = (
                "High-emission option. Consider a lower-carbon alternative if possible."
            )

        if estimated_trip_total <= budget_value:
            budget_message = (
                "Estimated transport plus accommodation total: "
                f"€{estimated_trip_total:.0f}. Within the stated budget."
            )
        else:
            over_budget_by = estimated_trip_total - budget_value

            budget_message = (
                "Estimated transport plus accommodation total: "
                f"€{estimated_trip_total:.0f}. "
                f"OVER BUDGET by €{over_budget_by:.0f}."
            )

        car_details_message = ""

        if mode == "Car":
            ferry_details_message = ""

            if car_route["has_ferry"]:
                ferry_details_message = (
                    "Ferry required: Yes. "
                    f"Ferry route: {car_route['ferry_route_name']}. "
                    "Ferry crossing estimate: "
                    f"{car_route['ferry_distance_km']:.0f} km, "
                    f"{car_route['ferry_duration_display']}. "
                    "Total route time excluding ferry check-in: "
                    f"{car_route['total_duration_display']}. "
                    "Ferry vehicle fare and ferry emissions are "
                    "not included in this prototype estimate. "
                )

            car_details_message = (
                "One-way road estimate: "
                f"{car_route['road_distance_km']:.0f} km, "
                f"{car_route['duration_display']}. "
                f"Estimated fuel: {car_route['fuel_litres']:.1f} L "
                f"at {car_route['fuel_consumption']:.1f} L/100 km. "
                f"Fuel price assumption: "
                f"€{car_route['fuel_price']:.2f}/L. "
                "Tolls are not included. "
                f"{ferry_details_message}"
                f"Route source: {car_route['route_source']}. "
            )

        options.append({
            "mode": mode,
            "price": price,
            "carbon": carbon,
            "label": label,
            "score": round(score, 3),
            "estimated_trip_total": round(estimated_trip_total, 2),
            "over_budget": estimated_trip_total > budget_value,
            "distance_km": round(mode_distance_km, 1),
            "car_route": (
                dict(car_route)
                if mode == "Car"
                else None
            ),
            "source": (
                f"{source}. "
                f"{explanation} "
                f"{car_details_message}"
                f"Suitable for: {trip_type_label(trip_type)}. "
                f"{budget_message}"
            ),
        })

    return sorted(
        options,
        key=lambda item: (
            item["over_budget"],
            -item["score"],
        ),
    )


def get_cultural_experiences(
    destination: str,
    trip_type: str,
) -> List[str]:
    destination_experiences = CULTURAL_EXPERIENCES.get(
        destination,
        CULTURAL_EXPERIENCES["default"],
    )

    trip_type_key = normalise_trip_type(trip_type) or "general_trip"

    scenario_experience = TRIP_TYPE_ACTIVITY.get(
        trip_type_key,
        TRIP_TYPE_ACTIVITY["general_trip"],
    )

    return [
        scenario_experience,
        *destination_experiences,
    ]


def format_recommendations(
    origin: str,
    destination: str,
    departure_date: Any,
    return_date: Any,
    budget: Any,
    sustainability_level: str,
    trip_type: str,
) -> str:
    origin = normalise_city(origin)
    destination = normalise_city(destination)

    sustainability_level = str(
        sustainability_level or "medium"
    ).lower()

    trip_type = normalise_trip_type(trip_type) or "general_trip"
    trip_type_display = trip_type_label(trip_type)

    distance_km = haversine_distance_km(
        origin,
        destination,
    )

    budget_value = safe_float(
        budget,
        0,
    )

    nights = calculate_trip_nights(
        departure_date,
        return_date,
    )

    hotels = get_accommodation_options(
        destination,
        budget_value,
        nights,
    )

    lowest_hotel_total = min(
        (
            hotel["total_price"]
            for hotel in hotels
        ),
        default=0,
    )

    ranked_transport = build_transport_options(
        origin=origin,
        destination=destination,
        budget=budget_value,
        sustainability_level=sustainability_level,
        trip_type=trip_type,
        accommodation_total=lowest_hotel_total,
    )

    experiences = get_cultural_experiences(
        destination,
        trip_type,
    )

    minimum_package = min(
        ranked_transport,
        key=lambda option: option["estimated_trip_total"],
    )

    minimum_hotel = min(
        hotels,
        key=lambda hotel: hotel["total_price"],
    )

    suggested_budget = math.ceil(
        minimum_package["estimated_trip_total"]
    )

    budget_gap = max(
        suggested_budget - budget_value,
        0,
    )

    all_options_over_budget = (
        bool(ranked_transport)
        and all(
            option["over_budget"]
            for option in ranked_transport
        )
    )

    lines = [
        (
            "Here are sustainable travel "
            "recommendations for "
            f"{origin} to {destination}."
        ),
        (
            "Trip context: estimated route "
            f"distance is {distance_km:.0f} km, "
            f"budget reference is €{budget_value:.0f}, "
            f"stay length is {nights} "
            f"night{'s' if nights != 1 else ''}, "
            f"trip type is {trip_type_display}, "
            "and sustainability priority is "
            f"{sustainability_level}."
        ),
    ]

    if all_options_over_budget:
        lines.append(
            "Budget alert: Your current budget "
            "does not cover the estimated transport "
            "and accommodation costs."
        )

        lines.append(
            "The lowest current estimate is "
            f"{minimum_package['mode']} + "
            f"{minimum_hotel['name']} at "
            f"approximately €{suggested_budget}, "
            f"which is €{budget_gap:.0f} above "
            f"your €{budget_value:.0f} budget."
        )

        lines.append(
            "Prices are estimates. You can edit "
            "your budget, change the travel date, "
            "choose another destination, or ask "
            "an advisor."
        )

    lines.extend([
        (
            "Scoring method: each option is ranked "
            "using a weighted score that combines "
            "lower carbon impact, estimated total "
            "trip cost, sustainability preference, "
            "and fit with the selected trip type."
        ),
        (
            "Transport options ranked by carbon "
            "impact, total estimated cost, and "
            "your preferences:"
        ),
    ])

    for index, option in enumerate(
        ranked_transport,
        start=1,
    ):
        lines.append(
            f"{index}. {option['mode']} | "
            f"Price: €{option['price']} | "
            f"Carbon: {option['carbon']} kg CO2e | "
            f"Label: {option['label']} | "
            f"Score: {option['score']} | "
            f"Source: {option['source']}"
        )

    lines.append("Eco-certified accommodation options:")

    for hotel in hotels:
        if hotel["over_budget"]:
            hotel_budget_status = (
                "Accommodation alone exceeds the total budget."
            )
        else:
            hotel_budget_status = (
                "Accommodation is within the total budget before transport is added."
            )

        lines.append(
            f"- {hotel['name']} in "
            f"{destination} | "
            f"€{hotel['price']} per night | "
            f"{nights}-night total: "
            f"€{hotel['total_price']} | "
            f"Budget status: "
            f"{hotel_budget_status} | "
            f"Features: {hotel['features']} | "
            f"Source: {hotel['source']}"
        )

    lines.append(
        "Local cultural experiences that support communities:"
    )

    for experience in experiences:
        lines.append(f"- {experience}")

    lines.append(
        "Environmental note: Carbon values "
        "are approximate and should be used "
        "for comparison, not as exact "
        "scientific claims. Emission colours "
        "are based on carbon intensity per "
        "passenger-kilometre rather than total "
        "trip distance. This prototype avoids "
        "claiming that a trip is carbon-neutral "
        "unless verified offset or certification "
        "data is available. Personal travel "
        "data should be handled only for trip "
        "planning and advisor handover."
    )

    return "\n".join(lines)


def confirmation_decision(tracker: Tracker):
    raw_text = str(tracker.latest_message.get("text", "")).casefold().strip()

    if raw_text == "/affirm":
        return "yes"

    if raw_text == "/deny":
        return "no"

    cleaned_text = re.sub(r"[^a-z\s]", "", raw_text).strip()

    uncertain_answers = [
        "unsure",
        "not sure",
        "maybe",
        "i dont know",
        "i am not sure",
        "im not sure",
    ]

    if cleaned_text in uncertain_answers:
        return None

    compact_text = cleaned_text.replace(" ", "")

    if re.fullmatch(r"y+e+s+|y+e+a+h+|y+e+p+|s+u+r+e+|o+k+a+y+", compact_text):
        return "yes"

    if re.fullmatch(r"n+o+|n+o+p+e+", compact_text):
        return "no"

    return None

def city_confirmation_buttons():
    return [
        {"title": "Yes", "payload": "/affirm"},
        {"title": "No", "payload": "/deny"},
    ]

def normalise_preference_text(value: Any) -> str:
    text = str(value or "").casefold().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )
    text = text.replace("ı", "i")
    text = re.sub(r"[^a-z\s-]", " ", text)

    return re.sub(r"\s+", " ", text).strip()

def fuzzy_word_present(
    text: str,
    target: str,
    cutoff: float = 0.76,
) -> bool:
    words = text.replace("-", " ").split()

    if target in words:
        return True

    return bool(get_close_matches(target, words, n=1, cutoff=cutoff))

def classify_sustainability_preference(value: Any):
    raw_value = str(value or "").casefold().strip()

    payload_match = re.search(
        r'"sustainability_level"\s*:\s*"(low|medium|high)"',
        raw_value,
    )

    if payload_match:
        return payload_match.group(1)

    text = normalise_preference_text(raw_value)

    if not text:
        return None

    words = text.replace("-", " ").split()
    compact_text = "".join(words)

    direct_choices = {
        "low": "low",
        "lo": "low",
        "lowest": "low",
        "medium": "medium",
        "med": "medium",
        "moderate": "medium",
        "balanced": "medium",
        "high": "high",
        "hi": "high",
        "veryhigh": "high",
        "maximum": "high",
    }

    if compact_text in direct_choices:
        return direct_choices[compact_text]

    if len(words) <= 2:
        close_choice = get_close_matches(
            compact_text,
            list(direct_choices.keys()),
            n=1,
            cutoff=0.74,
        )

        if close_choice:
            return direct_choices[close_choice[0]]

    importance_word = (
        fuzzy_word_present(text, "important")
        or fuzzy_word_present(text, "priority")
    )

    low_phrases = [
        "not important",
        "not very important",
        "not too important",
        "low priority",
        "does not matter",
        "doesnt matter",
        "price matters more",
        "budget matters more",
        "price is more important",
        "budget is more important",
        "budget is important",
        "convenience is important",
        "cheapest option",
        "cheap option",
        "prioritise price",
        "prioritize price",
    ]

    if any(phrase in text for phrase in low_phrases):
        return "low"

    if importance_word and any(
        word in {"not", "unimportant", "irrelevant", "least", "less"}
        for word in words
    ):
        return "low"

    price_focused = (
        fuzzy_word_present(text, "price")
        or fuzzy_word_present(text, "budget")
        or fuzzy_word_present(text, "cheapest")
        or fuzzy_word_present(text, "convenience")
    )

    if price_focused and importance_word:
        return "low"

    medium_phrases = [
        "somewhat important",
        "slightly important",
        "a little important",
        "moderately important",
        "both price and sustainability",
        "balance price and sustainability",
        "balanced option",
        "balanced options",
        "compromise",
    ]

    if any(phrase in text for phrase in medium_phrases):
        return "medium"

    if (
        fuzzy_word_present(text, "balanced")
        or fuzzy_word_present(text, "moderate")
        or fuzzy_word_present(text, "somewhat")
        or fuzzy_word_present(text, "compromise")
    ):
        return "medium"

    high_phrases = [
        "greenest",
        "lowest carbon",
        "low carbon",
        "lowest emission",
        "reduce emissions",
        "carbon reduction",
        "environment is important",
        "environment is very important",
        "environmental impact is important",
        "sustainability is important",
        "environment is my priority",
        "main priority",
        "most important",
        "very important",
    ]

    if any(phrase in text for phrase in high_phrases):
        return "high"

    if (
        importance_word
        or fuzzy_word_present(text, "greenest")
        or fuzzy_word_present(text, "sustainable")
        or fuzzy_word_present(text, "sustainability")
    ):
        return "high"

    return None

class ActionAskTripFormOrigin(Action):

    def name(self) -> Text:
        return "action_ask_trip_form_origin"

    def run(self, dispatcher, tracker, domain):

        pending_city = tracker.get_slot("pending_city")
        pending_slot = tracker.get_slot("pending_city_slot")

        if pending_city and pending_slot == "origin":
            dispatcher.utter_message(
                text=f"Did you mean {pending_city}?",
                buttons=city_confirmation_buttons(),
            )
            return []

        backup = get_change_backup(tracker)
        destination = normalise_city(
            tracker.get_slot("destination")
            or backup.get("destination")
        )
        previous_origin = normalise_city(
            backup.get("origin")
        )

        choices = [
            "Istanbul", "Paris", "Berlin",
            "Amsterdam", "Barcelona", "Rome",
            "Copenhagen",
        ]

        blocked = {
            city_search_key(city)
            for city in [destination, previous_origin]
            if city
        }

        available = [
            city for city in choices
            if city_search_key(city) not in blocked
        ]

        limit = 3 if backup else 4

        buttons = [
            {
                "title": city,
                "payload": (
                    f'/provide_origin{{"origin":"{city}"}}'
                ),
            }
            for city in available[:limit]
        ]

        if backup:
            buttons.append({
                "title": "Cancel change",
                "payload": "/cancel_change",
            })

        dispatcher.utter_message(
            text=(
                "Where will your journey start? "
                "Choose a city or type another location."
            ),
            buttons=buttons,
        )

        return []

class ActionAskTripFormDestination(Action):

    def name(self) -> Text:
        return "action_ask_trip_form_destination"

    def run(self, dispatcher, tracker, domain):

        pending_city = tracker.get_slot("pending_city")
        pending_slot = tracker.get_slot("pending_city_slot")

        if pending_city and pending_slot == "destination":
            dispatcher.utter_message(
                text=f"Did you mean {pending_city}?",
                buttons=city_confirmation_buttons(),
            )
            return []

        backup = get_change_backup(tracker)
        origin = normalise_city(
            tracker.get_slot("origin")
            or backup.get("origin")
        )
        previous_destination = normalise_city(
            backup.get("destination")
        )

        choices = [
            "Paris", "Amsterdam", "Berlin",
            "Barcelona", "Rome", "Copenhagen",
        ]

        blocked = {
            city_search_key(city)
            for city in [origin, previous_destination]
            if city
        }

        available = [
            city for city in choices
            if city_search_key(city) not in blocked
        ]

        limit = 3 if backup else 4

        buttons = [
            {
                "title": city,
                "payload": (
                    f'/provide_destination'
                    f'{{"destination":"{city}"}}'
                ),
            }
            for city in available[:limit]
        ]

        if backup:
            buttons.append({
                "title": "Cancel change",
                "payload": "/cancel_change",
            })

        dispatcher.utter_message(
            text="Where would you like to travel?",
            buttons=buttons,
        )

        return []

class ValidateTripForm(FormValidationAction):

    def name(self) -> Text:
        return "validate_trip_form"

    def _is_requested(
        self,
        tracker: Tracker,
        slot_name: Text,
    ) -> bool:
        return tracker.get_slot("requested_slot") == slot_name

    def _parse_date(self, value):
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        text = str(value or "").strip()

        if not text:
            return None

        normalised_text = re.sub(
            r"\s+",
            " ",
            text.casefold(),
        ).strip()

        vague_expressions = {
            "summer",
            "winter",
            "spring",
            "autumn",
            "fall",
            "sometime",
            "next month",
            "next year",
        }

        if normalised_text in vague_expressions:
            return None

        if re.fullmatch(r"\d{4}", normalised_text):
            return None

        exact_formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d.%m.%Y",
            "%d %B %Y",
            "%d %b %Y",
            "%B %d %Y",
            "%b %d %Y",
        ]

        for date_format in exact_formats:
            try:
                return datetime.strptime(
                    text,
                    date_format,
                ).date()
            except ValueError:
                continue

        weekday_numbers = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }

        weekday_match = re.fullmatch(
            r"(?:(?:next|coming|this)\s+)?"
            r"(monday|tuesday|wednesday|thursday|"
            r"friday|saturday|sunday)",
            normalised_text,
        )

        if weekday_match:
            target_weekday = weekday_numbers[
                weekday_match.group(1)
            ]

            today = date.today()

            days_ahead = (
                target_weekday - today.weekday()
            ) % 7

            if days_ahead == 0:
                days_ahead = 7

            return today + timedelta(days=days_ahead)

        try:
            parsed_value = dateparser.parse(
                text,
                languages=["en"],
                settings={
                    "DATE_ORDER": "DMY",
                    "PREFER_LOCALE_DATE_ORDER": False,
                    "PREFER_DATES_FROM": "future",
                    "RELATIVE_BASE": datetime.now(),
                    "RETURN_AS_TIMEZONE_AWARE": False,
                    "STRICT_PARSING": False,
                },
            )

        except (
            ValueError,
            TypeError,
            OverflowError,
        ):
            return None

        if parsed_value is None:
            return None

        return parsed_value.date()


    def _validate_travel_date(
        self,
        value,
        dispatcher,
        slot_label,
    ):
        parsed_date = self._parse_date(value)

        if not parsed_date:
            dispatcher.utter_message(
                text=(
                    f"I could not identify the {slot_label}. "
                    "You can enter a date such as 10 July 2026, "
                    "10/07/2026, next Friday, or 2026-07-10."
                )
            )
            return None

        today = date.today()
        max_allowed_date = today + timedelta(days=730)

        if parsed_date < today:
            dispatcher.utter_message(
                text=(
                    f"The {slot_label} cannot be in the past. "
                    "Please enter a future date."
                )
            )
            return None

        if parsed_date > max_allowed_date:
            dispatcher.utter_message(
                text=(
                    f"The {slot_label} is too far in the future. "
                    "Please choose a date within the next two years."
                )
            )
            return None

        return parsed_date.isoformat()

    def validate_origin(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:

        if not self._is_requested(tracker, "origin"):
            return {"origin": tracker.get_slot("origin")}

        pending_city = tracker.get_slot("pending_city")
        pending_slot = tracker.get_slot("pending_city_slot")

        if pending_city and pending_slot == "origin":
            confirmation = confirmation_decision(tracker)

            if confirmation == "yes":
                destination = normalise_city(
                    tracker.get_slot("destination")
                )

                if (
                    destination
                    and city_search_key(pending_city)
                    == city_search_key(destination)
                ):
                    dispatcher.utter_message(
                        text=(
                            "Your starting city should be different "
                            "from your destination."
                        )
                    )

                    return {
                        "origin": None,
                        "pending_city": None,
                        "pending_city_slot": None,
                    }

                return {
                    "origin": pending_city,
                    "pending_city": None,
                    "pending_city_slot": None,
                }

            if confirmation == "no":
                dispatcher.utter_message(
                    text=(
                        "No problem. Please enter your starting "
                        "city again."
                    )
                )

                return {
                    "origin": None,
                    "pending_city": None,
                    "pending_city_slot": None,
                }

            dispatcher.utter_message(
                text="Please choose Yes or No."
            )

            return {
                "origin": None,
                "pending_city": pending_city,
                "pending_city_slot": "origin",
            }

        resolved_city, suggested_city = resolve_city_input(
            slot_value
        )

        if resolved_city:
            destination = normalise_city(
                tracker.get_slot("destination")
            )

            if (
                destination
                and city_search_key(resolved_city)
                == city_search_key(destination)
            ):
                dispatcher.utter_message(
                    text=(
                        "Your starting city should be different "
                        "from your destination."
                    )
                )

                return {
                    "origin": None,
                    "pending_city": None,
                    "pending_city_slot": None,
                }

            return {
                "origin": resolved_city,
                "pending_city": None,
                "pending_city_slot": None,
            }

        if suggested_city:
            return {
                "origin": None,
                "pending_city": suggested_city,
                "pending_city_slot": "origin",
            }

        dispatcher.utter_message(
            text=(
                "I could not identify that starting city. "
                "Please check the spelling and enter a supported "
                "city again."
            )
        )

        return {
            "origin": None,
            "pending_city": None,
            "pending_city_slot": None,
        }

    def validate_destination(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:

        if not self._is_requested(tracker, "destination"):
            return {
                "destination": tracker.get_slot("destination")
            }

        pending_city = tracker.get_slot("pending_city")
        pending_slot = tracker.get_slot("pending_city_slot")
        origin = normalise_city(tracker.get_slot("origin"))

        if pending_city and pending_slot == "destination":
            confirmation = confirmation_decision(tracker)

            if confirmation == "yes":
                if (
                    origin
                    and city_search_key(pending_city)
                    == city_search_key(origin)
                ):
                    dispatcher.utter_message(
                        text=(
                            "Your destination should be different "
                            "from your starting city."
                        )
                    )

                    return {
                        "destination": None,
                        "pending_city": None,
                        "pending_city_slot": None,
                    }

                return {
                    "destination": pending_city,
                    "pending_city": None,
                    "pending_city_slot": None,
                }

            if confirmation == "no":
                dispatcher.utter_message(
                    text=(
                        "No problem. Please enter your destination "
                        "again."
                    )
                )

                return {
                    "destination": None,
                    "pending_city": None,
                    "pending_city_slot": None,
                }

            dispatcher.utter_message(
                text="Please choose Yes or No."
            )

            return {
                "destination": None,
                "pending_city": pending_city,
                "pending_city_slot": "destination",
            }

        resolved_city, suggested_city = resolve_city_input(
            slot_value
        )

        if resolved_city:
            if (
                origin
                and city_search_key(resolved_city)
                == city_search_key(origin)
            ):
                dispatcher.utter_message(
                    text=(
                        "Your destination should be different "
                        "from your starting city."
                    )
                )

                return {
                    "destination": None,
                    "pending_city": None,
                    "pending_city_slot": None,
                }

            return {
                "destination": resolved_city,
                "pending_city": None,
                "pending_city_slot": None,
            }

        if suggested_city:
            return {
                "destination": None,
                "pending_city": suggested_city,
                "pending_city_slot": "destination",
            }

        dispatcher.utter_message(
            text=(
                "I could not identify that destination. "
                "Please check the spelling and enter a supported "
                "city again."
            )
        )

        return {
            "destination": None,
            "pending_city": None,
            "pending_city_slot": None,
        }

    def validate_departure_date(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:

        if not self._is_requested(tracker, "departure_date"):
            return {
                "departure_date": tracker.get_slot(
                    "departure_date"
                )
            }

        valid_date = self._validate_travel_date(
            slot_value,
            dispatcher,
            "departure date",
        )

        if not valid_date:
            return {"departure_date": None}

        current_return_date = self._parse_date(
            tracker.get_slot("return_date")
        )
        parsed_departure_date = self._parse_date(valid_date)

        if (
            current_return_date
            and parsed_departure_date
            and parsed_departure_date > current_return_date
        ):
            if (
                tracker.get_slot("editing_trip_detail")
                == "departure_date"
            ):
                dispatcher.utter_message(
                    text=(
                        "Your new departure date is after the "
                        "current return date, so the return date "
                        "must also be updated."
                    )
                )

                return {
                    "departure_date": valid_date,
                    "return_date": None,
                }

            dispatcher.utter_message(
                text=(
                    "The departure date cannot be after the "
                    "return date."
                )
            )
            return {"departure_date": None}

        return {"departure_date": valid_date}

    def validate_return_date(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:

        if not self._is_requested(tracker, "return_date"):
            return {
                "return_date": tracker.get_slot("return_date")
            }

        valid_date = self._validate_travel_date(
            slot_value,
            dispatcher,
            "return date",
        )

        if not valid_date:
            return {"return_date": None}

        departure_date = self._parse_date(
            tracker.get_slot("departure_date")
        )
        return_date = self._parse_date(valid_date)

        if (
            departure_date
            and return_date
            and return_date < departure_date
        ):
            dispatcher.utter_message(
                text=(
                    "The return date cannot be before the "
                    "departure date."
                )
            )
            return {"return_date": None}

        return {"return_date": valid_date}

    def validate_budget(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:

        if not self._is_requested(tracker, "budget"):
            return {"budget": tracker.get_slot("budget")}

        match = re.search(
            r"[-+]?\s*\d+(?:[.,]\d+)?",
            str(slot_value),
        )

        if not match:
            dispatcher.utter_message(
                text=(
                    "Please enter your budget as a number, "
                    "for example 700."
                )
            )
            return {"budget": None}

        budget_text = (
            match.group()
            .replace(" ", "")
            .replace(",", ".")
        )

        try:
            budget = float(budget_text)
        except ValueError:
            dispatcher.utter_message(
                text="Please enter a valid budget number."
            )
            return {"budget": None}

        if budget <= 0:
            dispatcher.utter_message(
                text=(
                    "Your budget must be greater than zero. "
                    "Please enter a positive amount."
                )
            )
            return {"budget": None}

        if budget > 50000:
            dispatcher.utter_message(
                text=(
                    "That budget looks unusually high. "
                    "Please enter an approximate travel budget "
                    "in euros."
                )
            )
            return {"budget": None}

        return {"budget": budget}

    def validate_trip_type(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:

        if not self._is_requested(
            tracker,
            "trip_type",
        ):
            return {
                "trip_type": tracker.get_slot("trip_type")
            }

        latest_text = str(
            tracker.latest_message.get("text", "")
        ).strip()

        # Quick-reply payloads begin with "/".
        # For typed messages, validate the actual user text.
        if latest_text.startswith("/"):
            candidate = slot_value
        else:
            candidate = latest_text or slot_value

        trip_type = normalise_trip_type(candidate)

        if trip_type:
            return {"trip_type": trip_type}

        dispatcher.utter_message(
            text=(
                "I could not determine the trip type. "
                "Please choose city break, rural eco-tour, "
                "business trip, or general trip."
            )
        )

        return {"trip_type": None}

    def validate_sustainability_level(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:

        if not self._is_requested(
            tracker,
            "sustainability_level",
        ):
            return {
                "sustainability_level": tracker.get_slot(
                    "sustainability_level"
                )
            }

        level = classify_sustainability_preference(slot_value)

        if level:
            return {"sustainability_level": level}

        dispatcher.utter_message(
            text=(
                "I could not determine your sustainability "
                "preference. Please choose low, medium, or high."
            )
        )

        return {"sustainability_level": None}

DETAIL_LABELS = {
    "origin": "Starting city",
    "destination": "Destination",
    "trip_type": "Trip type",
    "departure_date": "Departure date",
    "return_date": "Return date",
    "budget": "Budget",
    "sustainability_level": "Sustainability preference",
        "selected_transport_mode": "Transport",
    "selected_hotel_name": "Hotel",
}

DETAIL_NAME_ALIASES = {
    "starting city": "origin",
    "origin": "origin",
    "departure city": "origin",
    "destination": "destination",
    "destination city": "destination",
    "departure date": "departure_date",
    "travel dates": "departure_date",
    "return date": "return_date",
    "budget": "budget",
    "sustainability": "sustainability_level",
    "sustainability preference": "sustainability_level",
    "environmental preference": "sustainability_level",
    "trip type": "trip_type",
    "travel type": "trip_type",
    "travel purpose": "trip_type",
    "travel scenario": "trip_type",
    "transport": "selected_transport_mode",
    "transport option": "selected_transport_mode",
    "travel mode": "selected_transport_mode",
    "hotel": "selected_hotel_name",
    "accommodation": "selected_hotel_name",
    "eco hotel": "selected_hotel_name",
}

TRIP_DETAIL_FIELDS = [
    "origin",
    "destination",
    "trip_type",
    "departure_date",
    "return_date",
    "budget",
    "sustainability_level",
    "selected_transport_mode",
    "selected_hotel_name",
]

def trip_details_snapshot(tracker):
    return {
        field: tracker.get_slot(field)
        for field in TRIP_DETAIL_FIELDS
    }

def get_change_backup(tracker):
    backup = tracker.get_slot("trip_change_backup")

    return backup if isinstance(backup, dict) else {}

def detail_change_buttons():
    return [
        {
            "title": "Starting city",
            "payload": (
                '/change_trip_detail{"detail_to_change":"origin"}'
            ),
        },
        {
            "title": "Destination",
            "payload": (
                '/change_trip_detail'
                '{"detail_to_change":"destination"}'
            ),
        },

        {
            "title": "Trip type",
            "payload": (
                '/change_trip_detail'
                '{"detail_to_change":"trip_type"}'
            ),
        },

        {
            "title": "Departure date",
            "payload": (
                '/change_trip_detail'
                '{"detail_to_change":"departure_date"}'
            ),
        },
        {
            "title": "Return date",
            "payload": (
                '/change_trip_detail'
                '{"detail_to_change":"return_date"}'
            ),
        },
        {
            "title": "Budget",
            "payload": (
                '/change_trip_detail{"detail_to_change":"budget"}'
            ),
        },
        {
            "title": "Sustainability",
            "payload": (
                '/change_trip_detail'
                '{"detail_to_change":"sustainability_level"}'
            ),
        },

        {
            "title": "Transport",
            "payload": (
                '/change_trip_detail'
                '{"detail_to_change":"selected_transport_mode"}'
            ),
        },
        {
            "title": "Hotel",
            "payload": (
                '/change_trip_detail'
                '{"detail_to_change":"selected_hotel_name"}'
            ),
        },

        {
            "title": "Cancel change",
            "payload": "/cancel_change",
        },
    ]

def readable_detail_value(
    detail_name: str,
    value: Any,
) -> str:

    if detail_name == "trip_type":
        return trip_type_label(value)

    if detail_name == "budget":
        return f"€{safe_float(value, 0):.0f}"

    if detail_name == "sustainability_level":
        return str(value or "not provided").title()

    return str(value or "not provided")

class ActionChooseDetailToChange(Action):

    def name(self) -> Text:
        return "action_choose_detail_to_change"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(
            text="Which trip detail would you like to change?",
            buttons=detail_change_buttons(),
        )

        return [
            SlotSet("awaiting_trip_confirmation", False),
            SlotSet("awaiting_detail_confirmation", False),
            SlotSet("editing_trip_detail", None),
            SlotSet("fallback_count", 0),
            FollowupAction("action_listen"),
            SlotSet(
                "trip_change_backup",
                trip_details_snapshot(tracker),
            ),
        ]

class ActionPrepareDetailChange(Action):

    def name(self) -> Text:
        return "action_prepare_detail_change"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        detail_name = next(
            tracker.get_latest_entity_values(
                "detail_to_change"
            ),
            None,
        )

        if detail_name:
            detail_name = DETAIL_NAME_ALIASES.get(
                str(detail_name).casefold().strip(),
                str(detail_name).strip(),
            )

        if detail_name not in DETAIL_LABELS:
            dispatcher.utter_message(
                text=(
                    "Which trip detail would you like to change?"
                ),
                buttons=detail_change_buttons(),
            )

            return [FollowupAction("action_listen")]

        label = DETAIL_LABELS[detail_name]

        if detail_name == "selected_transport_mode":
            dispatcher.utter_message(
                text=(
                    "Okay. Please choose a new transport option "
                    "from the recommendation cards."
                )
            )

            return [
                SlotSet("selected_transport_mode", None),
                SlotSet("editing_trip_detail", None),
                SlotSet("awaiting_trip_confirmation", False),
                SlotSet("awaiting_detail_confirmation", False),
                SlotSet("fallback_count", 0),
                FollowupAction("action_listen"),
            ]

        if detail_name == "selected_hotel_name":
            dispatcher.utter_message(
                text=(
                    "Okay. Please choose a new eco hotel from "
                    "the hotel cards."
                )
            )

            return [
                SlotSet("selected_hotel_name", None),
                SlotSet("editing_trip_detail", None),
                SlotSet("awaiting_trip_confirmation", False),
                SlotSet("awaiting_detail_confirmation", False),
                SlotSet("fallback_count", 0),
                FollowupAction("action_listen"),
            ]

        dispatcher.utter_message(
            text=f"Okay. Please enter the new {label.lower()}."
        )

        backup = get_change_backup(tracker)

        if not backup:
          backup = trip_details_snapshot(tracker)


        events = [
            SlotSet(detail_name, None),
            SlotSet("editing_trip_detail", detail_name),
            SlotSet("awaiting_trip_confirmation", False),
            SlotSet("awaiting_detail_confirmation", False),
            SlotSet("fallback_count", 0),
            SlotSet("trip_change_backup", backup),
        ]

        if detail_name in {"origin", "destination"}:
            events.extend(
                [
                    SlotSet("pending_city", None),
                    SlotSet("pending_city_slot", None),
                ]
            )

        return events

class ActionReviewTripDetails(Action):

    def name(self) -> Text:
        return "action_review_trip_details"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        editing_detail = tracker.get_slot(
            "editing_trip_detail"
        )

        if editing_detail in DETAIL_LABELS:
            detail_value = tracker.get_slot(editing_detail)
            detail_label = DETAIL_LABELS[editing_detail]

            if editing_detail == "departure_date":
                updated_detail_text = (
                    "Updated travel dates:\n"
                    f"Departure: {tracker.get_slot('departure_date')}\n"
                    f"Return: {tracker.get_slot('return_date')}"
                )
            else:
                updated_detail_text = (
                    f"Updated {detail_label}: "
                    f"{readable_detail_value(editing_detail, detail_value)}"
                )

            dispatcher.utter_message(
                text=(
                    f"{updated_detail_text}\n\n"
                    "Would you like to keep this change?"
                ),
                buttons=[
                    {
                        "title": "Confirm change",
                        "payload": "/affirm",
                    },
                    {
                        "title": "Re-enter value",
                        "payload": "/deny",
                    },
                    {
                        "title": "Cancel change",
                        "payload": "/cancel_change",
                    },
                ],
            )

            return [
                SlotSet("awaiting_detail_confirmation", True),
                SlotSet("awaiting_trip_confirmation", False),
                SlotSet("fallback_count", 0),
            ]

        origin = tracker.get_slot("origin")
        destination = tracker.get_slot("destination")
        trip_type = trip_type_label(
            tracker.get_slot("trip_type")
        )
        departure_date = tracker.get_slot("departure_date")
        return_date = tracker.get_slot("return_date")
        budget = safe_float(tracker.get_slot("budget"), 0)
        sustainability = tracker.get_slot(
            "sustainability_level"
        )

        dispatcher.utter_message(
            text=(
                "Please review your trip details:\n\n"
                f"Route: {origin} to {destination}\n"
                f"Trip type: {trip_type}\n"
                f"Departure: {departure_date}\n"
                f"Return: {return_date}\n"
                f"Budget: €{budget:.0f}\n"
                f"Sustainability priority: {sustainability}\n\n"
                "Are all these details correct?"
            ),
            buttons=[
                {
                    "title": "Confirm all",
                    "payload": "/affirm",
                },
                {
                    "title": "Change details",
                    "payload": "/deny",
                },
            ],
        )

        return [
            SlotSet("awaiting_trip_confirmation", True),
            SlotSet("awaiting_detail_confirmation", False),
            SlotSet("fallback_count", 0),
        ]

class ActionFinishDetailChange(Action):

    def name(self) -> Text:
        return "action_finish_detail_change"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        origin = tracker.get_slot("origin")
        destination = tracker.get_slot("destination")
        trip_type = trip_type_label(
            tracker.get_slot("trip_type")
        )
        departure_date = tracker.get_slot("departure_date")
        return_date = tracker.get_slot("return_date")
        budget = safe_float(tracker.get_slot("budget"), 0)
        sustainability = tracker.get_slot(
            "sustainability_level"
        )

        dispatcher.utter_message(
            text=(
                "The change has been saved.\n\n"
                "Please review your updated trip details:\n\n"
                f"Route: {origin} to {destination}\n"
                f"Trip type: {trip_type}\n"
                f"Departure: {departure_date}\n"
                f"Return: {return_date}\n"
                f"Budget: €{budget:.0f}\n"
                f"Sustainability priority: {sustainability}\n\n"
                "Are all these details correct?"
            ),
            buttons=[
                {
                    "title": "Confirm all",
                    "payload": "/affirm",
                },
                {
                    "title": "Change details",
                    "payload": "/deny",
                },
            ],
        )

        return [
            SlotSet("editing_trip_detail", None),
            SlotSet("awaiting_detail_confirmation", False),
            SlotSet("awaiting_trip_confirmation", True),
            SlotSet("fallback_count", 0),
            SlotSet("trip_change_backup", None),
            FollowupAction("action_listen"),

        ]

class ActionReenterChangedDetail(Action):

    def name(self) -> Text:
        return "action_reenter_changed_detail"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        detail_name = tracker.get_slot(
            "editing_trip_detail"
        )

        if detail_name not in DETAIL_LABELS:
            dispatcher.utter_message(
                text="Please choose the detail again.",
                buttons=detail_change_buttons(),
            )

            return [
                SlotSet("awaiting_detail_confirmation", False),
                FollowupAction("action_listen"),
            ]

        events = [
            SlotSet(detail_name, None),
            SlotSet("awaiting_detail_confirmation", False),
            SlotSet("awaiting_trip_confirmation", False),
            SlotSet("fallback_count", 0),
        ]

        if detail_name in {"origin", "destination"}:
            events.extend(
                [
                    SlotSet("pending_city", None),
                    SlotSet("pending_city_slot", None),
                ]
            )

        events.append(FollowupAction("trip_form"))

        return events

def has_selected_trip_plan(tracker: Tracker) -> bool:
    return bool(
        tracker.get_slot("selected_transport_mode")
        and tracker.get_slot("selected_hotel_name")
    )


def show_selected_plan_review(
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
) -> bool:
    plan_context = build_selected_plan_context(tracker)

    if (
        plan_context.get("selected_option")
        and plan_context.get("selected_hotel")
    ):
        dispatcher.utter_message(
            text=selected_plan_review_text(plan_context),
            buttons=selected_plan_buttons(),
        )
        return True

    return False

class ActionCancelDetailChange(Action):

    def name(self) -> Text:
        return "action_cancel_detail_change"

    def run(self, dispatcher, tracker, domain):

        backup = get_change_backup(tracker)

        if not backup:
            if has_selected_trip_plan(tracker):
                dispatcher.utter_message(
                    text=(
                        "No change was made. Your selected trip plan "
                        "is still active."
                    )
                )

                if show_selected_plan_review(dispatcher, tracker):
                    return [
                        SlotSet("editing_trip_detail", None),
                        SlotSet("awaiting_detail_confirmation", False),
                        SlotSet("awaiting_trip_confirmation", False),
                        SlotSet("fallback_count", 0),
                        FollowupAction("action_listen"),
                    ]

            dispatcher.utter_message(
                text="There is no active change to cancel."
            )

            return [
                SlotSet("editing_trip_detail", None),
                SlotSet("awaiting_detail_confirmation", False),
                SlotSet("awaiting_trip_confirmation", False),
                SlotSet("fallback_count", 0),
                FollowupAction("action_listen"),
            ]

        origin = backup.get("origin")
        destination = backup.get("destination")
        trip_type = trip_type_label(
            backup.get("trip_type")
        )
        departure_date = backup.get("departure_date")
        return_date = backup.get("return_date")
        budget = safe_float(backup.get("budget"), 0)
        sustainability = backup.get(
            "sustainability_level"
        )

        dispatcher.utter_message(
            text=(
                "The change was cancelled. Your previous "
                "trip details have been restored.\n\n"
                "Please review your trip details:\n\n"
                f"Route: {origin} to {destination}\n"
                f"Trip type: {trip_type}\n"
                f"Departure: {departure_date}\n"
                f"Return: {return_date}\n"
                f"Budget: €{budget:.0f}\n"
                f"Sustainability priority: "
                f"{sustainability}\n\n"
                "Are all these details correct?"
            ),
            buttons=[
                {
                    "title": "Confirm all",
                    "payload": "/affirm",
                },
                {
                    "title": "Change details",
                    "payload": "/deny",
                },
            ],
        )

        restored_events = [
            SlotSet(field, backup.get(field))
            for field in TRIP_DETAIL_FIELDS
        ]

        return restored_events + [
            SlotSet("pending_city", None),
            SlotSet("pending_city_slot", None),
            SlotSet("editing_trip_detail", None),
            SlotSet("trip_change_backup", None),
            SlotSet("awaiting_detail_confirmation", False),
            SlotSet("awaiting_trip_confirmation", True),
            SlotSet("fallback_count", 0),
            FollowupAction("action_listen"),
        ]

class ActionResetTripDetails(Action):

    def name(self) -> Text:
        return "action_reset_trip_details"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(
            text="The trip details have been cleared."
        )

        return [
            SlotSet("origin", None),
            SlotSet("destination", None),
            SlotSet("trip_type", None),
            SlotSet("departure_date", None),
            SlotSet("return_date", None),
            SlotSet("budget", None),
            SlotSet("sustainability_level", None),
            SlotSet("pending_city", None),
            SlotSet("pending_city_slot", None),
            SlotSet("editing_trip_detail", None),
            SlotSet("awaiting_detail_confirmation", False),
            SlotSet("awaiting_trip_confirmation", False),
            SlotSet("fallback_count", 0),

        ]

def transport_option_buttons():
    return [
        {
            "title": "Choose Train plan",
            "payload": (
                '/select_transport_option'
                '{"selected_transport_mode":"Train"}'
            ),
        },
        {
            "title": "Choose Bus plan",
            "payload": (
                '/select_transport_option'
                '{"selected_transport_mode":"Bus"}'
            ),
        },
        {
            "title": "Choose Car plan",
            "payload": (
                '/select_transport_option'
                '{"selected_transport_mode":"Car"}'
            ),
        },
        {
            "title": "Choose Flight plan",
            "payload": (
                '/select_transport_option'
                '{"selected_transport_mode":"Flight"}'
            ),
        },
    ]

class ActionShowRecommendations(Action):

    def name(self) -> Text:
        return "action_show_recommendations"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        origin = normalise_city(tracker.get_slot("origin"))
        destination = normalise_city(tracker.get_slot("destination"))
        trip_type = tracker.get_slot("trip_type") or "general_trip"
        departure_date = tracker.get_slot("departure_date")
        return_date = tracker.get_slot("return_date")
        budget = tracker.get_slot("budget")
        sustainability_level = tracker.get_slot("sustainability_level") or "medium"

        missing = []

        if not origin:
            missing.append("origin")
        if not destination:
            missing.append("destination")
        if not trip_type:
            missing.append("trip type")
        if not departure_date:
            missing.append("departure date")
        if not return_date:
            missing.append("return date")
        if not budget:
            missing.append("budget")

        if missing:
            dispatcher.utter_message(
                text=(
                    "I still need the following information before I can recommend options: "
                    + ", ".join(missing)
                    + "."
                )
            )
            return [FollowupAction("action_listen")]

        recommendations = format_recommendations(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            budget=budget,
            sustainability_level=sustainability_level,
            trip_type=trip_type,
        )

        if "Budget alert: Your current budget does " in recommendations:
            follow_up_buttons = [
                {
                    "title": "Edit budget",
                    "payload": '/change_trip_detail{"detail_to_change":"budget"}',
                },
                {
                    "title": "Change details",
                    "payload": "/change_trip_detail",
                },
                {
                    "title": "Prepare advisor summary",
                    "payload": "/request_human_advisor",
                },
                {
                    "title": "Finish",
                    "payload": "/goodbye",
                },
            ]
        else:
            follow_up_buttons = [
                {
                    "title": "Change details",
                    "payload": "/change_trip_detail",
                },
                {
                    "title": "Prepare advisor summary",
                    "payload": "/request_human_advisor",
                },
                {
                    "title": "Finish",
                    "payload": "/goodbye",
                },
            ]

        dispatcher.utter_message(
            text=recommendations,
            buttons=transport_option_buttons() + follow_up_buttons,
        )

        return [
            SlotSet("fallback_count", 0),
            SlotSet("editing_trip_detail", None),
            SlotSet("awaiting_detail_confirmation", False),
            SlotSet("awaiting_trip_confirmation", False),
            FollowupAction("action_listen"),
        ]

def selected_plan_buttons():
    return [
        {
            "title": "Confirm selected plan",
            "payload": "/confirm_selected_plan",
        },
        {
            "title": "Change trip details",
            "payload": "/change_trip_detail",
        },
        {
            "title": "Prepare advisor summary",
            "payload": "/request_human_advisor",
        },

    ]


def latest_entity_value(tracker: Tracker, entity_name: str):
    for entity in tracker.latest_message.get("entities", []):
        if entity.get("entity") == entity_name:
            return entity.get("value")

    text = str(tracker.latest_message.get("text", ""))

    payload_match = re.search(
        rf'"{entity_name}"\s*:\s*"([^"]+)"',
        text,
    )

    if payload_match:
        return payload_match.group(1)

    return None


def build_selected_plan_context(
    tracker: Tracker,
    selected_mode=None,
    selected_hotel_name=None,
):
    origin = normalise_city(tracker.get_slot("origin"))
    destination = normalise_city(tracker.get_slot("destination"))
    departure_date = tracker.get_slot("departure_date")
    return_date = tracker.get_slot("return_date")
    budget = tracker.get_slot("budget")
    sustainability_level = tracker.get_slot("sustainability_level") or "medium"
    trip_type = tracker.get_slot("trip_type") or "general_trip"

    selected_mode = (
        selected_mode
        or tracker.get_slot("selected_transport_mode")
    )

    selected_hotel_name = (
        selected_hotel_name
        or tracker.get_slot("selected_hotel_name")
    )

    nights = calculate_trip_nights(
        departure_date,
        return_date,
    )

    hotels = get_accommodation_options(
        destination,
        safe_float(budget, 0),
        nights,
    )

    selected_hotel = None

    if selected_hotel_name:
        selected_hotel = next(
            (
                hotel
                for hotel in hotels
                if hotel["name"].casefold()
                == str(selected_hotel_name).casefold()
            ),
            None,
        )

    accommodation_total = (
        selected_hotel["total_price"]
        if selected_hotel
        else 0
    )

    transport_options = build_transport_options(
        origin=origin,
        destination=destination,
        budget=budget,
        sustainability_level=sustainability_level,
        trip_type=trip_type,
        accommodation_total=accommodation_total,
    )

    selected_option = next(
        (
            option
            for option in transport_options
            if str(option["mode"]).casefold()
            == str(selected_mode).casefold()
        ),
        None,
    )

    experiences = get_cultural_experiences(
        destination,
        trip_type,
    )


    return {
        "origin": origin,
        "destination": destination,
        "departure_date": departure_date,
        "return_date": return_date,
        "budget": budget,
        "sustainability_level": sustainability_level,
        "trip_type": trip_type,
        "trip_type_display": trip_type_label(trip_type),
        "nights": nights,
        "hotels": hotels,
        "selected_hotel": selected_hotel,
        "selected_option": selected_option,
        "selected_mode": selected_mode,
        "experiences": experiences,
    }


def selected_car_route_text(selected_option):
    if selected_option.get("mode") != "Car":
        return ""

    car_route = selected_option.get("car_route") or {}

    if not car_route:
        return ""

    ferry_route_text = ""

    if car_route.get("has_ferry"):
        ferry_route_text = (
            "Ferry required: Yes\n"
            "Ferry route: "
            f"{car_route['ferry_departure_port']} to "
            f"{car_route['ferry_arrival_port']}\n"
            "Ferry crossing: "
            f"{car_route['ferry_distance_km']:.1f} km\n"
            "Estimated ferry time: "
            f"{car_route['ferry_duration_display']}\n"
            "Total route time: "
            f"{car_route['total_duration_display']} "
            "(excluding ferry check-in and waiting)\n"
            f"Ferry fare: {car_route['ferry_fare_note']}\n"
            "Ferry emissions: "
            f"{car_route['ferry_emissions_note']}\n"
        )

    return (
        f"Road distance: {car_route['road_distance_km']:.1f} km\n"
        "Estimated driving time: "
        f"{car_route['duration_display']}\n"
        f"Estimated fuel: {car_route['fuel_litres']:.1f} L\n"
        "Fuel assumption: "
        f"{car_route['fuel_consumption']:.1f} L/100 km at "
        f"€{car_route['fuel_price']:.2f}/L\n"
        f"Estimated fuel cost: €{car_route['fuel_cost']:.0f}\n"
        f"Tolls: {car_route['toll_note']}\n"
        f"{ferry_route_text}"
        f"Road route source: {car_route['route_source']}\n"
    )


def selected_plan_review_text(plan_context):
    selected_option = plan_context["selected_option"]
    selected_hotel = plan_context["selected_hotel"]

    budget_status = (
        "within your stated budget"
        if not selected_option["over_budget"]
        else "over your stated budget"
    )

    experiences = plan_context.get("experiences", [])[:3]

    experiences_text = "\n".join(
        f"- {experience}"
        for experience in experiences
    )

    if not experiences_text:
        experiences_text = "- Local low-impact experience suggestions are not available for this destination yet."

    car_route_text = selected_car_route_text(
        selected_option
    )

    return (
        "Review your selected trip plan:\n\n"
        f"Route: {plan_context['origin']} to {plan_context['destination']}\n"
        f"Trip type: {plan_context['trip_type_display']}\n"
        f"Dates: {plan_context['departure_date']} to {plan_context['return_date']}\n"
        f"Transport: {selected_option['mode']}, €{selected_option['price']}, "
        f"{selected_option['carbon']} kg CO2e\n"
        f"{car_route_text}"
        f"Hotel: {selected_hotel['name']} in {plan_context['destination']}, "
        f"€{selected_hotel['price']} per night, "
        f"€{selected_hotel['total_price']} total for "
        f"{plan_context['nights']} night"
        f"{'s' if plan_context['nights'] != 1 else ''}\n"
        f"Estimated trip total: €{selected_option['estimated_trip_total']:.0f}, "
        f"{budget_status}.\n\n"
        "Suggested local experiences:\n"
        f"{experiences_text}\n\n"
        "Would you like to confirm this selected plan?"
    )


def selected_plan_final_text(plan_context):
    selected_option = plan_context["selected_option"]
    selected_hotel = plan_context["selected_hotel"]

    budget_status = (
        "within your stated budget"
        if not selected_option["over_budget"]
        else "over your stated budget"
    )

    experiences = plan_context.get("experiences", [])[:3]

    experiences_text = "\n".join(
        f"- {experience}"
        for experience in experiences
    )

    if not experiences_text:
        experiences_text = "- Local low-impact experience suggestions are not available for this destination yet."

    car_route_text = selected_car_route_text(
        selected_option
    )

    return (
        f"Selected trip plan: {selected_option['mode']}\n\n"
        f"Route: {plan_context['origin']} to {plan_context['destination']}\n"
        f"Trip type: {plan_context['trip_type_display']}\n"
        f"Dates: {plan_context['departure_date']} to {plan_context['return_date']}\n"
        f"Transport estimate: €{selected_option['price']}\n"
        f"Transport carbon estimate: {selected_option['carbon']} kg CO2e\n"
        f"{car_route_text}"
        f"Estimated trip total: €{selected_option['estimated_trip_total']:.0f}, "
        f"{budget_status}.\n"
        f"Accommodation: {selected_hotel['name']} in {plan_context['destination']}, "
        f"€{selected_hotel['price']} per night, "
        f"€{selected_hotel['total_price']} total for "
        f"{plan_context['nights']} night"
        f"{'s' if plan_context['nights'] != 1 else ''}\n\n"
        "Suggested local experiences:\n"
        f"{experiences_text}\n\n"
        "This selected plan can now be shared with a human advisor, changed, or finished."
    )


class ActionSelectTransportOption(Action):

    def name(self) -> Text:
        return "action_select_transport_option"

    def _selected_mode(self, tracker: Tracker):
        selected_mode = latest_entity_value(
            tracker,
            "selected_transport_mode",
        )

        if selected_mode:
            return str(selected_mode).title()

        text = str(tracker.latest_message.get("text", ""))
        lowered = text.casefold()

        for mode in ["Train", "Bus", "Car", "Flight"]:
            if mode.casefold() in lowered:
                return mode

        return None

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        selected_mode = self._selected_mode(tracker)

        if selected_mode not in {"Train", "Bus", "Car", "Flight"}:
            dispatcher.utter_message(
                text=(
                    "Please choose one of the transport cards "
                    "shown in the recommendations."
                ),
            )

            return [FollowupAction("action_listen")]

        selected_hotel_name = tracker.get_slot(
            "selected_hotel_name"
        )

        if selected_hotel_name:
            plan_context = build_selected_plan_context(
                tracker,
                selected_mode=selected_mode,
                selected_hotel_name=selected_hotel_name,
            )

            if (
                plan_context["selected_option"]
                and plan_context["selected_hotel"]
            ):
                dispatcher.utter_message(
                    text=selected_plan_review_text(
                        plan_context
                    ),
                    buttons=selected_plan_buttons(),
                )

                return [
                    SlotSet(
                        "selected_transport_mode",
                        selected_mode,
                    ),
                    SlotSet("fallback_count", 0),
                    FollowupAction("action_listen"),
                ]

        dispatcher.utter_message(
            text=(
                f"Selected transport: {selected_mode}\n\n"
                "Now choose one of the eco hotel cards to build "
                "your final trip plan."
            )
        )

        return [
            SlotSet("selected_transport_mode", selected_mode),
            SlotSet("selected_hotel_name", None),
            SlotSet("fallback_count", 0),
            FollowupAction("action_listen"),
        ]

class ActionSelectHotelOption(Action):

    def name(self) -> Text:
        return "action_select_hotel_option"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        selected_mode = tracker.get_slot("selected_transport_mode")

        if not selected_mode:
            dispatcher.utter_message(
                text=(
                    "Please choose a transport card first. "
                    "After that, choose one of the eco hotel cards."
                )
            )

            return [FollowupAction("action_listen")]

        selected_hotel_name = latest_entity_value(
            tracker,
            "selected_hotel_name",
        )

        plan_context = build_selected_plan_context(
            tracker,
            selected_mode=selected_mode,
            selected_hotel_name=selected_hotel_name,
        )

        selected_hotel = plan_context["selected_hotel"]
        selected_option = plan_context["selected_option"]

        if not selected_hotel:
            dispatcher.utter_message(
                text=(
                    "I could not match that hotel with the current "
                    "recommendation list. Please choose one of the "
                    "hotel cards shown in the results."
                )
            )

            return [FollowupAction("action_listen")]

        if not selected_option:
            dispatcher.utter_message(
                text=(
                    "I could not rebuild the selected transport plan. "
                    "Please choose a transport card again."
                )
            )

            return [
                SlotSet("selected_transport_mode", None),
                FollowupAction("action_listen"),
            ]

        dispatcher.utter_message(
            text=selected_plan_review_text(plan_context),
            buttons=selected_plan_buttons(),
        )

        return [
            SlotSet("selected_hotel_name", selected_hotel["name"]),
            SlotSet("fallback_count", 0),
            FollowupAction("action_listen"),
        ]


class ActionConfirmSelectedPlan(Action):

    def name(self) -> Text:
        return "action_confirm_selected_plan"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        plan_context = build_selected_plan_context(tracker)

        if not plan_context["selected_option"]:
            dispatcher.utter_message(
                text=(
                    "Please choose a transport card before confirming "
                    "the selected plan."
                )
            )

            return [FollowupAction("action_listen")]

        if not plan_context["selected_hotel"]:
            dispatcher.utter_message(
                text=(
                    "Please choose an eco hotel card before confirming "
                    "the selected plan."
                )
            )

            return [FollowupAction("action_listen")]

        dispatcher.utter_message(
            text=selected_plan_final_text(plan_context),
            buttons=[
                {
                    "title": "Change trip details",
                    "payload": "/change_trip_detail",
                },
                {
                    "title": "Prepare advisor summary",
                    "payload": "/request_human_advisor",
                },
                {
                    "title": "Finish",
                    "payload": "/goodbye",
                },
            ],
        )

        return [
            SlotSet("fallback_count", 0),
            FollowupAction("action_listen"),
        ]

def human_readable_command(value: Any) -> str:
    text = str(value or "").strip()

    if not text.startswith("/"):
        return text

    command_labels = {
        "/plan_trip": "Plan a trip",
        "/request_recommendations": "Show recommendations",
        "/request_human_advisor": "Prepare advisor summary",
        "/affirm": "Confirm",
        "/deny": "Change or re-enter value",
    }

    if text in command_labels:
        return command_labels[text]

    detail_match = re.search(
        r'"detail_to_change"\s*:\s*"([^"]+)"',
        text,
    )

    if detail_match:
        detail_name = detail_match.group(1)
        detail_label = DETAIL_LABELS.get(
            detail_name,
            detail_name.replace("_", " ").title(),
        )

        return f"Change trip detail: {detail_label}"

    destination_match = re.search(
        r'"destination"\s*:\s*"([^"]+)"',
        text,
    )

    if destination_match:
        return (
            f"Destination: {destination_match.group(1)}"
        )

    preference_match = re.search(
        r'"sustainability_level"\s*:\s*"([^"]+)"',
        text,
    )

    transport_match = re.search(
        r'"selected_transport_mode"\s*:\s*"([^"]+)"',
        text,
    )

    if transport_match:
        return (
            "Selected transport option: "
            f"{transport_match.group(1)}"
        )

    if preference_match:
        return (
            "Sustainability preference: "
            f"{preference_match.group(1)}"
        )

    return text

def build_conversation_history(
    tracker: Tracker,
) -> List[Dict[str, str]]:

    history_items = []

    for event in tracker.events:
        event_type = event.get("event")

        if event_type == "restart":
            history_items = []
            continue

        if event_type == "user":
            message = human_readable_command(
                event.get("text", "")
            )
            speaker = "User"

        elif event_type == "bot":
            message = str(
                event.get("text", "") or ""
            ).strip()
            speaker = "Bot"

        else:
            continue

        if message:
            history_items.append(
                {
                    "speaker": speaker,
                    "message": message,
                }
            )

    return history_items

class ActionDefaultFallback(Action):

    def name(self) -> Text:
        return "action_default_fallback"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        if tracker.get_slot("handover_requested"):
            dispatcher.utter_message(
                text=(
                    "Simulated advisor handover is already prepared. "
                    "The conversation is paused in this prototype."
                )
            )

            return [FollowupAction("action_listen")]

        current_count = (
            tracker.get_slot("fallback_count") or 0
        )
        next_count = current_count + 1

        if next_count < 2:
            dispatcher.utter_message(
                text=(
                    "I am not fully sure what you mean yet. "
                    "Please choose one of these options so I can "
                    "recover the conversation."
                ),
                buttons=[
                    {
                        "title": "Continue trip planning",
                        "payload": "/plan_trip",
                    },
                    {
                        "title": "Show recommendations",
                        "payload": "/request_recommendations",
                    },
                    {
                        "title": "Prepare advisor summary",
                        "payload": "/request_human_advisor",
                    },
                ],
            )

            return [
                SlotSet("fallback_count", next_count),
                FollowupAction("action_listen"),
            ]

        dispatcher.utter_message(
            text=(
                "I still cannot confidently understand the "
                "request, so I am escalating this conversation "
                "to a human travel advisor."
            )
        )

        return ActionHumanHandover().run(
            dispatcher,
            tracker,
            domain,
        )

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-4o-mini"
OPENROUTER_TIMEOUT_SECONDS = 6


def build_openrouter_advisor_summary(
    context: Dict[Text, Any],
    history_items: List[Dict[Text, Text]],
    latest_user_message: Text,
):
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        return None

    context_text = "\n".join(
        f"- {key}: {value}"
        for key, value in context.items()
    )

    recent_history = history_items[-10:]

    history_text = "\n".join(
        f"{item.get('speaker', 'Message')}: {item.get('message', '')}"
        for item in recent_history
    )

    prompt = (
        "Create a concise handover summary for a human sustainable travel advisor.\n"
        "Use only the provided trip context and conversation history.\n"
        "Do not invent facts, do not request sensitive personal data, and do not make medical, legal, or financial claims.\n"
        "Return 3 short bullet points: user goal, known trip details, and advisor attention points.\n\n"
        f"Trip context:\n{context_text}\n\n"
        f"Latest user request:\n{latest_user_message}\n\n"
        f"Recent conversation:\n{history_text}"
    )

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You summarise chatbot handovers for sustainable travel advisors.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.2,
        "max_tokens": 180,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://colab.research.google.com",
        "X-Title": "Eco Travel Advisor",
    }

    try:
        response = requests.post(
            OPENROUTER_CHAT_URL,
            json=payload,
            headers=headers,
            timeout=OPENROUTER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        data = response.json()
        summary = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        return summary or None

    except Exception:
        return None

class ActionHumanHandover(Action):

    def name(self) -> Text:
        return "action_human_handover"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        if tracker.get_slot("handover_requested"):
            dispatcher.utter_message(
                text=(
                    "Simulated advisor handover is already prepared. "
                    "No additional summary is needed."
                )
            )

            return [FollowupAction("action_listen")]

        latest_user_message = human_readable_command(
            tracker.latest_message.get("text", "")
        )

        latest_intent = tracker.latest_message.get(
            "intent",
            {},
        ).get("name", "")

        if latest_intent in {
            "nlu_fallback",
            "out_of_scope",
        }:
            latest_user_message = (
                "Unrecognised message that triggered escalation: "
                f'"{latest_user_message}"'
            )

        budget_value = safe_float(
            tracker.get_slot("budget"),
            0,
        )

        budget_display = (
            f"€{budget_value:.0f}"
            if budget_value > 0
            else "Not provided"
        )

        context = {
            "Starting city": (
                tracker.get_slot("origin") or "Not provided"
            ),
            "Destination": (
                tracker.get_slot("destination")
                or "Not provided"
            ),
            "Trip type": (
                trip_type_label(tracker.get_slot("trip_type"))
                if tracker.get_slot("trip_type")
                else "Not provided"
            ),
            "Departure date": (
                tracker.get_slot("departure_date")
                or "Not provided"
            ),
            "Return date": (
                tracker.get_slot("return_date")
                or "Not provided"
            ),
            "Budget": budget_display,
            "Sustainability priority": (
                tracker.get_slot("sustainability_level")
                or "Not provided"
            ),
        }

        history_items = build_conversation_history(tracker)

        history_text = "\n".join(
            (
                f"{index}. {item['speaker']}: "
                + re.sub(
                    r"\s*\n\s*",
                    " / ",
                    item["message"],
                )
            )
            for index, item in enumerate(
                history_items,
                start=1,
            )
        )

        if not history_text:
            history_text = (
                "No conversational messages were available."
            )

        privacy_note = (
            "Only information needed to support this trip "
            "should be shared with the advisor. Sensitive "
            "personal data should not be requested unless "
            "it is necessary."
        )

        context_text = "\n".join(
            f"- {label}: {value}"
            for label, value in context.items()
        )

        advisor_summary = build_openrouter_advisor_summary(
            context=context,
            history_items=history_items,
            latest_user_message=latest_user_message
            or "Not available",
        )

        advisor_summary_text = (
            "\n\nAdvisor summary generated by OpenRouter:\n"
            f"{advisor_summary}"
            if advisor_summary
            else ""
        )

        dispatcher.utter_message(
            text=(
                "Simulated advisor handover is now prepared.\n\n"
                "Trip context for the advisor:\n"
                f"{context_text}"
                f"{advisor_summary_text}\n\n"
                "Conversation history:\n"
                f"{history_text}\n\n"
                f"Privacy note: {privacy_note}"
            ),
            json_message={
                "type": "human_handover",
                "status": "active",
                "latest_user_request": (
                    latest_user_message
                    or "Not available"
                ),
                "context": context,
                "conversation_history": history_items,
                "privacy_note": privacy_note,
                "advisor_summary": (
                    advisor_summary
                    or "Not available"
                ),
            },
        )

        return [
            SlotSet("handover_requested", True),
            SlotSet("editing_trip_detail", None),
            SlotSet("awaiting_detail_confirmation", False),
            SlotSet("awaiting_trip_confirmation", False),
            SlotSet("fallback_count", 0),
            FollowupAction("action_listen"),
        ]
