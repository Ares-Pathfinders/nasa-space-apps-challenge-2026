import os
import json
from functools import lru_cache
from io import BytesIO
from typing import Optional

import numpy as np
import requests
import tifffile

from ..terrain.grid import ElevationGrid
from .terrain_errors import TerrainDataError

# Full Gale Crater extent published by the NASA Mars Trek DEM
GALE_MIN_LAT = -4.925
GALE_MAX_LAT = -4.249
GALE_MIN_LON = 137.1225
GALE_MAX_LON = 137.7298

GALE_TERRAIN_SOURCE = {
    "name": "NASA Mars Trek Gale_DEM_SMG_1m",
    "url": "https://trek.nasa.gov/mars/trekarcgis/rest/services/Gale_DEM_SMG_1m/ImageServer",
    "native_resolution_m": 1.0,
    "method": "DEM Float32 interpolado bilinealmente a la cuadrícula de ruta",
}

GALE_DEM_EXPORT_URL = f"{GALE_TERRAIN_SOURCE['url']}/exportImage"
MSL_WAYPOINTS_URL = "https://mars.nasa.gov/mmgis-maps/MSL/Layers/json/MSL_waypoints.json"


def fetch_or_cache_curiosity_waypoints(cache_dir: Optional[str] = None) -> list:
    """
    Downloads or retrieves cached NASA MMGIS 3D waypoints for the Curiosity rover.
    Each waypoint includes (lon, lat, elev_geoid, sol, tilt, roll, pitch).
    """
    if cache_dir is None:
        cache_dir = os.path.dirname(__file__)

    cache_file = os.path.join(cache_dir, "curiosity_waypoints_cache.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    try:
        resp = requests.get(MSL_WAYPOINTS_URL, timeout=8)
        if resp.status_code == 200:
            data = resp.json().get("features", [])
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return data
    except Exception as e:
        print(f"[WARN] Could not fetch live MSL waypoints ({e}).")

    return []


@lru_cache(maxsize=8)
def _fetch_gale_elevation(
    resolution_rows: int,
    resolution_cols: int,
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
) -> np.ndarray:
    params = {
        "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "bboxSR": "104905",
        "imageSR": "104905",
        "size": f"{resolution_cols},{resolution_rows}",
        "format": "tiff",
        "pixelType": "F32",
        "interpolation": "RSP_BilinearInterpolation",
        "f": "image",
    }

    try:
        response = requests.get(GALE_DEM_EXPORT_URL, params=params, timeout=45)
        response.raise_for_status()
        elevation = np.asarray(tifffile.imread(BytesIO(response.content))).squeeze()
    except (requests.RequestException, ValueError, OSError) as error:
        raise TerrainDataError(f"Could not load the NASA Gale DEM: {error}") from error

    if elevation.shape != (resolution_rows, resolution_cols):
        raise TerrainDataError(
            f"NASA Gale DEM returned shape {elevation.shape}; "
            f"expected {(resolution_rows, resolution_cols)}."
        )
    if not np.issubdtype(elevation.dtype, np.number):
        raise TerrainDataError("NASA Gale DEM did not contain numeric elevation values.")
    elevation = elevation.astype(np.float32, copy=False)
    if not np.isfinite(elevation).all() or np.any((elevation < -10000) | (elevation > 10000)):
        raise TerrainDataError("NASA Gale DEM contains missing or invalid elevation values.")

    elevation.setflags(write=False)
    return elevation


def generate_gale_crater_elevation_grid(
    resolution_rows: int = 100,
    resolution_cols: int = 100,
    min_lat: float = GALE_MIN_LAT,
    max_lat: float = GALE_MAX_LAT,
    min_lon: float = GALE_MIN_LON,
    max_lon: float = GALE_MAX_LON,
) -> ElevationGrid:
    """Load NASA Mars Trek's approximately 1 m Gale DEM onto the route grid."""
    if resolution_rows < 2 or resolution_cols < 2:
        raise ValueError("Terrain grid dimensions must both be at least 2.")
    if not (GALE_MIN_LAT <= min_lat < max_lat <= GALE_MAX_LAT):
        raise ValueError("Requested latitude bounds fall outside the Gale DEM corridor.")
    if not (GALE_MIN_LON <= min_lon < max_lon <= GALE_MAX_LON):
        raise ValueError("Requested longitude bounds fall outside the Gale DEM corridor.")

    elevation = _fetch_gale_elevation(
        resolution_rows,
        resolution_cols,
        min_lat,
        max_lat,
        min_lon,
        max_lon,
    )
    return ElevationGrid(
        elevation=elevation,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
    )
