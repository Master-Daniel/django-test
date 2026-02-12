"""
Load fuel prices from CSV and find cheapest station near a (lat, lon).
CSV format: lat,lon,price_per_gallon,name (or state,city,lat,lon,price_per_gallon,name)
"""
import csv
import math
from pathlib import Path

from django.conf import settings

# In-memory cache: list of (lat, lon, price, name)
_fuel_cache = None

# Search radius in miles when finding "nearby" stations
SEARCH_RADIUS_MILES = 35


def _haversine_miles(lat1, lon1, lat2, lon2):
    R = 3959
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def load_fuel_prices():
    """Load fuel stations from CSV; return list of dicts with lat, lon, price_per_gallon, name."""
    global _fuel_cache
    if _fuel_cache is not None:
        return _fuel_cache
    path = getattr(settings, 'FUEL_PRICES_CSV', None) or Path(settings.BASE_DIR) / 'data' / 'fuel_prices.csv'
    if not path.exists():
        _fuel_cache = []
        return _fuel_cache
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            _fuel_cache = []
            return _fuel_cache
        # Support: lat,lon,price_per_gallon,name  OR  state,city,lat,lon,price_per_gallon,name
        for row in reader:
            if len(row) < 4:
                continue
            try:
                if header[0].lower().strip() in ('state', 'state_code'):
                    # state,city,lat,lon,price,name
                    state, city, lat, lon, price = row[0], row[1], float(row[2]), float(row[3]), float(row[4])
                    name = row[5] if len(row) > 5 else f"{city}, {state}"
                else:
                    lat, lon = float(row[0]), float(row[1])
                    price = float(row[2])
                    name = row[3] if len(row) > 3 else f"{lat:.4f}, {lon:.4f}"
                rows.append({'lat': lat, 'lon': lon, 'price_per_gallon': price, 'name': name})
            except (ValueError, IndexError):
                continue
    _fuel_cache = rows
    return _fuel_cache


def find_cheapest_fuel_near(lat, lon, radius_miles=SEARCH_RADIUS_MILES):
    """
    Return the cheapest fuel station within radius_miles of (lat, lon).
    Returns dict with lat, lon, price_per_gallon, name or None if none found.
    """
    stations = load_fuel_prices()
    if not stations:
        return None
    best = None
    best_price = float('inf')
    for s in stations:
        d = _haversine_miles(lat, lon, s['lat'], s['lon'])
        if d <= radius_miles and s['price_per_gallon'] < best_price:
            best_price = s['price_per_gallon']
            best = s
    return best
