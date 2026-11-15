"""
ARES-Nav Unified Server.
Provides:
1. REST API endpoints on /api/... (health, sites, rover-photos, pathfinding/simulate, terrain).
2. Static file serving for the React + Three.js frontend (from frontend/dist).
Zero third-party dependencies required; runs directly with standard library Python 3.13.
"""

import os
import sys
import json
import math
import mimetypes
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

# Add repo root to sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.dirname(__file__))

from app.services.psa_service import PSAService
from backend.data.gale_crater_topography import (
    GALE_MAX_LAT,
    GALE_MAX_LON,
    GALE_MIN_LAT,
    GALE_MIN_LON,
    generate_gale_crater_elevation_grid,
)
from backend.data.jezero_crater_topography import (
    JEZERO_MAX_LAT,
    JEZERO_MAX_LON,
    JEZERO_MIN_LAT,
    JEZERO_MIN_LON,
    generate_jezero_crater_elevation_grid,
)
from backend.data.jezero_slope import resample_jezero_slope_to_grid
from backend.data.terrain_errors import TerrainDataError
from backend.terrain.slope import SlopeAnalyzer
from backend.terrain.cell_graph import CellGraphBuilder

FRONTEND_DIST_DIR = os.path.join(REPO_ROOT, "frontend", "dist")
TERRAIN_CACHE_FILE = os.path.join(os.path.dirname(__file__), "terrain_analysis_output.json")
GALE_TERRAIN_SOURCE = {
    "name": "Modelo sintético de terreno de Gale (no DEM medido)",
    "url": "https://mars.nasa.gov/",
    "method": "Topografía procedural demostrativa; no representa mediciones orbitales.",
}
JEZERO_TERRAIN_SOURCE = {
    "name": "Modelo sintético de terreno de Jezero (no DEM medido)",
    "url": "https://mars.nasa.gov/",
    "method": "Topografía procedural demostrativa; no representa mediciones orbitales.",
}


def _nearest_passable_cell(grid, builder, cell, max_radius=2):
    row, col = cell
    for radius in range(max_radius + 1):
        candidates = []
        for candidate_row in range(max(0, row - radius), min(grid.rows, row + radius + 1)):
            for candidate_col in range(max(0, col - radius), min(grid.cols, col + radius + 1)):
                if max(abs(candidate_row - row), abs(candidate_col - col)) != radius:
                    continue
                candidate = (candidate_row, candidate_col)
                if candidate in builder.graph:
                    candidates.append(candidate)
        if candidates:
            return min(
                candidates,
                key=lambda candidate: grid.get_distance_meters(row, col, candidate[0], candidate[1])
            )
    return None


# Preload or initialize Gale Crater terrain graph once on server startup
print("[ARES-Nav Server] Initializing Gale Crater cell graph...")
elevation_grid = generate_gale_crater_elevation_grid(resolution_rows=80, resolution_cols=80)
slope_analyzer = SlopeAnalyzer(elevation_grid, max_slope_deg=15.0)
cell_graph_builder = CellGraphBuilder(elevation_grid, slope_analyzer, slope_penalty_weight=3.5)
print(f"[ARES-Nav Server] Cell graph ready with {cell_graph_builder.graph.number_of_nodes()} navigable nodes.")


