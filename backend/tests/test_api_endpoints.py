"""
Integration test for ARES-Nav HTTP REST API endpoints.
Tests:
- GET /api/health
- GET /api/sites
- GET /api/atmosphere/zones/{zone_id}
- GET /api/rover-photos
- GET /api/terrain (Gale & Jezero)
- POST /api/pathfinding/simulate for Gale and Jezero
"""

import sys
import os
import requests

BASE_URL = os.environ.get("ARES_NAV_BASE_URL", "http://localhost:8000")

def test_api():
    print("\n" + "=" * 60)
    print("TEST SUITE: ARES-Nav Live HTTP API Endpoints")
    print("=" * 60)

    # 1. Health
    r = requests.get(f"{BASE_URL}/api/health", timeout=3)
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    health = r.json()
    print(f"[OK] GET /api/health -> Status: {health.get('status')} | Version: {health.get('version')} | Nodes: {health.get('cell_graph_nodes')}")

    # 2. Sites
    r = requests.get(f"{BASE_URL}/api/sites", timeout=3)
    assert r.status_code == 200
    sites = r.json()
    print(f"[OK] GET /api/sites -> {len(sites)} sites loaded ({', '.join([s['id'] for s in sites])})")

    # 3. Atmospheric data used by the gases map
    r = requests.get(f"{BASE_URL}/api/atmosphere/zones/mount-sharp-gale-crater", timeout=3)
    assert r.status_code == 200
    assert r.json()["zone_id"] == "mount-sharp-gale-crater"
    print("[OK] GET /api/atmosphere/zones/{zone_id} -> regional gas data loaded")

    # 4. Dynamic Terrain for Gale Crater
    r = requests.get(f"{BASE_URL}/api/terrain?zone=gale&resolution=40&max_slope=15.0", timeout=8)
    assert r.status_code == 200
    gale_data = r.json()
    print(f"[OK] GET /api/terrain (Gale Crater) -> {len(gale_data.get('grid', {}).get('passable', []))} cells, Route waypoints: {gale_data.get('safe_route', {}).get('num_waypoints')}")

    # 5. Dynamic Terrain for Jezero Crater
    r = requests.get(f"{BASE_URL}/api/terrain?zone=jezero&resolution=40&max_slope=15.0", timeout=8)
    assert r.status_code == 200
    jezero_data = r.json()
    print(f"[OK] GET /api/terrain (Jezero Crater) -> {len(jezero_data.get('grid', {}).get('passable', []))} cells, Route waypoints: {jezero_data.get('safe_route', {}).get('num_waypoints')}")

    # 6. Pathfinding Simulation
    payload = {
        "site_id": "mount-sharp-boxwork",
        "start": {"latitude": -4.596, "longitude": 137.488},
        "target": {"latitude": -4.716, "longitude": 137.397}
    }
    r = requests.post(f"{BASE_URL}/api/pathfinding/simulate", json=payload, timeout=8)
    assert r.status_code == 200
    route = r.json()
    print(f"[OK] POST /api/pathfinding/simulate -> Distance: {route.get('total_distance_m')}m | Risk: {route.get('risk_level')} | Max slope: {route.get('max_slope_deg')}°")

    # 7. User-selected route over Jezero terrain
    jezero_route = jezero_data["safe_route"]["coordinates_lon_lat_elev"]
    jezero_payload = {
        "zone": "jezero",
        "resolution": 40,
        "max_slope": 15.0,
        "start": {"latitude": jezero_route[0][1], "longitude": jezero_route[0][0]},
        "target": {"latitude": jezero_route[-1][1], "longitude": jezero_route[-1][0]},
    }
    r = requests.post(f"{BASE_URL}/api/pathfinding/simulate", json=jezero_payload, timeout=8)
    assert r.status_code == 200, f"Jezero route failed: {r.status_code} {r.text}"
    selected_route = r.json()
    assert selected_route["zone"] == "jezero"
    assert len(selected_route["waypoints"]) >= 2
    assert all(point["slope_deg"] <= jezero_payload["max_slope"] for point in selected_route["waypoints"])
    print(f"[OK] POST /api/pathfinding/simulate (Jezero) -> Distance: {selected_route['total_distance_m']}m")

    # 8. Coordinates outside the expedition bounds are rejected, not clamped.
    outside_payload = {
        "zone": "jezero",
        "resolution": 40,
        "max_slope": 15.0,
        "start": {"latitude": 30.0, "longitude": 77.5},
        "target": jezero_payload["target"],
    }
    r = requests.post(f"{BASE_URL}/api/pathfinding/simulate", json=outside_payload, timeout=8)
    assert r.status_code == 400, f"Out-of-bounds route should be rejected: {r.status_code}"
    print("[OK] POST /api/pathfinding/simulate rejects out-of-bounds coordinates")

    print("\n>> ALL LIVE API TESTS PASSED SUCCESSFULLY!\n")

if __name__ == "__main__":
    try:
        test_api()
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Server is not running on {BASE_URL}.")
        print("Please run 'python backend/server.py 8000' or execute 'start_server.bat' first!\n")
        sys.exit(1)
