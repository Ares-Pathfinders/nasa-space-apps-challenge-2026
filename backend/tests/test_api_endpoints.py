"""
Integration test for ARES-Nav HTTP REST API endpoints.
Tests:
- GET /api/health
- GET /api/sites
- GET /api/rover-photos
- GET /api/terrain (Gale & Jezero)
- POST /api/pathfinding/simulate
"""

import sys
import requests

BASE_URL = "http://localhost:8000"

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

    # 3. Dynamic Terrain for Gale Crater
    r = requests.get(f"{BASE_URL}/api/terrain?zone=gale&resolution=40&max_slope=15.0", timeout=8)
    assert r.status_code == 200
    gale_data = r.json()
    print(f"[OK] GET /api/terrain (Gale Crater) -> {len(gale_data.get('cells', []))} cells, Route waypoints: {gale_data.get('safe_route', {}).get('num_waypoints')}")

    # 4. Dynamic Terrain for Jezero Crater
    r = requests.get(f"{BASE_URL}/api/terrain?zone=jezero&resolution=40&max_slope=15.0", timeout=8)
    assert r.status_code == 200
    jezero_data = r.json()
    print(f"[OK] GET /api/terrain (Jezero Crater) -> {len(jezero_data.get('cells', []))} cells, Route waypoints: {jezero_data.get('safe_route', {}).get('num_waypoints')}")

    # 5. Pathfinding Simulation
    payload = {
        "site_id": "mount-sharp-boxwork",
        "start": {"latitude": -4.596, "longitude": 137.488},
        "target": {"latitude": -4.716, "longitude": 137.397}
    }
    r = requests.post(f"{BASE_URL}/api/pathfinding/simulate", json=payload, timeout=8)
    assert r.status_code == 200
    route = r.json()
    print(f"[OK] POST /api/pathfinding/simulate -> Distance: {route.get('total_distance_m')}m | Risk: {route.get('risk_level')} | Max slope: {route.get('max_slope_deg')}°")

    print("\n>> ALL LIVE API TESTS PASSED SUCCESSFULLY!\n")

if __name__ == "__main__":
    try:
        test_api()
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Server is not running on {BASE_URL}.")
        print("Please run 'python backend/server.py 8000' or execute 'start_server.bat' first!\n")
        sys.exit(1)