EXPLORATION_SITES = [
    {
        "id": "mount-sharp-boxwork",
        "name": "Mount Sharp - Boxwork Formations",
        "region": "Aeolis Mons, Gale Crater",
        "coordinates": {"latitude": -4.589, "longitude": 137.441, "elevation_m": -4500.97},
        "rover_mission": "Curiosity (MSL)",
        "landing_year": 2012,
        "summary": "Prominent central mound in Gale Crater with steep hematite ridges (Vera Rubin Ridge) and ancient freshwater lacustrine mudstone beds.",
        "objectives": [
            {"id": "1", "title": "Vera Rubin Ridge Escarpment Bypass", "category": "Navigation", "priority": "PRIMARY", "description": "Detect and safely circumvent slopes > 15° along hematite scarp."},
            {"id": "2", "title": "Clay-to-Sulfate Transition Layer Profiling", "category": "Paleoclimate", "priority": "PRIMARY", "description": "Inspect contact beds."}
        ],
        "hazards": [
            {"hazard_type": "Steep Escarpment Scarps", "severity": "HIGH", "description": "Terraced cliff edges with slopes > 16.8° at Vera Rubin Ridge and Greenheugh Pediment.", "mitigation": "Follow ARES-Nav cell graph safe corridor standoff."}
        ],
        "environment": {
            "avg_temp_c": -48.0,
            "min_temp_c": -88.0,
            "max_temp_c": -12.0,
            "radiation_mgy_day": 0.23,
            "atmospheric_pressure_pa": 780.0,
            "dust_opacity_tau": 0.65
        },
        "default_sol": 1000,
        "recommended_cameras": ["MAST", "NAV_LEFT_B", "CHEMCAM"],
        "available_layers": ["optical", "elevation", "thermal", "radiation"]
    },
    {
        "id": "jezero-crater-delta",
        "name": "Jezero Crater Delta",
        "region": "Syrtis Major Quadrangle",
        "coordinates": {"latitude": 18.38, "longitude": 77.58, "elevation_m": -2500.0},
        "rover_mission": "Perseverance (Mars 2020)",
        "landing_year": 2021,
        "summary": "Ancient river-lake delta system rich in carbonates, clays, and mudstones with high biosignature preservation potential.",
        "objectives": [
            {"id": "3", "title": "Delta Front Siltstone Sampling", "category": "Astrobiology", "priority": "PRIMARY", "description": "Bottomset siltstone beds for microbial fossils."}
        ],
        "hazards": [
            {"hazard_type": "Fine-Grained Sand Dune Traps", "severity": "HIGH", "description": "Transverse Aeolian Ridges (TARs) with loose silty sand.", "mitigation": "Bypass ripples wider than 2 meters."}
        ],
        "environment": {
            "avg_temp_c": -54.0,
            "min_temp_c": -92.0,
            "max_temp_c": -15.0,
            "radiation_mgy_day": 0.25,
            "atmospheric_pressure_pa": 720.0,
            "dust_opacity_tau": 0.55
        },
        "default_sol": 100,
        "recommended_cameras": ["NAVCAM_LEFT", "MCZ_RIGHT", "SUPERCAM"],
        "available_layers": ["optical", "elevation", "thermal", "radiation"]
    }
]


