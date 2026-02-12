# Route Fuel API

Django API that returns a route map between two USA locations, **optimal (cost-effective) fuel stop locations** along the route, and **total fuel cost**. The vehicle is assumed to have a **500-mile range** and **10 MPG**; refuels are planned every 400 miles with the cheapest fuel near that segment.

## Requirements

- Python 3.10+
- Django 5.x
- `requests`

## Setup

```bash
cd "Django Test"
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

## Run

```bash
python manage.py runserver
```

API base: `http://127.0.0.1:8000/api/`

## API Endpoint

**`GET` or `POST` `/api/route/`**

- **Parameters:** `start_lat`, `start_lon`, `end_lat`, `end_lon` (all required; USA coordinates).
- **Response:**
  - **`map`** – GeoJSON `FeatureCollection`: route line + fuel stop points (for rendering a map).
  - **`fuel_stops`** – List of optimal fuel stops (lat, lon, price, gallons, cost, etc.).
  - **`route_summary`** – `total_distance_miles`, `total_fuel_cost_usd`, `miles_per_gallon`, `vehicle_range_miles`.

### Example (GET)

```
GET http://127.0.0.1:8000/api/route/?start_lat=37.77&start_lon=-122.42&end_lat=41.88&end_lon=-87.63
```

### Example (POST, JSON body)

```json
{
  "start_lat": 37.77,
  "start_lon": -122.42,
  "end_lat": 41.88,
  "end_lon": -87.63
}
```

## Map & Routing

- **Routing:** One call to **OSRM** (public demo: `router.project-osrm.org`) to get the full route and geometry. No API key required; use a single request per route.
- **Map:** The response `map` field is standard GeoJSON you can draw in any map library (Leaflet, Mapbox, etc.).

## Fuel Prices

- Fuel prices are read from **`data/fuel_prices.csv`**.
- **CSV format (with header):**  
  `state,city,lat,lon,price_per_gallon,name`  
  or: `lat,lon,price_per_gallon,name`
- Replace or edit `data/fuel_prices.csv` with your own list of fuel prices. A sample file with USA cities is included.

## Design Notes

- **Speed:** One OSRM request per route; fuel data is loaded once and cached in memory.
- **Optimal fuel:** For each planned refuel (every 400 miles), the code picks the **cheapest** station within ~35 miles of that point on the route.
- **Vehicle:** 500-mile range, refuel at 400 miles, 10 MPG (configurable in `config/settings.py`).

## Loom / Postman

Use Postman (or similar) to call `GET` or `POST` `/api/route/` with the parameters above and show the JSON response (map GeoJSON, fuel_stops, total_fuel_cost_usd). Record a short (≤5 min) Loom walking through the request and a quick code overview.
