import os
import json
from functools import lru_cache
from typing import Optional, Tuple
import numpy as np
import requests
from scipy.ndimage import map_coordinates, percentile_filter

from ..terrain.grid import ElevationGrid
from ..terrain.slope import SlopeAnalyzer
from .terrain_errors import TerrainDataError

# Relieve real del cráter Gale: el mismo modelo STL que usa la vista 3D del visor
# táctico (frontend/src/tactical/terrain3d.ts). El STL no trae coordenadas; se
# georreferenció ajustándolo al DEM MOLA/HRSC blend de 200 m (correlación 0,9998).
# Es una rejilla de 513x513 alturas con el norte hacia +Y y
# z_stl = GALE_STL_ELEV_SCALE * elevación_m + GALE_STL_ELEV_OFFSET.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GALE_STL_PATH = os.path.join(REPO_ROOT, "frontend", "public", "models", "gale_crater.stl")
GALE_STL_GRID = 513
GALE_STL_ELEV_SCALE = 0.00147483  # unidades STL por metro
GALE_STL_ELEV_OFFSET = 8.426

# La retícula cubre todo el modelo 3D (cráter Gale completo, ~210 x 275 km).
GALE_MIN_LAT = -7.84402
GALE_MAX_LAT = -3.21708
GALE_MIN_LON = 135.97957
GALE_MAX_LON = 139.49492

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
        print(f"[WARN] Could not fetch live MSL waypoints ({e}), using synthetic topography.")

    return []


@lru_cache(maxsize=1)
def _load_gale_stl_terrain() -> Tuple[np.ndarray, np.ndarray]:
    """
    Lee el STL binario y devuelve (elevación_m, pendiente_deg) a resolución nativa
    (513x513, fila 0 = norte). La pendiente se calcula con el método de Horn sobre
    las alturas reales (sin exageración vertical).
    """
    try:
        with open(GALE_STL_PATH, "rb") as stl_file:
            stl_file.seek(80)
            triangle_count = int(np.frombuffer(stl_file.read(4), dtype="<u4")[0])
            triangles = np.frombuffer(
                stl_file.read(50 * triangle_count),
                dtype=np.dtype([("normal", "<f4", 3), ("vertices", "<f4", (3, 3)), ("attr", "<u2")]),
            )
    except (OSError, IndexError, ValueError) as error:
        raise TerrainDataError(f"No se pudo leer el modelo STL de Gale ({GALE_STL_PATH}): {error}") from error

    vertices = triangles["vertices"].reshape(-1, 3).astype(np.float64)
    surface = vertices[vertices[:, 2] > 0]  # descarta la base plana del sólido
    if surface.size == 0:
        raise TerrainDataError("El modelo STL de Gale no contiene superficie de relieve.")

    n = GALE_STL_GRID
    x, y, z = surface[:, 0], surface[:, 1], surface[:, 2]
    cols = np.rint((x - x.min()) / (x.max() - x.min()) * (n - 1)).astype(int)
    rows_from_south = np.rint((y - y.min()) / (y.max() - y.min()) * (n - 1)).astype(int)
    stl_height = np.full((n, n), np.nan)
    stl_height[(n - 1) - rows_from_south, cols] = z
    if np.isnan(stl_height).any():
        raise TerrainDataError("El modelo STL de Gale no es una rejilla regular de 513x513 alturas.")

    elevation = (stl_height - GALE_STL_ELEV_OFFSET) / GALE_STL_ELEV_SCALE
    native_grid = ElevationGrid(
        elevation=elevation,
        min_lat=GALE_MIN_LAT,
        max_lat=GALE_MAX_LAT,
        min_lon=GALE_MIN_LON,
        max_lon=GALE_MAX_LON,
    )
    slope = SlopeAnalyzer(native_grid).slope_deg_matrix
    return elevation, slope


@lru_cache(maxsize=8)
def _footprint_slope(window_rows: int, window_cols: int) -> np.ndarray:
    """Percentil 75 de la pendiente nativa en una ventana del tamaño de la celda."""
    _, slope = _load_gale_stl_terrain()
    return percentile_filter(slope, 75, size=(window_rows, window_cols), mode="nearest")


def generate_gale_crater_elevation_grid(
    resolution_rows: int = 100,
    resolution_cols: int = 100,
    min_lat: float = GALE_MIN_LAT,
    max_lat: float = GALE_MAX_LAT,
    min_lon: float = GALE_MIN_LON,
    max_lon: float = GALE_MAX_LON,
) -> ElevationGrid:
    """
    Retícula de elevación del cráter Gale a partir del modelo 3D (STL) georreferenciado.

    - La elevación de cada celda se interpola bilinealmente en el relieve del STL.
    - La pendiente de cada celda es el percentil 75 de las pendientes reales del STL
      dentro de la huella de la celda: una celda gruesa no "suaviza" una pared
      escarpada, pero un único píxel ruidoso tampoco la bloquea. Va en
      ``ElevationGrid.slope_deg`` y la usa SlopeAnalyzer.
    """
    if resolution_rows < 2 or resolution_cols < 2:
        raise ValueError("La retícula necesita al menos 2x2 celdas.")
    elevation, slope = _load_gale_stl_terrain()
    n = GALE_STL_GRID

    lats = np.linspace(max_lat, min_lat, resolution_rows)  # fila 0 = norte
    lons = np.linspace(min_lon, max_lon, resolution_cols)  # columna 0 = oeste
    native_rows = (GALE_MAX_LAT - lats) / (GALE_MAX_LAT - GALE_MIN_LAT) * (n - 1)
    native_cols = (lons - GALE_MIN_LON) / (GALE_MAX_LON - GALE_MIN_LON) * (n - 1)
    row_grid, col_grid = np.meshgrid(native_rows, native_cols, indexing="ij")
    cell_elevation = map_coordinates(elevation, [row_grid, col_grid], order=1, mode="nearest")

    # Huella de una celda en píxeles nativos (semiancho redondeado hacia arriba).
    half_rows = int(np.ceil(abs(native_rows[1] - native_rows[0]) / 2))
    half_cols = int(np.ceil(abs(native_cols[1] - native_cols[0]) / 2))
    footprint_slope = _footprint_slope(2 * half_rows + 1, 2 * half_cols + 1)
    cell_slope = footprint_slope[
        np.clip(np.rint(row_grid).astype(int), 0, n - 1),
        np.clip(np.rint(col_grid).astype(int), 0, n - 1),
    ]

    return ElevationGrid(
        elevation=cell_elevation,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        slope_deg=cell_slope,
    )
