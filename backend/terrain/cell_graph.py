import math
from typing import Tuple, Dict, Any, List, Optional
import networkx as nx
import numpy as np
from scipy.ndimage import label
from .grid import ElevationGrid
from .slope import SlopeAnalyzer


class CellGraphBuilder:
    """
    Constructs a spatial navigability cell graph from an ElevationGrid and SlopeAnalyzer.
    Cells are nodes; passable transitions between adjacent cells are weighted edges.
    Impassable cells (cliffs, steep scarps) are excluded from the graph.
    """

    # 8-connectivity (orthogonal + diagonal offsets)
    NEIGHBOR_OFFSETS = [
        (-1, 0), (1, 0), (0, -1), (0, 1),     # Orthogonal (N, S, W, E)
        (-1, -1), (-1, 1), (1, -1), (1, 1)    # Diagonal (NW, NE, SW, SE)
    ]
    BASE_EVA_SPEED_MPS = 0.8

    def __init__(
        self,
        grid: ElevationGrid,
        slope_analyzer: SlopeAnalyzer,
        slope_penalty_weight: float = 3.0,
    ):
        """
        :param grid: ElevationGrid instance.
        :param slope_analyzer: SlopeAnalyzer instance containing slopes and passability mask.
        :param slope_penalty_weight: Multiplier for slope difficulty in traversal cost (default: 3.0).
        """
        self.grid = grid
        self.slope_analyzer = slope_analyzer
        self.slope_weight = float(slope_penalty_weight)
        self.max_slope = slope_analyzer.max_slope_deg
        self.graph = nx.DiGraph()
        self._build_graph()

    def _build_graph(self):
        """Builds the networkx graph with nodes and passable edges."""
        rows, cols = self.grid.shape
        passable_mask = self.slope_analyzer.passable_mask

        # Step 1: Add passable cells as graph nodes
        for r in range(rows):
            for c in range(cols):
                if passable_mask[r, c]:
                    lat, lon = self.grid.cell_to_geo(r, c)
                    elev = self.grid.get_elevation(r, c)
                    slope = self.slope_analyzer.get_cell_slope(r, c)
                    self.graph.add_node(
                        (r, c),
                        row=r,
                        col=c,
                        lat=lat,
                        lon=lon,
                        elevation=elev,
                        slope_deg=slope,
                    )

        # Step 2: Add directed transitions; uphill and downhill take different time.
        for r in range(rows):
            for c in range(cols):
                if not passable_mask[r, c]:
                    continue

                u = (r, c)
                for dr, dc in self.NEIGHBOR_OFFSETS:
                    nr, nc = r + dr, c + dc
                    v = (nr, nc)

                    # Process each adjacent pair once before adding both directions.
                    if (dr < 0) or (dr == 0 and dc < 0):
                        continue

                    if not self.grid.in_bounds(nr, nc):
                        continue

                    if not passable_mask[nr, nc]:
                        continue
                    # A diagonal must not pass between blocked orthogonal cells.
                    if dr and dc and (
                        not passable_mask[r + dr, c]
                        or not passable_mask[r, c + dc]
                    ):
                        continue

                    # Check directional slope between adjacent cells
                    edge_slope = self.slope_analyzer.compute_edge_slope_deg(r, c, nr, nc)
                    if edge_slope > self.max_slope:
                        # Slope is too steep to traverse between these two cells
                        continue

                    # Traversal cost: distance * (1 + slope_weight * (slope / max_slope)^2)
                    dist_m = self.grid.get_distance_meters(r, c, nr, nc)
                    slope_factor = (edge_slope / max(0.1, self.max_slope)) ** 2
                    cost = dist_m * (1.0 + self.slope_weight * slope_factor)

                    elevation_change = (
                        self.grid.get_elevation(nr, nc) - self.grid.get_elevation(r, c)
                    )
                    self._add_transition(u, v, dist_m, edge_slope, cost, elevation_change)
                    self._add_transition(v, u, dist_m, edge_slope, cost, -elevation_change)

    def _add_transition(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        distance_m: float,
        slope_deg: float,
        distance_cost: float,
        elevation_change_m: float,
    ) -> None:
        grade = elevation_change_m / max(distance_m, 0.1)
        speed_mps = self.BASE_EVA_SPEED_MPS * math.exp(
            -2.0 * abs(grade) - max(grade, 0.0)
        )
        self.graph.add_edge(
            start,
            end,
            weight=distance_cost,
            travel_time_s=distance_m / speed_mps,
            distance_m=distance_m,
            edge_slope_deg=round(slope_deg, 2),
            elevation_change_m=elevation_change_m,
        )

    def find_path_astar(
        self, start: Tuple[int, int], goal: Tuple[int, int]
    ) -> Optional[Dict[str, Any]]:
        """
        Computes the optimal hazard-aware path between start and goal cells using A*.
        Minimizes estimated travel time; distance divided by the maximum EVA speed
        is an admissible heuristic because slopes can only reduce traversal speed.

        :param start: (row, col) of origin
        :param goal: (row, col) of destination
        :return: Dict with route path cells, coordinates, total distance, and metrics; or None if no path.
        """
        if start not in self.graph:
            raise ValueError(f"Start cell {start} is either out of bounds or impassable.")
        if goal not in self.graph:
            raise ValueError(f"Goal cell {goal} is either out of bounds or impassable.")

        def heuristic(u, v):
            return self.grid.get_distance_meters(u[0], u[1], v[0], v[1]) / self.BASE_EVA_SPEED_MPS

        try:
            cell_path = nx.astar_path(
                self.graph, start, goal, heuristic=heuristic, weight="travel_time_s"
            )

            total_distance_m = 0.0
            total_time_s = 0.0
            elevation_gain_m = 0.0
            elevation_loss_m = 0.0
            edge_slopes = []
            coordinates = []

            for i in range(len(cell_path)):
                curr = cell_path[i]
                node_data = self.graph.nodes[curr]
                coordinates.append([node_data["lon"], node_data["lat"], node_data["elevation"]])

                if i > 0:
                    prev = cell_path[i - 1]
                    edge = self.graph.edges[prev, curr]
                    total_distance_m += edge["distance_m"]
                    total_time_s += edge["travel_time_s"]
                    edge_slopes.append(edge["edge_slope_deg"])
                    if edge["elevation_change_m"] > 0:
                        elevation_gain_m += edge["elevation_change_m"]
                    else:
                        elevation_loss_m += abs(edge["elevation_change_m"])

            return {
                "success": True,
                "num_waypoints": len(cell_path),
                "total_distance_meters": round(total_distance_m, 2),
                "total_cost_seconds": round(total_time_s, 2),
                "estimated_duration_min": round(total_time_s / 60.0, 1),
                "cell_path": cell_path,
                "coordinates_lon_lat_elev": coordinates,
                "mean_path_slope_deg": round(float(np.mean(edge_slopes)), 2) if edge_slopes else 0.0,
                "max_path_slope_deg": round(float(np.max(edge_slopes)), 2) if edge_slopes else 0.0,
                "elevation_gain_m": round(elevation_gain_m, 2),
                "elevation_loss_m": round(elevation_loss_m, 2),
            }
        except nx.NetworkXNoPath:
            return None

    def get_impassable_hazard_zones(self, min_cluster_size: int = 2) -> List[Dict[str, Any]]:
        """
        Groups connected impassable cells into distinct hazard clusters/zones.
        Uses 8-connectivity image labeling.

        :param min_cluster_size: Minimum number of contiguous cells to qualify as a named hazard zone.
        :return: List of hazard cluster descriptors.
        """
        impassable_binary = (~self.slope_analyzer.passable_mask).astype(int)
        structure = np.ones((3, 3), dtype=int)  # 8-connectivity
        labeled_array, num_features = label(impassable_binary, structure=structure)

        hazard_clusters = []
        for feature_id in range(1, num_features + 1):
            cell_indices = np.argwhere(labeled_array == feature_id)
            if len(cell_indices) < min_cluster_size:
                continue

            slopes = [self.slope_analyzer.get_cell_slope(r, c) for r, c in cell_indices]
            coords = [self.grid.cell_to_geo(r, c) for r, c in cell_indices]
            lats = [c[0] for c in coords]
            lons = [c[1] for c in coords]

            hazard_clusters.append({
                "cluster_id": int(feature_id),
                "cell_count": len(cell_indices),
                "max_slope_deg": round(float(np.max(slopes)), 2),
                "mean_slope_deg": round(float(np.mean(slopes)), 2),
                "bounding_box": {
                    "min_lat": round(min(lats), 5),
                    "max_lat": round(max(lats), 5),
                    "min_lon": round(min(lons), 5),
                    "max_lon": round(max(lons), 5),
                },
                "centroid_geo": {
                    "lat": round(float(np.mean(lats)), 5),
                    "lon": round(float(np.mean(lons)), 5),
                }
            })

        # Sort clusters by size (largest hazard zones first)
        hazard_clusters.sort(key=lambda x: x["cell_count"], reverse=True)
        return hazard_clusters

    def get_graph_summary(self) -> Dict[str, Any]:
        """Returns topological summary of the generated cell graph."""
        return {
            "num_nodes": self.graph.number_of_nodes(),
            "num_edges": self.graph.number_of_edges(),
            "is_connected": nx.is_weakly_connected(self.graph) if self.graph.number_of_nodes() > 0 else False,
            "connected_components": nx.number_weakly_connected_components(self.graph) if self.graph.number_of_nodes() > 0 else 0,
            "max_slope_deg": self.max_slope,
        }
