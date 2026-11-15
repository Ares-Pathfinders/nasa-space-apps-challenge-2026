from typing import Optional, Tuple

from ..models.pathfinding import PathfindingRequest, PathfindingResponse, PathWaypoint
try:
    from backend.terrain.cell_graph import CellGraphBuilder
    from backend.terrain.slope import SlopeAnalyzer
except ModuleNotFoundError:
    from terrain.cell_graph import CellGraphBuilder
    from terrain.slope import SlopeAnalyzer

try:
    from backend.data.gale_crater_topography import (
        generate_gale_crater_elevation_grid,
    )
    from backend.data.jezero_crater_topography import (
        generate_jezero_crater_elevation_grid,
    )
except ModuleNotFoundError:
    from data.gale_crater_topography import generate_gale_crater_elevation_grid
    from data.jezero_crater_topography import generate_jezero_crater_elevation_grid


def _nearest_passable_cell(
    grid, builder: CellGraphBuilder, cell: Tuple[int, int], max_radius: int = 2
) -> Optional[Tuple[int, int]]:
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
                key=lambda candidate: grid.get_distance_meters(
                    row, col, candidate[0], candidate[1]
                ),
            )
    return None


class PathfindingService:
    @staticmethod
    def simulate_eva_route(req: PathfindingRequest) -> PathfindingResponse:
        zone_generators = {
            "mount-sharp-boxwork": generate_gale_crater_elevation_grid,
            "gale": generate_gale_crater_elevation_grid,
            "jezero-crater-delta": generate_jezero_crater_elevation_grid,
            "jezero": generate_jezero_crater_elevation_grid,
        }
        generator = zone_generators.get(req.site_id.lower())
        if generator is None:
            raise ValueError("Pathfinding is available only for Gale Crater and Jezero.")

        grid = generator(resolution_rows=80, resolution_cols=80)
        analyzer = SlopeAnalyzer(grid, max_slope_deg=req.max_slope_limit_deg)
        builder = CellGraphBuilder(grid, analyzer, slope_penalty_weight=3.5)

        endpoints = (
            ("start", req.start.latitude, req.start.longitude),
            ("target", req.target.latitude, req.target.longitude),
        )
        endpoint_cells = []
        for name, latitude, longitude in endpoints:
            if not (
                grid.min_lat <= latitude <= grid.max_lat
                and grid.min_lon <= longitude <= grid.max_lon
            ):
                raise ValueError(f"{name} must be inside the loaded terrain bounds.")
            requested_cell = grid.geo_to_cell(latitude, longitude)
            passable_cell = _nearest_passable_cell(grid, builder, requested_cell)
            if passable_cell is None:
                raise ValueError(
                    f"{name} is on impassable terrain with no safe cell nearby."
                )
            endpoint_cells.append((requested_cell, passable_cell))

        (_, start_cell), (_, target_cell) = endpoint_cells
        if start_cell == target_cell:
            raise ValueError("Choose two points at least one navigable cell apart.")

        route = builder.find_path_astar(start_cell, target_cell)
        if route is None:
            raise ValueError("No safe route connects the selected points.")

        waypoints = []
        cumulative_distance = 0.0
        cumulative_energy = 0.0
        for index, (longitude, latitude, elevation) in enumerate(
            route["coordinates_lon_lat_elev"]
        ):
            slope = 0.0
            if index:
                previous = route["cell_path"][index - 1]
                current = route["cell_path"][index]
                edge = builder.graph.edges[previous, current]
                cumulative_distance += edge["distance_m"]
                slope = edge["edge_slope_deg"]
                cumulative_energy += edge["distance_m"] * (0.24 + slope * 0.012)

            waypoints.append(
                PathWaypoint(
                    index=index,
                    latitude=round(latitude, 6),
                    longitude=round(longitude, 6),
                    elevation_m=round(elevation, 2),
                    slope_deg=round(slope, 2),
                    cumulative_distance_m=round(cumulative_distance, 2),
                    hazard_warning=f"MODERATE SLOPE WARNING ({slope}°)" if slope > 14 else None,
                    radiation_rate_ugy_h=9.8,
                    estimated_energy_kcal=round(cumulative_energy, 2),
                )
            )

        duration_min = route["estimated_duration_min"]
        oxygen_liters = round(duration_min * 0.95, 1)
        maximum_slope = route["max_path_slope_deg"]
        if duration_min > req.eva_time_limit_minutes:
            risk_level = "CRITICAL"
        elif maximum_slope > 15 or duration_min > req.eva_time_limit_minutes * 0.75:
            risk_level = "HIGH"
        elif maximum_slope > 10:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"

        return PathfindingResponse(
            site_id=req.site_id,
            total_distance_m=round(route["total_distance_meters"], 1),
            estimated_duration_min=duration_min,
            max_slope_deg=maximum_slope,
            average_slope_deg=route["mean_path_slope_deg"],
            total_elevation_gain_m=route["elevation_gain_m"],
            total_elevation_loss_m=route["elevation_loss_m"],
            estimated_o2_consumed_liters=oxygen_liters,
            total_radiation_dose_usv=round(9.8 * duration_min / 60.0, 2),
            risk_level=risk_level,
            safety_margins={
                "o2_reserve_remaining_percent": max(
                    0.0, round(100.0 - oxygen_liters / 300.0 * 100.0, 1)
                ),
                "safe_return_time_buffer_min": round(
                    max(0.0, req.eva_time_limit_minutes - duration_min), 1
                ),
                "point_of_no_return_distance_m": round(
                    route["total_distance_meters"] * 0.5, 1
                ),
            },
            waypoints=waypoints,
        )


pathfinding_service = PathfindingService()
