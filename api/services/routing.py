"""
Single-call routing via OSRM (public demo server).
Returns route geometry and coordinates with cumulative distances for fuel-stop placement.
"""
import math
import requests
from django.conf import settings


def _haversine_miles(lon1, lat1, lon2, lat2):
    """Return distance in miles between two (lon, lat) points."""
    R = 3959  # Earth radius miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_route_geometry_and_coords(start_lon, start_lat, end_lon, end_lat):
    """
    Call OSRM once; return route as GeoJSON geometry and a list of (lon, lat, cumulative_distance_miles).
    Raises ValueError if no route or API error.
    """
    url = (
        f"{settings.OSRM_BASE_URL}/route/v1/driving/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
    )
    params = {
        'overview': 'full',
        'geometries': 'geojson',
        'steps': 'true',
    }
    headers = {'User-Agent': 'RouteFuelAPI/1.0 (Django; non-commercial)'}
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get('code') != 'Ok' or not data.get('routes'):
        raise ValueError('No route found between the given locations.')
    route = data['routes'][0]
    geometry = route.get('geometry') or {}
    coords = list(geometry.get('coordinates') or [])
    # OSRM may not return top-level geometry; assemble from legs/steps
    if not coords:
        for leg in route.get('legs', []):
            for step in leg.get('steps', []):
                step_coords = (step.get('geometry') or {}).get('coordinates') or []
                for c in step_coords:
                    coords.append(c)
        if coords:
            geometry = {'type': 'LineString', 'coordinates': coords}
    # Build (lon, lat, cumulative_distance_miles) from geometry using haversine between points
    coords_with_dist = []
    cum_miles = 0.0
    for i, (lon, lat) in enumerate(coords):
        coords_with_dist.append((lon, lat, cum_miles))
        if i < len(coords) - 1:
            nlon, nlat = coords[i + 1]
            cum_miles += _haversine_miles(lon, lat, nlon, nlat)
    total_miles = (route.get('distance') or 0) / 1609.344  # OSRM distance in meters
    if coords_with_dist:
        coords_with_dist[-1] = (coords_with_dist[-1][0], coords_with_dist[-1][1], total_miles)
    return {
        'geometry': geometry,
        'coords_with_distance': coords_with_dist,
        'total_distance_miles': total_miles,
    }
