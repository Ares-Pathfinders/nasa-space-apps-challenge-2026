import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from unittest.mock import patch

from backend.terrain.cell_graph import CellGraphBuilder
from backend.terrain.grid import ElevationGrid
from backend.terrain.slope import SlopeAnalyzer
from backend.app.models.pathfinding import LatLonPoint, PathfindingRequest
from backend.app.services import pathfinding_service
from backend.data.gale_crater_topography import (
    GALE_MAX_LAT,
    GALE_MAX_LON,
    GALE_MIN_LAT,
    GALE_MIN_LON,
)
from backend.data.jezero_crater_topography import (
    JEZERO_MAX_LAT,
    JEZERO_MAX_LON,
    JEZERO_MIN_LAT,
    JEZERO_MIN_LON,
)


def _small_grid(elevation):
    return ElevationGrid(
        elevation=np.asarray(elevation, dtype=float),
        min_lat=-4.60,
        max_lat=-4.58,
        min_lon=137.40,
        max_lon=137.42,
    )


def test_route_grid_round_trips_coordinates_and_has_physical_cell_sizes():
    grid = _small_grid(np.zeros((3, 3)))

    for cell in ((0, 0), (1, 1), (2, 2)):
        assert grid.geo_to_cell(*grid.cell_to_geo(*cell)) == cell

    assert grid.cell_size_x > 0
    assert grid.cell_size_y > 0
    assert grid.get_distance_meters(0, 0, 1, 1) > grid.get_distance_meters(0, 0, 1, 0)


def test_astar_estimates_uphill_slower_than_downhill():
    grid = _small_grid([[0, 0], [0, 10]])
    analyzer = SlopeAnalyzer(grid, max_slope_deg=25)
    builder = CellGraphBuilder(grid, analyzer)

    uphill_seconds = builder.graph.edges[(0, 0), (1, 1)]["travel_time_s"]
    downhill_seconds = builder.graph.edges[(1, 1), (0, 0)]["travel_time_s"]

    assert uphill_seconds > downhill_seconds
    assert builder.find_path_astar((0, 0), (1, 1))["estimated_duration_min"] > 0


def test_astar_prefers_a_longer_flat_detour_when_it_is_faster():
    grid = _small_grid([[0, 250, 0], [0, 0, 0], [0, 0, 0]])
    analyzer = SlopeAnalyzer(grid, max_slope_deg=25)
    builder = CellGraphBuilder(grid, analyzer)

    route = builder.find_path_astar((0, 0), (0, 2))

    assert route is not None
    assert any(row > 0 for row, _ in route["cell_path"])
    assert route["total_distance_meters"] > grid.get_distance_meters(0, 0, 0, 2)


def test_astar_does_not_cut_diagonally_between_blocked_cells():
    grid = _small_grid(np.zeros((2, 2)))
    analyzer = SlopeAnalyzer(grid, max_slope_deg=25)
    analyzer.passable_mask = np.array([[True, False], [False, True]])
    builder = CellGraphBuilder(grid, analyzer)

    assert builder.find_path_astar((0, 0), (1, 1)) is None


def test_api_pathfinding_service_returns_grid_route_and_realistic_metrics():
    grid = _small_grid(np.zeros((3, 3)))
    request = PathfindingRequest(
        site_id="mount-sharp-boxwork",
        start=LatLonPoint(latitude=grid.min_lat, longitude=grid.min_lon),
        target=LatLonPoint(latitude=grid.max_lat, longitude=grid.max_lon),
    )

    with patch.object(pathfinding_service, "generate_gale_crater_elevation_grid", return_value=grid):
        response = pathfinding_service.pathfinding_service.simulate_eva_route(request)

    assert response.total_distance_m > 0
    assert response.estimated_duration_min > 0
    assert response.total_elevation_gain_m == 0
    assert len(response.waypoints) >= 2

def test_api_pathfinding_accepts_points_in_expanded_expedition_bounds():
    expeditions = (
        (
            "gale",
            "generate_gale_crater_elevation_grid",
            (GALE_MIN_LAT, GALE_MAX_LAT, GALE_MIN_LON, GALE_MAX_LON),
        ),
        (
            "jezero",
            "generate_jezero_crater_elevation_grid",
            (JEZERO_MIN_LAT, JEZERO_MAX_LAT, JEZERO_MIN_LON, JEZERO_MAX_LON),
        ),
    )

    for site_id, generator_name, bounds in expeditions:
        min_lat, max_lat, min_lon, max_lon = bounds
        grid = ElevationGrid(
            elevation=np.zeros((3, 3)),
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
        )
        request = PathfindingRequest(
            site_id=site_id,
            start=LatLonPoint(latitude=min_lat, longitude=min_lon),
            target=LatLonPoint(latitude=max_lat, longitude=max_lon),
        )

        with patch.object(pathfinding_service, generator_name, return_value=grid):
            response = pathfinding_service.pathfinding_service.simulate_eva_route(request)

        assert len(response.waypoints) >= 2
