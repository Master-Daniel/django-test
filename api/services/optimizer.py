"""
Compute fuel stop locations along the route (every REFUEL_AT_MILES) and choose
cost-effective stations from fuel price data.
"""
from django.conf import settings

from .fuel import find_cheapest_fuel_near


def _interpolate_point(coords_with_distance, target_miles):
    """Return (lon, lat) on route at target_miles. coords_with_distance: list of (lon, lat, cum_miles)."""
    if not coords_with_distance:
        return None, None
    if target_miles <= 0:
        return coords_with_distance[0][0], coords_with_distance[0][1]
    total = coords_with_distance[-1][2]
    if target_miles >= total:
        return coords_with_distance[-1][0], coords_with_distance[-1][1]
    for i, (lon, lat, cum) in enumerate(coords_with_distance):
        if cum >= target_miles:
            if i == 0:
                return lon, lat
            plon, plat, pcum = coords_with_distance[i - 1]
            t = (target_miles - pcum) / (cum - pcum) if cum > pcum else 1
            return plon + t * (lon - plon), plat + t * (lat - plat)
    return coords_with_distance[-1][0], coords_with_distance[-1][1]


def compute_fuel_stops(coords_with_distance, total_distance_miles):
    """
    Determine refuel points every REFUEL_AT_MILES and assign cheapest nearby station.
    Returns list of dicts: { lat, lon, price_per_gallon, name, gallons, cost, miles_to_next }.
    """
    refuel_at = getattr(settings, 'REFUEL_AT_MILES', 400)
    mpg = getattr(settings, 'MILES_PER_GALLON', 10)
    stops = []
    next_stop_miles = refuel_at
    while next_stop_miles < total_distance_miles:
        lon, lat = _interpolate_point(coords_with_distance, next_stop_miles)
        station = find_cheapest_fuel_near(lat, lon)
        if station is None:
            # No fuel data: use route point and assume a default price for display
            station = {
                'lat': lat, 'lon': lon, 'price_per_gallon': 0.0,
                'name': 'No fuel data near this point',
            }
        miles_to_next = min(refuel_at, total_distance_miles - next_stop_miles)
        gallons = miles_to_next / mpg
        cost = gallons * station['price_per_gallon'] if station['price_per_gallon'] else 0
        stops.append({
            'lat': station['lat'],
            'lon': station['lon'],
            'price_per_gallon': station['price_per_gallon'],
            'name': station['name'],
            'gallons': round(gallons, 2),
            'cost': round(cost, 2),
            'miles_to_next': round(miles_to_next, 1),
            'route_position_miles': round(next_stop_miles, 1),
        })
        next_stop_miles += refuel_at
    return stops


def total_fuel_cost(stops, total_distance_miles):
    """Total cost from stops plus any remaining segment if last stop doesn't cover end."""
    mpg = getattr(settings, 'MILES_PER_GALLON', 10)
    refuel_at = getattr(settings, 'REFUEL_AT_MILES', 400)
    total = sum(s['cost'] for s in stops)
    # Last segment: from last refuel to destination
    if stops:
        last_pos = stops[-1]['route_position_miles']
        remaining = total_distance_miles - last_pos - stops[-1]['miles_to_next']
    else:
        remaining = total_distance_miles
    if remaining > 0:
        # Need to refuel at start or we have no stops - add cost for remaining miles at first available price
        # For simplicity: add (remaining/mpg) * avg_price. If no stops, we need one "virtual" fill at start.
        if stops:
            avg_price = sum(s['price_per_gallon'] for s in stops) / len(stops)
        else:
            avg_price = 0
        total += (remaining / mpg) * avg_price
    return round(total, 2)
