from dataclasses import dataclass
from typing import Tuple, Optional
import numpy as np

# Mars volumetric mean radius in meters (NASA planetary constants)
MARS_RADIUS_METERS = 3389500.0
METERS_PER_DEGREE_LAT = (np.pi * MARS_RADIUS_METERS) / 180.0  # ~59,160.0 meters per degree


@dataclass
class Cell:
    """Represents an individual spatial cell on the Martian surface."""
    row: int
    col: int
    lat: float
    lon: float
    elevation_m: float
    slope_deg: float = 0.0
    is_passable: bool = True


class ElevationGrid:
    """
    Represents a regular 2D discretization (cell grid) of Martian topographic elevation data.
    Provides coordinate transformations between discrete grid cells (row, col)
    and Martian geographic coordinates (lat, lon).
    """

    def __init__(
        self,
        elevation: np.ndarray,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
    ):
        """
        Initialize the elevation grid.

        :param elevation: 2D numpy array of shape (rows, cols) with heights in meters.
        :param min_lat: Southern-most latitude in decimal degrees.
        :param max_lat: Northern-most latitude in decimal degrees.
        :param min_lon: Western-most longitude in decimal degrees.
        :param max_lon: Eastern-most longitude in decimal degrees.
        """
        if elevation.ndim != 2:
            raise ValueError(f"Elevation array must be 2D, got shape {elevation.shape}")
        if min_lat >= max_lat:
            raise ValueError(f"min_lat ({min_lat}) must be strictly less than max_lat ({max_lat})")
        if min_lon >= max_lon:
            raise ValueError(f"min_lon ({min_lon}) must be strictly less than max_lon ({max_lon})")

        self.elevation = elevation.astype(np.float64)
        self.rows, self.cols = elevation.shape
        self.min_lat = float(min_lat)
        self.max_lat = float(max_lat)
        self.min_lon = float(min_lon)
        self.max_lon = float(max_lon)

        # Geographic resolution in degrees per cell
        self.dlat_deg = (self.max_lat - self.min_lat) / max(1, self.rows - 1)
        self.dlon_deg = (self.max_lon - self.min_lon) / max(1, self.cols - 1)

        # Physical cell dimensions in meters
        # dy corresponds to latitude variation (constant along meridians)
        self.cell_size_y = self.dlat_deg * METERS_PER_DEGREE_LAT

        # dx corresponds to longitude variation (varies with cosine of mean latitude)
        mean_lat_rad = np.radians((self.min_lat + self.max_lat) / 2.0)
        self.cell_size_x = self.dlon_deg * METERS_PER_DEGREE_LAT * np.cos(mean_lat_rad)

    @property
    def shape(self) -> Tuple[int, int]:
        return (self.rows, self.cols)

    def in_bounds(self, row: int, col: int) -> bool:
        """Check if grid index (row, col) is within grid bounds."""
        return 0 <= row < self.rows and 0 <= col < self.cols

    def cell_to_geo(self, row: int, col: int) -> Tuple[float, float]:
        """
        Convert grid cell indices (row, col) to (latitude, longitude) in degrees.
        Row 0 is at max_lat (North), Row (rows - 1) is at min_lat (South).
        Col 0 is at min_lon (West), Col (cols - 1) is at max_lon (East).
        """
        lat = self.max_lat - (row * self.dlat_deg)
        lon = self.min_lon + (col * self.dlon_deg)
        return (lat, lon)

    def geo_to_cell(self, lat: float, lon: float) -> Tuple[int, int]:
        """
        Convert (latitude, longitude) to closest grid cell indices (row, col).
        Clamps to valid grid boundaries.
        """
        row = int(np.round((self.max_lat - lat) / self.dlat_deg))
        col = int(np.round((lon - self.min_lon) / self.dlon_deg))
        row = max(0, min(self.rows - 1, row))
        col = max(0, min(self.cols - 1, col))
        return (row, col)

    def get_elevation(self, row: int, col: int) -> float:
        """Get elevation in meters at (row, col)."""
        if not self.in_bounds(row, col):
            raise IndexError(f"Cell ({row}, {col}) is out of bounds for grid of shape {self.shape}")
        return float(self.elevation[row, col])

    def get_distance_meters(self, r1: int, c1: int, r2: int, c2: int) -> float:
        """
        Calculate local Euclidean physical distance in meters between two cells.
        """
        dr = abs(r1 - r2)
        dc = abs(c1 - c2)
        dx = dc * self.cell_size_x
        dy = dr * self.cell_size_y
        return float(np.sqrt(dx**2 + dy**2))
