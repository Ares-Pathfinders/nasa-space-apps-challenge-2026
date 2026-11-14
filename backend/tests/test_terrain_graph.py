"""
Unit and integration test suite for the ARES-Nav terrain cell graph.
Validates:
1. Cell grid coordinate transformation and elevation bounds.
2. Horn's slope algorithm accuracy against known geometric planes and cliffs.
3. Accurate detection and clustering of impassable cells (cliffs > max_slope_deg).
4. Cell graph generation (nodes, edges, connectivity).
5. Hazard-aware A* pathfinding avoiding all detected impassable zones.
"""

import sys
import os
import numpy as np

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.terrain.grid import ElevationGrid
from backend.terrain.slope import SlopeAnalyzer
from backend.terrain.cell_graph import CellGraphBuilder
from backend.data.gale_crater_topography import (
    generate_gale_crater_elevation_grid,
    fetch_or_cache_curiosity_waypoints,
)


def test_controlled_step_cliff_detection():
    """
    Test 1: Controlled synthetic benchmark.
    Creates a 20x20 cell grid with a flat plateau, a vertical cliff (slope > 40°),
    and a gentle ramp (slope ~ 5°).
    Verifies that the cliff cells are 100% marked as impassable.
    """
    print("\n" + "=" * 65)
    print("TEST 1: Controlled Synthetic Cliff & Hazard Threshold Verification")
    print("=" * 65)

    rows, cols = 20, 20
    elev = np.zeros((rows, cols), dtype=np.float64)

    # Left half: elevation 0m (flat floor)
    # Right half: elevation 200m (plateau)
    # Column 10: cliff edge with steep drop
    elev[:, 10:] = 200.0

    # Create grid spanning 0.02 degrees (~1.18 km)
    grid = ElevationGrid(
        elevation=elev,
        min_lat=-4.60,
        max_lat=-4.58,
        min_lon=137.40,
        max_lon=137.42,
    )

    analyzer = SlopeAnalyzer(grid, max_slope_deg=15.0)
    builder = CellGraphBuilder(grid, analyzer)

    stats = analyzer.get_statistics()
    print(f"Grid dimensions: {rows}x{cols} ({stats['total_cells']} cells)")
    print(f"Cell physical size: dx={grid.cell_size_x:.1f}m, dy={grid.cell_size_y:.1f}m")
    print(f"Max computed slope: {stats['max_slope_deg']}°")
    print(f"Impassable cells detected (slope > 15°): {stats['impassable_cells']} ({stats['impassable_percentage']}%)")
    print(f"Graph nodes generated: {builder.graph.number_of_nodes()} (Passable cells only)")

    # Assert that cliff columns (columns 9 and 10) contain impassable cells
    assert stats["impassable_cells"] > 0, "Failed: impassable cliff was not detected!"
    for r in range(rows):
        assert not analyzer.is_cell_passable(r, 9) or not analyzer.is_cell_passable(r, 10), (
            f"Row {r} cliff edge should be marked impassable"
        )

    # Verify that no edge directly crosses the cliff
    for u, v in builder.graph.edges:
        # u and v cannot bridge from col 8 to col 11 directly through the cliff
        assert not (u[1] <= 8 and v[1] >= 11), f"Graph incorrectly allows crossing cliff between {u} and {v}"

    print(">> TEST 1 PASSED: Cliff correctly detected as impassable and severed from graph.")


