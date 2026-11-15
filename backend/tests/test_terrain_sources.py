import math
from io import BytesIO
from unittest.mock import Mock, patch

import numpy as np
import tifffile

from backend.data import gale_crater_topography as gale
from backend.data import jezero_crater_topography as jezero


def test_gale_grid_uses_float32_elevation_from_nasa_export():
    expected = np.array(
        [[-4410.0, -4405.0], [-4388.0, -4379.0]],
        dtype=np.float32,
    )
    image = BytesIO()
    tifffile.imwrite(image, expected)
    response = Mock(content=image.getvalue())

    gale._fetch_gale_elevation.cache_clear()
    with patch.object(gale.requests, "get", return_value=response) as get:
        grid = gale.generate_gale_crater_elevation_grid(
            resolution_rows=2,
            resolution_cols=2,
        )

    np.testing.assert_array_equal(grid.elevation, expected)
    assert get.call_args.args[0] == gale.GALE_DEM_EXPORT_URL
    assert get.call_args.kwargs["params"]["pixelType"] == "F32"


def test_default_grids_cover_expanded_expedition_areas():
    for module, grid, base_bounds in (
        (
            gale,
            gale.generate_gale_crater_elevation_grid(),
            (
                gale.GALE_BASE_MIN_LAT,
                gale.GALE_BASE_MAX_LAT,
                gale.GALE_BASE_MIN_LON,
                gale.GALE_BASE_MAX_LON,
                gale.GALE_CENTER_LAT,
            ),
        ),
        (
            jezero,
            jezero.generate_jezero_crater_elevation_grid(),
            (
                jezero.JEZERO_BASE_MIN_LAT,
                jezero.JEZERO_BASE_MAX_LAT,
                jezero.JEZERO_BASE_MIN_LON,
                jezero.JEZERO_BASE_MAX_LON,
                jezero.JEZERO_CENTER_LAT,
            ),
        ),
    ):
        base_min_lat, base_max_lat, base_min_lon, base_max_lon, center_lat = base_bounds
        lat_margin_km = math.radians(base_min_lat - grid.min_lat) * module.MARS_RADIUS_KM
        lon_margin_km = (
            math.radians(base_min_lon - grid.min_lon)
            * module.MARS_RADIUS_KM
            * math.cos(math.radians(center_lat))
        )

        assert math.isclose(lat_margin_km, 25.0, abs_tol=1e-9)
        assert math.isclose(lon_margin_km, 25.0, abs_tol=1e-9)
        assert math.isclose(
            math.radians(grid.max_lat - base_max_lat) * module.MARS_RADIUS_KM,
            25.0,
            abs_tol=1e-9,
        )
        assert math.isclose(
            math.radians(grid.max_lon - base_max_lon)
            * module.MARS_RADIUS_KM
            * math.cos(math.radians(center_lat)),
            25.0,
            abs_tol=1e-9,
        )


def test_jezero_pds_range_decodes_little_endian_float_and_skips_nodata():
    product = {
        "url": "https://example.test/DTM.IMG",
        "SCALING_FACTOR": 2.0,
        "OFFSET": -1.0,
    }
    span = {
        "start": 100,
        "end": 107,
        "first_sample": 4,
        "last_sample": 5,
        "cells_by_sample": {4: [7], 5: [8]},
    }
    payload = np.array([5.0, -3.4028235e38], dtype="<f4").tobytes()
    response = Mock(
        status_code=206,
        headers={"Content-Range": "bytes 100-107/1000"},
        content=payload,
    )
    session = Mock()
    session.get.return_value = response

    with patch.object(jezero, "_session", return_value=session):
        samples = jezero._read_range_batch((2, product, [span]))

    assert samples == [(7, 2, 9.0)]


def test_jezero_pds_label_parses_projection_and_image_offset():
    label = """
RECORD_BYTES = 32940
^IMAGE = 2
LINES = 21258
LINE_SAMPLES = 8235
SAMPLE_BITS = 32
SAMPLE_TYPE = PC_REAL
SCALING_FACTOR = 1.0
OFFSET = 0.0
MAP_PROJECTION_TYPE = EQUIRECTANGULAR
CENTER_LATITUDE = 18.4
CENTER_LONGITUDE = 77.5
MAP_RESOLUTION = 58600.0
MAP_SCALE = 1.01
LINE_PROJECTION_OFFSET = 1080000
SAMPLE_PROJECTION_OFFSET = 4200
END
"""

    product = jezero._parse_product_label(label, "https://example.test/DTM.IMG")

    assert product["image_offset"] == 32940
    assert product["line_samples"] == 8235
    assert jezero._pixel_for_coordinate(product, 18.4, 77.5) == (1759, 4199)
