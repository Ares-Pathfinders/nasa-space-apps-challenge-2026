"""
Standalone CLI entry point for the ARES-Nav Topographic Terrain Analysis & Cell Graph.
Runs the pipeline, calculates slopes, detects impassable hazards, generates the navigability
graph, and exports the results to GeoJSON/JSON for the frontend.
"""

import os
import sys
import json
import argparse

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.terrain.grid import ElevationGrid
from backend.terrain.slope import SlopeAnalyzer
from backend.terrain.cell_graph import CellGraphBuilder
from backend.data.gale_crater_topography import (
    generate_gale_crater_elevation_grid,
    fetch_or_cache_curiosity_waypoints,
    GALE_MIN_LAT,
    GALE_MAX_LAT,
    GALE_MIN_LON,
    GALE_MAX_LON,
)


def export_topographic_analysis(
    output_path: str = "terrain_analysis_output.json",
    resolution: int = 80,
    max_slope_deg: float = 15.0,
    slope_penalty_weight: float = 3.5,
):
    print(f"[ARES-Nav] Generating Gale Crater elevation grid ({resolution}x{resolution})...")
    grid = generate_gale_crater_elevation_grid(
        resolution_rows=resolution,
        resolution_cols=resolution,
    )

    print(f"[ARES-Nav] Computing topographic slopes (Horn's method, threshold = {max_slope_deg}°)...")
    analyzer = SlopeAnalyzer(grid, max_slope_deg=max_slope_deg)
    stats = analyzer.get_statistics()

    print(f"[ARES-Nav] Building navigability cell graph...")
    builder = CellGraphBuilder(grid, analyzer, slope_penalty_weight=slope_penalty_weight)
    graph_summary = builder.get_graph_summary()

    print(f"[ARES-Nav] Detecting impassable hazard zones...")
    hazard_clusters = builder.get_impassable_hazard_zones(min_cluster_size=4)

    # Route simulation: Bradbury Landing corridor to Mount Sharp target
    start_cell = (15, int(resolution * 0.8))
    goal_cell = (int(resolution * 0.8), int(resolution * 0.3))

    if not analyzer.is_cell_passable(*start_cell):
        start_cell = (start_cell[0] - 1, start_cell[1])
    if not analyzer.is_cell_passable(*goal_cell):
        goal_cell = (goal_cell[0] - 1, goal_cell[1])

    print(f"[ARES-Nav] Simulating hazard-aware A* route from {start_cell} to {goal_cell}...")
    route = builder.find_path_astar(start_cell, goal_cell)

    # Compile impassable cells as geo points for visualization
    impassable_points = []
    rows, cols = grid.shape
    for r in range(rows):
        for c in range(cols):
            if not analyzer.is_cell_passable(r, c):
                lat, lon = grid.cell_to_geo(r, c)
                impassable_points.append({
                    "row": r,
                    "col": c,
                    "lat": round(lat, 5),
                    "lon": round(lon, 5),
                    "elevation_m": round(grid.get_elevation(r, c), 1),
                    "slope_deg": round(analyzer.get_cell_slope(r, c), 1),
                })

    output_data = {
        "metadata": {
            "mission": "Curiosity (MSL) - Gale Crater / Mount Sharp",
            "bounds": {
                "min_lat": GALE_MIN_LAT,
                "max_lat": GALE_MAX_LAT,
                "min_lon": GALE_MIN_LON,
                "max_lon": GALE_MAX_LON,
            },
            "grid_resolution": [resolution, resolution],
            "cell_size_meters": {
                "dx": round(grid.cell_size_x, 1),
                "dy": round(grid.cell_size_y, 1),
            },
        },
        "statistics": stats,
        "graph_summary": graph_summary,
        "hazard_zones": hazard_clusters,
        "impassable_cells_sample": impassable_points,
        "safe_route": route,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print(f"[ARES-Nav] Results saved to: {output_path}")
    print(f"[ARES-Nav] Impassable cells found: {len(impassable_points)}")
    print(f"[ARES-Nav] Hazard clusters: {len(hazard_clusters)}")
    if route:
        print(f"[ARES-Nav] Safe route length: {route['total_distance_meters'] / 1000.0:.2f} km across {route['num_waypoints']} cells")

    return output_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ARES-Nav Topographic Cell Graph Generator")
    parser.add_argument("--resolution", type=int, default=80, help="Grid resolution (default: 80)")
    parser.add_argument("--max-slope", type=float, default=15.0, help="Max safe slope in degrees (default: 15.0)")
    parser.add_argument("--output", type=str, default="terrain_analysis_output.json", help="Output JSON path")
    args = parser.parse_args()

    export_topographic_analysis(
        output_path=args.output,
        resolution=args.resolution,
        max_slope_deg=args.max_slope,
    )