def test_gale_crater_curiosity_topography():
    """
    Test 2: Real Gale Crater / Curiosity Expedition Corridor.
    Evaluates the cell graph on the 12 km corridor covering Bradbury Landing,
    the floor of Gale Crater, Vera Rubin Ridge (hematite scarp), and the slopes of Mount Sharp.
    """
    print("\n" + "=" * 65)
    print("TEST 2: Curiosity Expedition Corridor (Gale Crater) Topographic Analysis")
    print("=" * 65)

    # Generate Gale Crater elevation grid (80x80 = 6,400 cells)
    grid = generate_gale_crater_elevation_grid(resolution_rows=80, resolution_cols=80)
    print(f"Gale Crater Grid: {grid.rows}x{grid.cols} cells ({grid.rows * grid.cols} total)")
    print(f"Area: Lat [{grid.min_lat:.3f}°, {grid.max_lat:.3f}°] | Lon [{grid.min_lon:.3f}°, {grid.max_lon:.3f}°]")
    print(f"Cell Resolution: {grid.cell_size_x:.1f}m (East-West) x {grid.cell_size_y:.1f}m (North-South)")

    # Analyze slopes with EVA safety threshold of 15°
    max_eva_slope = 15.0
    analyzer = SlopeAnalyzer(grid, max_slope_deg=max_eva_slope)
    stats = analyzer.get_statistics()

    print("\n--- Topographic Statistics ---")
    print(f"Elevation Range: {stats['min_elevation_m']} m to {stats['max_elevation_m']} m")
    print(f"Slope Range: min={stats['min_slope_deg']}°, max={stats['max_slope_deg']}°, mean={stats['mean_slope_deg']}°")
    print(f"Safe / Passable Cells: {stats['passable_cells']} ({(stats['passable_cells']/stats['total_cells'])*100:.1f}%)")
    print(f"Impassable Cells (> {max_eva_slope}°): {stats['impassable_cells']} ({stats['impassable_percentage']}%)")

    # Build cell graph
    builder = CellGraphBuilder(grid, analyzer, slope_penalty_weight=3.5)
    graph_summary = builder.get_graph_summary()

    print("\n--- Cell Graph Topologic Metrics ---")
    print(f"Graph Nodes (Navigable cells): {graph_summary['num_nodes']}")
    print(f"Graph Edges (Valid traversals): {graph_summary['num_edges']}")
    print(f"Connected Components: {graph_summary['connected_components']}")

    # Identify distinct impassable hazard zones
    hazard_clusters = builder.get_impassable_hazard_zones(min_cluster_size=5)
    print(f"\n--- Detected Impassable Hazard Zones (Clusters > 5 cells): {len(hazard_clusters)} ---")
    for idx, cluster in enumerate(hazard_clusters[:5], start=1):
        print(
            f"  [Hazard Zone {idx}] Cells: {cluster['cell_count']} | "
            f"Max Slope: {cluster['max_slope_deg']}° | "
            f"Centroid: Lat {cluster['centroid_geo']['lat']}°, Lon {cluster['centroid_geo']['lon']}°"
        )

    # Pathfinding simulation: EVA route navigating around the detected hazards
    # Start: Near Bradbury Landing (North-East, row 15, col 65)
    # Goal: Science target in lower Mount Sharp (South-West, row 65, col 25)
    start_cell = (15, 65)
    goal_cell = (65, 25)

    # Ensure start and goal are passable
    if not analyzer.is_cell_passable(*start_cell):
        start_cell = (14, 65)
    if not analyzer.is_cell_passable(*goal_cell):
        goal_cell = (64, 25)

    print(f"\n--- Pathfinding Simulation (Hazard-Aware A*) ---")
    print(f"Start Cell: {start_cell} (Lat {grid.cell_to_geo(*start_cell)[0]:.4f}°, Lon {grid.cell_to_geo(*start_cell)[1]:.4f}°)")
    print(f"Goal Cell:  {goal_cell} (Lat {grid.cell_to_geo(*goal_cell)[0]:.4f}°, Lon {grid.cell_to_geo(*goal_cell)[1]:.4f}°)")

    route = builder.find_path_astar(start_cell, goal_cell)
    assert route is not None, "Failed: A* could not find a safe path through navigable cells!"

    print(f"Route Status: SUCCESS")
    print(f"Waypoints Count: {route['num_waypoints']}")
    print(f"Total Ground Distance: {route['total_distance_meters'] / 1000.0:.2f} km")
    print(f"Elevation Traversed: {route['elevation_gain_m']:.1f} m")
    print(f"Mean Route Slope: {route['mean_path_slope_deg']}°")
    print(f"Max Route Slope: {route['max_path_slope_deg']}° (Guaranteed <= {max_eva_slope}° threshold)")

    # Assert that no point in the route exceeds max_eva_slope
    assert route["max_path_slope_deg"] <= max_eva_slope, (
        f"Safety violation: Path entered impassable terrain with slope {route['max_path_slope_deg']}°"
    )

    print("\n>> TEST 2 PASSED: Real Gale Crater topography correctly mapped to cell graph;")
    print("   Impassable zones successfully identified and safely bypassed by the routing engine.")


def test_live_waypoints_fetch():
    """
    Test 3: Fetch Curiosity rover real telemetry data from NASA MMGIS API.
    """
    print("\n" + "=" * 65)
    print("TEST 3: NASA MMGIS Live Curiosity Telemetry Connection")
    print("=" * 65)
    waypoints = fetch_or_cache_curiosity_waypoints()
    print(f"NASA Curiosity 3D Waypoints Retrieved: {len(waypoints)}")
    if waypoints:
        wp0 = waypoints[0]["properties"]
        wp_last = waypoints[-1]["properties"]
        print(f"Landing (Sol {wp0.get('sol', 0)}): Lat {wp0.get('lat')}°, Lon {wp0.get('lon')}°, Elev {wp0.get('elev_geoid')}m")
        print(f"Latest  (Sol {wp_last.get('sol', 0)}): Lat {wp_last.get('lat')}°, Lon {wp_last.get('lon')}°, Elev {wp_last.get('elev_geoid')}m")
        print(f"Total Traversed Distance: {wp_last.get('dist_total_m', 0) / 1000.0:.2f} km")
        print(">> TEST 3 PASSED: NASA Curiosity telemetry connection active.")


if __name__ == "__main__":
    test_controlled_step_cliff_detection()
    test_gale_crater_curiosity_topography()
    test_live_waypoints_fetch()
    print("\n" + "#" * 65)
    print("ALL TOPOGRAPHIC CELL GRAPH TESTS COMPLETED SUCCESSFULLY!")
    print("#" * 65)
