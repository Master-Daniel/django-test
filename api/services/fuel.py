"""
Fast fuel-price lookup service.

Supports:
1) lat,lon,price_per_gallon,name
2) state,city,lat,lon,price_per_gallon,name
3) assessment file:
   OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price

Performance note:
- No live geocoding in request path (to keep API latency low).
- If `data/geocode_cache.json` exists, cached city/state coordinates are used.
"""
import csv
import json
import math
from pathlib import Path

from django.conf import settings

_fuel_cache = None
_geocode_cache = None
_cheapest_station = None

SEARCH_RADIUS_MILES = 35
GEOCODE_CACHE_FILE = "geocode_cache.json"


def _haversine_miles(lat1, lon1, lat2, lon2):
    R = 3959
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _normalize_state(state):
    return (state or "").strip().upper()


def _city_state_key(city, state):
    return f"{(city or '').strip().lower()}|{_normalize_state(state)}"


def _load_geocode_cache():
    global _geocode_cache
    if _geocode_cache is not None:
        return _geocode_cache
    path = Path(settings.BASE_DIR) / "data" / GEOCODE_CACHE_FILE
    if not path.exists():
        _geocode_cache = {}
        return _geocode_cache
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        _geocode_cache = data if isinstance(data, dict) else {}
    except Exception:
        _geocode_cache = {}
    return _geocode_cache


def load_fuel_prices():
    """
    Load stations from CSV and return a city/state-deduped list with best (lowest) price.
    """
    global _fuel_cache, _cheapest_station
    if _fuel_cache is not None:
        return _fuel_cache
    path = getattr(settings, "FUEL_PRICES_CSV", None) or Path(settings.BASE_DIR) / "data" / "fuel-prices-for-be-assessment.csv"
    if not path.exists():
        _fuel_cache = []
        return _fuel_cache

    geocode_cache = _load_geocode_cache()
    best_by_city_state = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = [h.strip().lower() for h in (reader.fieldnames or [])]
        is_assessment = "retail price" in headers and "city" in headers and "state" in headers
        for row in reader:
            try:
                if is_assessment:
                    city = (row.get("City") or "").strip()
                    state = _normalize_state(row.get("State"))
                    price = float(row.get("Retail Price"))
                    name = (row.get("Truckstop Name") or "").strip() or f"{city}, {state}"
                    address = (row.get("Address") or "").strip()
                    key = _city_state_key(city, state)
                    geo = geocode_cache.get(key)
                    lat = geo.get("lat") if isinstance(geo, dict) else None
                    lon = geo.get("lon") if isinstance(geo, dict) else None
                else:
                    # Existing formats.
                    if "state" in headers and "city" in headers and "lat" in headers and "lon" in headers:
                        city = (row.get("city") or "").strip()
                        state = _normalize_state(row.get("state"))
                        lat = float(row.get("lat"))
                        lon = float(row.get("lon"))
                        price = float(row.get("price_per_gallon"))
                        name = (row.get("name") or "").strip() or f"{city}, {state}"
                        address = ""
                    else:
                        lat = float(row.get("lat"))
                        lon = float(row.get("lon"))
                        price = float(row.get("price_per_gallon"))
                        city = ""
                        state = ""
                        name = (row.get("name") or "").strip() or f"{lat:.4f}, {lon:.4f}"
                        address = ""
            except Exception:
                continue

            key = _city_state_key(city, state) if city and state else f"coord|{lat}|{lon}"
            existing = best_by_city_state.get(key)
            if existing is None or price < existing["price_per_gallon"]:
                best_by_city_state[key] = {
                    "city": city,
                    "state": state,
                    "lat": lat,
                    "lon": lon,
                    "price_per_gallon": price,
                    "name": name,
                    "address": address,
                }

    _fuel_cache = list(best_by_city_state.values())
    if _fuel_cache:
        _cheapest_station = min(_fuel_cache, key=lambda s: s.get("price_per_gallon", float("inf")))
    else:
        _cheapest_station = None
    return _fuel_cache


def find_cheapest_fuel_near(lat, lon, radius_miles=SEARCH_RADIUS_MILES):
    """
    Return cheapest station within radius from point.
    Fast path only: uses stations that already have coordinates.
    Falls back to overall cheapest station if no geocoded nearby station exists.
    """
    stations = load_fuel_prices()
    if not stations:
        return None

    candidates = [s for s in stations if s.get("lat") is not None and s.get("lon") is not None]
    best = None
    best_price = float("inf")
    for s in candidates:
        d = _haversine_miles(lat, lon, s["lat"], s["lon"])
        if d <= radius_miles and s["price_per_gallon"] < best_price:
            best_price = s["price_per_gallon"]
            best = s

    if best:
        return best

    # Fallback 1: cheapest geocoded station overall
    if candidates:
        return min(candidates, key=lambda s: s.get("price_per_gallon", float("inf")))

    # Fallback 2: cheapest station from full dataset (no coordinates available)
    if _cheapest_station:
        return {
            "lat": lat,
            "lon": lon,
            "price_per_gallon": _cheapest_station.get("price_per_gallon", 0.0),
            "name": _cheapest_station.get("name", "Fallback fuel station"),
            "city": _cheapest_station.get("city", ""),
            "state": _cheapest_station.get("state", ""),
            "address": _cheapest_station.get("address", ""),
        }
    return None
