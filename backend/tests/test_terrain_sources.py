from io import BytesIO
from unittest.mock import Mock, patch

import numpy as np
import tifffile

from backend.data import gale_crater_topography as gale
from backend.data import jezero_crater_topography as jezero
from backend.terrain.cell_graph import CellGraphBuilder
from backend.terrain.slope import SlopeAnalyzer


def test_gale_grid_covers_the_whole_3d_model_with_real_elevations():
    grid = gale.generate_gale_crater_elevation_grid(resolution_rows=64, resolution_cols=64)

    assert (grid.min_lat, grid.max_lat) == (gale.GALE_MIN_LAT, gale.GALE_MAX_LAT)
    assert (grid.min_lon, grid.max_lon) == (gale.GALE_MIN_LON, gale.GALE_MAX_LON)
    # Suelo de Gale (~-4,6 km) y borde/tierras altas (~+1,4 km) según MOLA/HRSC.
    assert -4800 < grid.elevation.min() < -4400
    assert 1000 < grid.elevation.max() < 1600
    # El norte va arriba: Monte Sharp (sur) más alto que Bradbury Landing (norte).
    bradbury = grid.get_elevation(*grid.geo_to_cell(-4.5895, 137.4417))
    mount_sharp = grid.get_elevation(*grid.geo_to_cell(-5.08, 137.85))
    assert -4700 < bradbury < -4300
    assert mount_sharp > bradbury + 2500


def test_gale_slopes_come_from_the_native_3d_model():
    grid = gale.generate_gale_crater_elevation_grid(resolution_rows=128, resolution_cols=128)
    analyzer = SlopeAnalyzer(grid, max_slope_deg=15.0)

    assert grid.slope_deg is not None
    np.testing.assert_array_equal(analyzer.slope_deg_matrix, grid.slope_deg)
    assert analyzer.is_cell_passable(*grid.geo_to_cell(-4.5895, 137.4417))  # llanura de Bradbury
    stats = analyzer.get_statistics()
    assert 2.0 < stats["impassable_percentage"] < 25.0
    assert stats["max_slope_deg"] > 25.0  # paredes del cráter y del Monte Sharp

    builder = CellGraphBuilder(grid, analyzer, slope_penalty_weight=3.5)
    route = builder.find_path_astar(grid.geo_to_cell(-4.5895, 137.4417), grid.geo_to_cell(-4.90, 137.45))
    assert route is not None
    assert route["max_path_slope_deg"] <= 15.0
    assert route["elevation_gain_m"] > 500


def test_default_jezero_grid_covers_expanded_expedition_area():
    jezero_grid = jezero.generate_jezero_crater_elevation_grid(resolution_rows=4, resolution_cols=4)

    assert (jezero_grid.min_lat, jezero_grid.max_lat) == (jezero.JEZERO_MIN_LAT, jezero.JEZERO_MAX_LAT)
    assert (jezero_grid.min_lon, jezero_grid.max_lon) == (jezero.JEZERO_MIN_LON, jezero.JEZERO_MAX_LON)


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
