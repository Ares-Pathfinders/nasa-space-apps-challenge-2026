from functools import lru_cache
from pathlib import Path
from typing import Tuple

import numpy as np
import tifffile

from ..terrain.grid import ElevationGrid

JEZERO_SLOPE_TIFF = (
    Path(__file__).parent
    / "J03_045994_1986_J03_046060_1986_20m_slope_20m.tif"
)


@lru_cache(maxsize=1)
def _load_slope_raster() -> Tuple[np.ndarray, float, float, float, float, float, float, float]:
    with tifffile.TiffFile(JEZERO_SLOPE_TIFF) as image:
        page = image.pages[0]
        slope_values = page.asarray().astype(np.float32, copy=False)
        pixel_scale_x, pixel_scale_y, _ = page.tags["ModelPixelScaleTag"].value
        _, _, _, origin_x, origin_y, _ = page.tags["ModelTiepointTag"].value
        geo_keys = page.tags["GeoKeyDirectoryTag"].value
        double_params = page.tags["GeoDoubleParamsTag"].value
        ascii_params = page.tags["GeoAsciiParamsTag"].value

    key_entries = {
        geo_keys[offset]: (
            geo_keys[offset + 1],
            geo_keys[offset + 2],
            geo_keys[offset + 3],
        )
        for offset in range(4, 4 + 4 * geo_keys[3], 4)
    }
    projection_type = key_entries.get(3075, (0, 0, 0))[2]
    if projection_type != 17 or "Equirectangular Mars" not in ascii_params:
        raise ValueError("Jezero slope raster must use the Equirectangular Mars projection.")

    def double_key(key_id: int) -> float:
        location, count, offset = key_entries[key_id]
        if location != 34736 or count != 1:
            raise ValueError(f"Unexpected GeoTIFF encoding for key {key_id}.")
        return float(double_params[offset])

    center_lat = double_key(3089)
    center_lon = double_key(3088)
    mars_radius_m = double_key(2057)
    if (
        slope_values.ndim != 2
        or pixel_scale_x <= 0
        or pixel_scale_y <= 0
        or mars_radius_m <= 0
    ):
        raise ValueError("Jezero slope raster has invalid dimensions or georeferencing.")

    slope_values = slope_values.copy()
    slope_values[
        ~np.isfinite(slope_values) | (slope_values < 0) | (slope_values > 90)
    ] = np.nan
    slope_values.setflags(write=False)
    return (
        slope_values,
        float(pixel_scale_x),
        float(pixel_scale_y),
        float(origin_x),
        float(origin_y),
        center_lat,
        center_lon,
        mars_radius_m,
    )


def resample_jezero_slope_to_grid(grid: ElevationGrid) -> np.ndarray:
    """Return the maximum measured slope in each route cell; uncovered cells are NaN."""
    (
        raster,
        pixel_scale_x,
        pixel_scale_y,
        origin_x,
        origin_y,
        center_lat,
        center_lon,
        mars_radius_m,
    ) = _load_slope_raster()
    rows, cols = raster.shape
    result = np.full(grid.shape, np.nan, dtype=np.float64)

    for row in range(grid.rows):
        latitude = grid.max_lat - row * grid.dlat_deg
        min_lat = max(grid.min_lat, latitude - grid.dlat_deg / 2)
        max_lat = min(grid.max_lat, latitude + grid.dlat_deg / 2)
        y_min = mars_radius_m * np.radians(min_lat - center_lat)
        y_max = mars_radius_m * np.radians(max_lat - center_lat)
        raster_row_start = max(0, int(np.floor((origin_y - y_max) / pixel_scale_y)))
        raster_row_end = min(rows, int(np.ceil((origin_y - y_min) / pixel_scale_y)))

        for col in range(grid.cols):
            longitude = grid.min_lon + col * grid.dlon_deg
            min_lon = max(grid.min_lon, longitude - grid.dlon_deg / 2)
            max_lon = min(grid.max_lon, longitude + grid.dlon_deg / 2)
            x_min = mars_radius_m * np.radians(min_lon - center_lon)
            x_max = mars_radius_m * np.radians(max_lon - center_lon)
            raster_col_start = max(
                0, int(np.floor((x_min - origin_x) / pixel_scale_x))
            )
            raster_col_end = min(
                cols, int(np.ceil((x_max - origin_x) / pixel_scale_x))
            )

            if raster_row_start >= raster_row_end or raster_col_start >= raster_col_end:
                continue
            cell_values = raster[
                raster_row_start:raster_row_end,
                raster_col_start:raster_col_end,
            ]
            valid_values = cell_values[np.isfinite(cell_values)]
            if valid_values.size == cell_values.size:
                result[row, col] = float(np.max(valid_values))

    return result