class AresNavHandler(SimpleHTTPRequestHandler):
    """Handles both REST API calls on /api/... and static UI assets."""

    def end_headers(self):
        # Enable CORS for local dev / client integration
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            self._handle_api_get(path, parse_qs(parsed.query))
        else:
            self._handle_static_get(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/pathfinding/simulate":
            self._handle_pathfinding_simulate()
        else:
            self.send_error(404, "Endpoint not found")

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_api_get(self, path: str, query: dict):
        if path == "/api/health":
            self._send_json({
                "status": "operational",
                "system": "ARES-Nav Mars Engine",
                "version": "1.0.0",
                "cell_graph_nodes": cell_graph_builder.graph.number_of_nodes(),
            })
        elif path == "/api/sites":
            self._send_json(EXPLORATION_SITES)
        elif path.startswith("/api/atmosphere/zones/"):
            zone_id = path.rsplit("/", 1)[-1]
            zone = PSAService.get_zone_by_id(zone_id)
            if zone is None:
                self._send_json({"error": f"Atmospheric zone not found: {zone_id}"}, status=404)
            else:
                self._send_json(json.loads(zone.model_dump_json()))
        elif path == "/api/rover-photos":
            rover = query.get("rover", ["curiosity"])[0]
            sol = int(query.get("sol", [1000])[0])
            self._send_json({
                "rover": rover,
                "sol": sol,
                "total_photos": 4,
                "source": "curated_fallback",
                "photos": [
                    {
                        "id": 1026858,
                        "sol": sol,
                        "camera": {"name": "MAST", "full_name": "Mast Camera"},
                        "img_src": "https://mars.nasa.gov/msl-raw-images/msss/01000/mcam/1000MR0044631300503690E01_DXXX.jpg",
                        "earth_date": "2015-05-31"
                    },
                    {
                        "id": 1026859,
                        "sol": sol,
                        "camera": {"name": "CHEMCAM", "full_name": "Chemistry & Camera Complex"},
                        "img_src": "https://mars.nasa.gov/msl-raw-images/msss/01000/mcam/1000ML0044631290405230E01_DXXX.jpg",
                        "earth_date": "2015-05-31"
                    }
                ]
            })
        elif path == "/api/terrain":
            zone = query.get("zone", ["gale"])[0].lower()
            res = min(100, max(20, int(query.get("resolution", [60])[0])))
            max_slope = float(query.get("max_slope", [15.0])[0])

            if zone == "jezero":
                try:
                    grid = generate_jezero_crater_elevation_grid(resolution_rows=res, resolution_cols=res)
                except TerrainDataError as error:
                    self._send_json({"error": str(error)}, status=503)
                    return
                zone_title = "Jezero Crater Delta (Perseverance / Mars 2020)"
                zone_center = [18.38, 77.55]
                terrain_source = {
                    **JEZERO_TERRAIN_SOURCE,
                    "slope_data": (
                        "Measured 20.2 m HiRISE slope raster used for Jezero routes."
                    ),
                }
                historical_wps = [
                    {"name": "Octavia E. Butler Landing", "lat": 18.4447, "lon": 77.4508, "type": "LANDING"},
                    {"name": "Kodiak Butte (Delta Remnant)", "lat": 18.412, "lon": 77.485, "type": "SCIENCE"},
                    {"name": "Delta Front Escarpment Base", "lat": 18.428, "lon": 77.512, "type": "HAZARD"},
                    {"name": "Neretva Vallis Canyon Inlet", "lat": 18.380, "lon": 77.470, "type": "VALLEY"}
                ]
                start_c = (int(res * 0.2), int(res * 0.2))
                goal_c = (int(res * 0.75), int(res * 0.75))
            else:
                try:
                    grid = generate_gale_crater_elevation_grid(resolution_rows=res, resolution_cols=res)
                except TerrainDataError as error:
                    self._send_json({"error": str(error)}, status=503)
                    return
                zone_title = "Gale Crater - Mount Sharp (Curiosity / MSL)"
                zone_center = [-4.65, 137.43]
                terrain_source = GALE_TERRAIN_SOURCE
                historical_wps = [
                    {"name": "Bradbury Landing (Sol 0)", "lat": -4.5895, "lon": 137.4417, "type": "LANDING"},
                    {"name": "Yellowknife Bay (Mudstone)", "lat": -4.591, "lon": 137.452, "type": "SCIENCE"},
                    {"name": "Dingo Gap (Sand Ripple Pass)", "lat": -4.633, "lon": 137.408, "type": "HAZARD"},
                    {"name": "Vera Rubin Ridge (Hematite Escarpment)", "lat": -4.685, "lon": 137.400, "type": "SCARP"},
                    {"name": "Greenheugh Pediment (Sandstone Cap)", "lat": -4.715, "lon": 137.375, "type": "CLIFF"}
                ]
                start_c = (int(res * 0.2), int(res * 0.8))
                goal_c = (int(res * 0.8), int(res * 0.3))

            slope_deg_matrix = (
                resample_jezero_slope_to_grid(grid) if zone == "jezero" else None
            )
            analyzer = SlopeAnalyzer(
                grid,
                max_slope_deg=max_slope,
                slope_deg_matrix=slope_deg_matrix,
            )
            builder = CellGraphBuilder(grid, analyzer, slope_penalty_weight=3.5)
            stats = analyzer.get_statistics()
            hazard_clusters = builder.get_impassable_hazard_zones(min_cluster_size=3)

            start_cell = _nearest_passable_cell(grid, builder, start_c)
            goal_cell = _nearest_passable_cell(grid, builder, goal_c)
            route = (
                builder.find_path_astar(start_cell, goal_cell)
                if start_cell is not None
                and goal_cell is not None
                and start_cell != goal_cell
                else None
            )

            # Compile compact cell list for 2D map rendering
            cells_data = []
            for r in range(grid.rows):
                for c in range(grid.cols):
                    lat, lon = grid.cell_to_geo(r, c)
                    elev = grid.get_elevation(r, c)
                    slope = analyzer.get_cell_slope(r, c)
                    passable = analyzer.is_cell_passable(r, c)
                    cells_data.append({
                        "r": r,
                        "c": c,
                        "lat": round(lat, 5),
                        "lon": round(lon, 5),
                        "elev": round(elev, 1),
                        "slope": round(slope, 1) if math.isfinite(slope) else None,
                        "passable": passable
                    })

            self._send_json({
                "zone": zone,
                "zone_title": zone_title,
                "terrain_source": terrain_source,
                "zone_center": zone_center,
                "bounds": {
                    "min_lat": grid.min_lat,
                    "max_lat": grid.max_lat,
                    "min_lon": grid.min_lon,
                    "max_lon": grid.max_lon
                },
                "resolution": [grid.rows, grid.cols],
                "cell_size_m": {
                    "dx": round(grid.cell_size_x, 1),
                    "dy": round(grid.cell_size_y, 1)
                },
                "statistics": stats,
                "hazard_zones": hazard_clusters,
                "historical_waypoints": historical_wps,
                "safe_route": route,
                "cells": cells_data
            })
        else:
            self.send_error(404, f"API endpoint not found: {path}")

    def _handle_pathfinding_simulate(self):
        content_len = int(self.headers.get("Content-Length", 0))
        try:
            body = self.rfile.read(content_len)
            req = json.loads(body.decode("utf-8")) if body else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            self._send_json({"error": f"Invalid JSON request: {error}"}, status=400)
            return

        if not isinstance(req, dict):
            self._send_json({"error": "Request body must be a JSON object."}, status=400)
            return

        zone = req.get("zone", "gale")
        if not isinstance(zone, str) or zone.lower() not in ("gale", "jezero"):
            self._send_json({"error": "zone must be either 'gale' or 'jezero'."}, status=400)
            return
        zone = zone.lower()

        try:
            resolution = int(req.get("resolution", 80))
            max_slope = float(req.get("max_slope", 15.0))
            start_coords = req.get("start", {"latitude": -4.596, "longitude": 137.488})
            target_coords = req.get("target", {"latitude": -4.716, "longitude": 137.397})
            start = (float(start_coords["latitude"]), float(start_coords["longitude"]))
            target = (float(target_coords["latitude"]), float(target_coords["longitude"]))
        except (KeyError, TypeError, ValueError) as error:
            self._send_json({"error": f"Invalid route parameters: {error}"}, status=400)
            return

        if not 20 <= resolution <= 100:
            self._send_json({"error": "resolution must be between 20 and 100."}, status=400)
            return
        if not math.isfinite(max_slope) or not 8.0 <= max_slope <= 25.0:
            self._send_json({"error": "max_slope must be between 8 and 25 degrees."}, status=400)
            return
        if not all(math.isfinite(value) for value in (*start, *target)):
            self._send_json({"error": "Route coordinates must be finite numbers."}, status=400)
            return

        if zone == "gale" and resolution == 80 and max_slope == 15.0:
            grid, analyzer, builder = elevation_grid, slope_analyzer, cell_graph_builder
        else:
            try:
                if zone == "jezero":
                    grid = generate_jezero_crater_elevation_grid(resolution_rows=resolution, resolution_cols=resolution)
                    terrain_source = {
                        **JEZERO_TERRAIN_SOURCE,
                        "slope_data": (
                            "Measured 20.2 m HiRISE slope raster; used only for route calculations."
                        ),
                    }
                else:
                    grid = generate_gale_crater_elevation_grid(resolution_rows=resolution, resolution_cols=resolution)
                    terrain_source = GALE_TERRAIN_SOURCE
            except TerrainDataError as error:
                self._send_json({"error": str(error)}, status=503)
                return
            slope_deg_matrix = (
                resample_jezero_slope_to_grid(grid) if zone == "jezero" else None
            )
            analyzer = SlopeAnalyzer(
                grid,
                max_slope_deg=max_slope,
                slope_deg_matrix=slope_deg_matrix,
            )
            builder = CellGraphBuilder(grid, analyzer, slope_penalty_weight=3.5)
        if zone == "gale" and resolution == 80 and max_slope == 15.0:
            terrain_source = GALE_TERRAIN_SOURCE

        for name, coords in (("start", start), ("target", target)):
            latitude, longitude = coords
            if not (grid.min_lat <= latitude <= grid.max_lat and grid.min_lon <= longitude <= grid.max_lon):
                self._send_json({
                    "error": f"{name} must be inside the loaded {zone} terrain bounds.",
                    "bounds": {
                        "min_lat": grid.min_lat,
                        "max_lat": grid.max_lat,
                        "min_lon": grid.min_lon,
                        "max_lon": grid.max_lon,
                    },
                }, status=400)
                return

        requested_start_cell = grid.geo_to_cell(*start)
        requested_goal_cell = grid.geo_to_cell(*target)
        start_cell = _nearest_passable_cell(grid, builder, requested_start_cell)
        goal_cell = _nearest_passable_cell(grid, builder, requested_goal_cell)
        if start_cell is None or goal_cell is None:
            self._send_json({
                "error": "The selected endpoint is on impassable terrain with no safe cell nearby. Choose a safer point."
            }, status=422)
            return
        if start_cell == goal_cell:
            self._send_json({"error": "Choose two points at least one navigable cell apart."}, status=422)
            return

        route = builder.find_path_astar(start_cell, goal_cell)
        if not route:
            self._send_json({"error": "No safe route connects the selected points at this slope limit."}, status=422)
            return

        waypoints = []
        cumulative_distance = 0.0
        cumulative_energy = 0.0
        for idx, (lon, lat, elev) in enumerate(route["coordinates_lon_lat_elev"]):
            slope = 0.0
            if idx > 0:
                previous = route["cell_path"][idx - 1]
                current = route["cell_path"][idx]
                edge = builder.graph.edges[previous, current]
                cumulative_distance += edge["distance_m"]
                slope = edge["edge_slope_deg"]
                cumulative_energy += edge["distance_m"] * (0.24 + slope * 0.012)

            waypoints.append({
                "index": idx,
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "elevation_m": round(elev, 2),
                "slope_deg": round(slope, 2),
                "cumulative_distance_m": round(cumulative_distance, 1),
                "hazard_warning": "High slope scarp nearby" if slope > 12.0 else None,
                "radiation_rate_ugy_h": 9.8,
                "estimated_energy_kcal": round(cumulative_energy, 1),
            })

        distance_m = route["total_distance_meters"]
        duration_min = route["estimated_duration_min"]
        oxygen_liters = round(duration_min * 0.95, 1)
        snapped_start_coords = grid.cell_to_geo(*start_cell)
        snapped_target_coords = grid.cell_to_geo(*goal_cell)
        self._send_json({
            "site_id": req.get("site_id", "jezero-crater-delta" if zone == "jezero" else "mount-sharp-boxwork"),
            "zone": zone,
            "terrain_source": terrain_source,
            "total_distance_m": round(distance_m, 1),
            "estimated_duration_min": duration_min,
            "max_slope_deg": route["max_path_slope_deg"],
            "average_slope_deg": route["mean_path_slope_deg"],
            "total_elevation_gain_m": route["elevation_gain_m"],
            "total_elevation_loss_m": route["elevation_loss_m"],
            "estimated_o2_consumed_liters": oxygen_liters,
            "total_radiation_dose_usv": round((duration_min / 60.0) * 10.5, 2),
            "risk_level": "LOW" if route["max_path_slope_deg"] < 12.0 else "MODERATE",
            "safety_margins": {
                "o2_reserve_remaining_percent": round(max(0.0, 100.0 - (oxygen_liters / 400.0) * 100.0), 1),
                "safe_return_time_buffer_min": round(duration_min * 0.6, 1),
                "point_of_no_return_distance_m": round(distance_m * 0.5, 1),
            },
            "snapped_start": start_cell != requested_start_cell,
            "snapped_target": goal_cell != requested_goal_cell,
            "waypoints": waypoints,
        })

    def _handle_static_get(self, path: str):
        """Serves compiled frontend files from frontend/dist."""
        clean_path = path.lstrip("/")
        if not clean_path:
            clean_path = "index.html"
        elif clean_path in ("tactical", "tactical/"):
            clean_path = "tactical.html"

        file_path = os.path.join(FRONTEND_DIST_DIR, clean_path)

        # Fallback to index.html for SPA routes
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            file_path = os.path.join(FRONTEND_DIST_DIR, "index.html")

        if not os.path.exists(file_path):
            self.send_error(404, "File not found")
            return

        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")


def run_server(port=8000):
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, AresNavHandler)
    print("\n" + "=" * 56)
    print("[ARES-Nav] Martian Tactical Server is RUNNING!")
    print(f"[ARES-Nav] Local Web UI: http://localhost:{port}")
    print(f"[ARES-Nav] API Health:   http://localhost:{port}/api/health")
    print(f"[ARES-Nav] Sites API:    http://localhost:{port}/api/sites")
    print(f"[ARES-Nav] Terrain API:  http://localhost:{port}/api/terrain")
    print("=" * 56 + "\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[ARES-Nav Server] Stopped by user.")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port)
