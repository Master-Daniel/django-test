"""
API view: one endpoint that returns route map, optimal fuel stops, and total fuel cost.
"""
import json
from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .services import get_route_geometry_and_coords, load_fuel_prices, compute_fuel_stops


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_http_methods(['GET', 'POST']), name='dispatch')
class RouteFuelView(View):
    """
    GET or POST with: start_lat, start_lon, end_lat, end_lon (all required).
    Returns: route (GeoJSON), fuel_stops, total_distance_miles, total_fuel_cost_usd.
    """

    def get_params(self, request):
        if request.method == 'POST':
            try:
                body = json.loads(request.body) if request.body else {}
            except json.JSONDecodeError:
                body = {}
            return {
                'start_lat': body.get('start_lat'),
                'start_lon': body.get('start_lon'),
                'end_lat': body.get('end_lat'),
                'end_lon': body.get('end_lon'),
            }
        return {
            'start_lat': request.GET.get('start_lat'),
            'start_lon': request.GET.get('start_lon'),
            'end_lat': request.GET.get('end_lat'),
            'end_lon': request.GET.get('end_lon'),
        }

    def get(self, request):
        return self.respond(request)

    def post(self, request):
        return self.respond(request)

    def respond(self, request):
        p = self.get_params(request)
        for key in ('start_lat', 'start_lon', 'end_lat', 'end_lon'):
            val = p.get(key)
            if val is None or val == '':
                return JsonResponse(
                    {'error': f'Missing required parameter: {key}. Use start_lat, start_lon, end_lat, end_lon (USA coordinates).'},
                    status=400,
                )
        try:
            start_lat = float(p['start_lat'])
            start_lon = float(p['start_lon'])
            end_lat = float(p['end_lat'])
            end_lon = float(p['end_lon'])
        except (TypeError, ValueError):
            return JsonResponse(
                {'error': 'start_lat, start_lon, end_lat, end_lon must be numbers.'},
                status=400,
            )
        # Basic USA bounds (continental + rough)
        if not (24 <= start_lat <= 50 and -125 <= start_lon <= -66) or not (24 <= end_lat <= 50 and -125 <= end_lon <= -66):
            return JsonResponse(
                {'error': 'Start and finish must be within the USA (approx. lat 24–50, lon -125 to -66).'},
                status=400,
            )
        try:
            route_data = get_route_geometry_and_coords(start_lon, start_lat, end_lon, end_lat)
        except Exception as e:
            return JsonResponse(
                {'error': f'Routing failed: {str(e)}'},
                status=502,
            )
        total_distance_miles = route_data['total_distance_miles']
        coords_with_distance = route_data['coords_with_distance']
        fuel_stops = compute_fuel_stops(coords_with_distance, total_distance_miles)
        # If trip is short (no stops), still report fuel cost: one "fill" at start for full trip
        mpg = getattr(settings, 'MILES_PER_GALLON', 10)
        if total_distance_miles > 0 and not fuel_stops:
            from .services.fuel import find_cheapest_fuel_near
            station = find_cheapest_fuel_near(start_lat, start_lon)
            if station:
                gallons = total_distance_miles / mpg
                total_fuel_cost_usd = round(gallons * station['price_per_gallon'], 2)
                fuel_stops = [{
                    'lat': station['lat'], 'lon': station['lon'],
                    'price_per_gallon': station['price_per_gallon'], 'name': station['name'],
                    'gallons': round(gallons, 2), 'cost': total_fuel_cost_usd,
                    'miles_to_next': round(total_distance_miles, 1), 'route_position_miles': 0,
                }]
            else:
                total_fuel_cost_usd = 0.0
        else:
            total_fuel_cost_usd = round(sum(s['cost'] for s in fuel_stops), 2)
        # Always return route path with explicit latitude/longitude objects.
        route_coordinates = [
            {'latitude': lat, 'longitude': lon}
            for lon, lat, _ in coords_with_distance
        ]
        # Human-friendly fuel stop keys for API consumers.
        response_fuel_stops = [
            {
                'latitude': s['lat'],
                'longitude': s['lon'],
                'price_per_gallon': s['price_per_gallon'],
                'name': s['name'],
                'gallons': s['gallons'],
                'cost': s['cost'],
                'miles_to_next': s['miles_to_next'],
                'route_position_miles': s['route_position_miles'],
            }
            for s in fuel_stops
        ]
        return JsonResponse({
            'map_routes': route_coordinates,
            'route_summary': {
                'total_distance_miles': round(total_distance_miles, 2),
                'total_fuel_cost_usd': total_fuel_cost_usd,
                'miles_per_gallon': mpg,
                'vehicle_range_miles': getattr(settings, 'VEHICLE_RANGE_MILES', 500),
            },
            'fuel_stops': response_fuel_stops,
        })
