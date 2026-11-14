from typing import Tuple, Dict, Any
import numpy as np
from .grid import ElevationGrid


class SlopeAnalyzer:
    """
    Computes topographic slopes, gradient vectors, and hazard passability masks
    from an ElevationGrid using standard planetary GIS algorithms (Horn's method).
    """

    def __init__(self, grid: ElevationGrid, max_slope_deg: float = 15.0):
        """
        :param grid: ElevationGrid instance containing elevation raster and georeferencing.
        :param max_slope_deg: Maximum allowable slope in degrees before a cell is considered
                              impassable for human EVA or rover transit (default: 15.0°).
        """
        self.grid = grid
        self.max_slope_deg = float(max_slope_deg)
        self.slope_deg_matrix = self._compute_slope_matrix()
        self.passable_mask = self.slope_deg_matrix <= self.max_slope_deg

    def _compute_slope_matrix(self) -> np.ndarray:
        """
        Calculates surface slope in degrees for every cell using Horn's 3x3 finite difference method,
        accounting for physical cell dimensions in meters (dx and dy).
        """
        elev = self.grid.elevation
        rows, cols = elev.shape
        dx = self.grid.cell_size_x
        dy = self.grid.cell_size_y

        # Pad boundaries using reflection to compute gradients cleanly at edges
        padded = np.pad(elev, pad_width=1, mode='edge')

        # 3x3 neighborhood windows (North-West, North, North-East, etc.)
        z_nw = padded[0:rows, 0:cols]
        z_n  = padded[0:rows, 1:cols+1]
        z_ne = padded[0:rows, 2:cols+2]
        z_w  = padded[1:rows+1, 0:cols]
        z_e  = padded[1:rows+1, 2:cols+2]
        z_sw = padded[2:rows+2, 0:cols]
        z_s  = padded[2:rows+2, 1:cols+1]
        z_se = padded[2:rows+2, 2:cols+2]

        # Horn's weighted gradient approximation
        dz_dx = ((z_ne + 2.0 * z_e + z_se) - (z_nw + 2.0 * z_w + z_sw)) / (8.0 * dx)
        dz_dy = ((z_sw + 2.0 * z_s + z_se) - (z_nw + 2.0 * z_n + z_ne)) / (8.0 * dy)

        gradient_magnitude = np.sqrt(dz_dx**2 + dz_dy**2)
        slope_radians = np.arctan(gradient_magnitude)
        slope_degrees = np.degrees(slope_radians)

        return slope_degrees

    def get_cell_slope(self, row: int, col: int) -> float:
        """Get the computed surface slope in degrees for cell (row, col)."""
        if not self.grid.in_bounds(row, col):
            raise IndexError(f"Cell ({row}, {col}) is out of bounds.")
        return float(self.slope_deg_matrix[row, col])

    def is_cell_passable(self, row: int, col: int) -> bool:
        """Check if cell (row, col) is safe to traverse based on slope threshold."""
        if not self.grid.in_bounds(row, col):
            return False
        return bool(self.passable_mask[row, col])

    def compute_edge_slope_deg(self, r1: int, c1: int, r2: int, c2: int) -> float:
        """
        Calculates the directional slope angle in degrees between two adjacent cells.
        Uses the exact physical distance and elevation difference.
        """
        z1 = self.grid.get_elevation(r1, c1)
        z2 = self.grid.get_elevation(r2, c2)
        distance_m = self.grid.get_distance_meters(r1, c1, r2, c2)
        if distance_m <= 0:
            return 0.0

        delta_z = abs(z2 - z1)
        slope_deg = np.degrees(np.arctan(delta_z / distance_m))
        return float(slope_deg)

    def get_statistics(self) -> Dict[str, Any]:
        """Returns statistical overview of the terrain slope and hazard coverage."""
        total_cells = self.grid.rows * self.grid.cols
        impassable_cells = int(np.sum(~self.passable_mask))
        passable_cells = total_cells - impassable_cells
        impassable_pct = (impassable_cells / total_cells) * 100.0

        return {
            "total_cells": total_cells,
            "passable_cells": passable_cells,
            "impassable_cells": impassable_cells,
            "impassable_percentage": round(impassable_pct, 2),
            "max_slope_threshold_deg": self.max_slope_deg,
            "min_slope_deg": round(float(np.min(self.slope_deg_matrix)), 2),
            "max_slope_deg": round(float(np.max(self.slope_deg_matrix)), 2),
            "mean_slope_deg": round(float(np.mean(self.slope_deg_matrix)), 2),
            "median_slope_deg": round(float(np.median(self.slope_deg_matrix)), 2),
            "min_elevation_m": round(float(np.min(self.grid.elevation)), 2),
            "max_elevation_m": round(float(np.max(self.grid.elevation)), 2),
        }
