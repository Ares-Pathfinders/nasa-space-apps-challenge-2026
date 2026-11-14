import email
import email.policy
import math
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from scipy.ndimage import distance_transform_edt

from ..terrain.grid import ElevationGrid
from .terrain_errors import TerrainDataError

JEZERO_MIN_LAT = 18.270
JEZERO_MAX_LAT = 18.490
JEZERO_MIN_LON = 77.445
JEZERO_MAX_LON = 77.655

_PDS_ROOT = "https://hirise-pds.lpl.arizona.edu/PDS/"
_PRODUCT_PATHS = (
    "DTM/ESP/ORB_023500_023599/ESP_023524_1985_ESP_023379_1985/DTEEC_023524_1985_023379_1985_U01.IMG",
    "DTM/ESP/ORB_023200_023299/ESP_023247_1985_ESP_022957_1985/DTEEC_023247_1985_022957_1985_U01.IMG",
    "DTM/ESP/ORB_045900_045999/ESP_045994_1985_ESP_046060_1985/DTEEC_045994_1985_046060_1985_U01.IMG",
    "DTM/ESP/ORB_022600_022699/ESP_022680_1985_ESP_022746_1985/DTEEC_022680_1985_022746_1985_A01.IMG",
)
_LABEL_FIELDS = (
    "RECORD_BYTES",
    "^IMAGE",
    "LINES",
    "LINE_SAMPLES",
    "SAMPLE_BITS",
    "SAMPLE_TYPE",
    "SCALING_FACTOR",
    "OFFSET",
    "MAP_PROJECTION_TYPE",
    "CENTER_LATITUDE",
    "CENTER_LONGITUDE",
    "MAP_RESOLUTION",
    "MAP_SCALE",
    "LINE_PROJECTION_OFFSET",
    "SAMPLE_PROJECTION_OFFSET",
)
_THREAD_LOCAL = threading.local()

JEZERO_TERRAIN_SOURCE = {
    "name": "NASA PDS HiRISE DTM stereo products",
    "url": "https://hirise-pds.lpl.arizona.edu/PDS/DTM/ESP/",
    "native_resolution_m": 1.01,
    "products": [path.rsplit("/", 1)[-1].removesuffix(".IMG") for path in _PRODUCT_PATHS],
    "method": "Muestras Float32 del DTM de cobertura más cercana; los huecos aislados usan la muestra válida más próxima",
}


def _session() -> requests.Session:
    session = getattr(_THREAD_LOCAL, "session", None)
    if session is None:
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.25,
            status_forcelist=(429, 500, 502, 503, 504),
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=1, pool_maxsize=1)
        session = requests.Session()
        session.mount("https://", adapter)
        _THREAD_LOCAL.session = session
    return session


def _parse_product_label(label: str, url: str) -> dict:
    fields = {}
    for key in _LABEL_FIELDS:
        match = re.search(
            r"^\s*" + re.escape(key) + r"\s*=\s*([^\r\n/]+)",
            label,
            re.MULTILINE,
        )
        if match:
            fields[key] = match.group(1).strip().split("<", 1)[0].strip().strip('"')
    missing = [key for key in _LABEL_FIELDS if key not in fields]
    if missing:
        raise ValueError(f"{url} label is missing {', '.join(missing)}.")
    if fields["SAMPLE_TYPE"] != "PC_REAL" or fields["MAP_PROJECTION_TYPE"] != "EQUIRECTANGULAR":
        raise ValueError(f"{url} does not use the expected PC_REAL equirectangular format.")

    product = {
        key: float(value)
        for key, value in fields.items()
        if key not in ("SAMPLE_TYPE", "MAP_PROJECTION_TYPE", "^IMAGE", "RECORD_BYTES", "LINES", "LINE_SAMPLES", "SAMPLE_BITS")
    }
    product.update({
        "url": url,
        "record_bytes": int(fields["RECORD_BYTES"]),
        "image_record": int(fields["^IMAGE"]),
        "lines": int(fields["LINES"]),
        "line_samples": int(fields["LINE_SAMPLES"]),
        "sample_bits": int(fields["SAMPLE_BITS"]),
    })
    if product["sample_bits"] != 32:
        raise ValueError(f"{url} has unsupported {product['sample_bits']}-bit samples.")
    product["image_offset"] = (product["image_record"] - 1) * product["record_bytes"]
    return product


@lru_cache(maxsize=1)
def _load_products() -> tuple:
    products = []
    for path in _PRODUCT_PATHS:
        url = _PDS_ROOT + path
        response = _session().get(
            url,
            headers={"Range": "bytes=0-65535"},
            timeout=(10, 30),
            stream=True,
        )
        response.raise_for_status()
        if response.status_code != 206:
            response.close()
            raise ValueError(f"{url} did not honor the PDS label byte-range request.")
        if not response.headers.get("Content-Range", "").startswith("bytes 0-"):
            response.close()
            raise ValueError(f"{url} returned an invalid PDS label byte range.")
        label = response.content.decode("ascii", errors="ignore")
        response.close()
        label_end = re.search(r"(?m)^\s*END\s*$", label)
        if label_end:
            label = label[:label_end.end()]
        products.append(_parse_product_label(label, url))
    return tuple(products)


def _pixel_for_coordinate(product: dict, latitude: float, longitude: float):
    line = round(
        product["LINE_PROJECTION_OFFSET"]
        - latitude * product["MAP_RESOLUTION"]
    ) - 1
    sample = round(
        product["SAMPLE_PROJECTION_OFFSET"]
        + (longitude - product["CENTER_LONGITUDE"])
        * product["MAP_RESOLUTION"]
        * math.cos(math.radians(product["CENTER_LATITUDE"]))
    ) - 1
    if not (0 <= line < product["lines"] and 0 <= sample < product["line_samples"]):
        return None
    return line, sample


def _read_range_batch(batch: tuple) -> list:
    product_index, product, spans = batch
    ranges = ",".join(f"{span['start']}-{span['end']}" for span in spans)
    response = _session().get(
        product["url"],
        headers={"Range": f"bytes={ranges}"},
        timeout=(10, 45),
        stream=True,
    )
    response.raise_for_status()
    if response.status_code != 206:
        response.close()
        raise ValueError(f"{product['url']} did not honor a PDS image byte-range request.")

    if len(spans) == 1:
        content_range = response.headers.get("Content-Range", "")
        match = re.fullmatch(r"bytes (\d+)-(\d+)/\d+", content_range)
        if not match or (int(match.group(1)), int(match.group(2))) != (spans[0]["start"], spans[0]["end"]):
            response.close()
            raise ValueError(f"{product['url']} returned an invalid image byte range.")
        bodies = {(spans[0]["start"], spans[0]["end"]): response.content}
    else:
        content_type = response.headers.get("Content-Type", "")
        message = email.message_from_bytes(
            b"MIME-Version: 1.0\r\nContent-Type: "
            + content_type.encode("ascii")
            + b"\r\n\r\n"
            + response.content,
            policy=email.policy.default,
        )
        response.close()
        if not message.is_multipart():
            raise ValueError(f"{product['url']} did not return multipart data for multiple byte ranges.")
        bodies = {}
        for part in message.iter_parts():
            content_range = part.get("Content-Range", "")
            match = re.fullmatch(r"bytes (\d+)-(\d+)/\d+", content_range)
            if not match:
                raise ValueError(f"{product['url']} returned an invalid multipart byte range.")
            key = (int(match.group(1)), int(match.group(2)))
            if key in bodies:
                raise ValueError(f"{product['url']} returned a duplicate multipart byte range.")
            bodies[key] = part.get_payload(decode=True)

    results = []
    for span in spans:
        key = (span["start"], span["end"])
        body = bodies.get(key)
        expected_length = (span["last_sample"] - span["first_sample"] + 1) * 4
        if body is None or len(body) != expected_length:
            raise ValueError(f"{product['url']} returned an incomplete elevation sample row.")
        samples = np.frombuffer(body, dtype="<f4")
        for sample, cell_indices in span["cells_by_sample"].items():
            raw_value = float(samples[sample - span["first_sample"]])
            if not math.isfinite(raw_value) or not -10000 <= raw_value <= 10000:
                continue
            value = float(
                raw_value * product["SCALING_FACTOR"] + product["OFFSET"]
            )
            if math.isfinite(value) and -10000 <= value <= 10000:
                results.extend(
                    (cell_index, product_index, value)
                    for cell_index in cell_indices
                )
    return results


@lru_cache(maxsize=8)
def _sample_jezero_elevation(
    resolution_rows: int,
    resolution_cols: int,
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
) -> np.ndarray:
    try:
        products = _load_products()
        candidates_by_cell = [[] for _ in range(resolution_rows * resolution_cols)]
        row_samples = {}

        latitudes = np.linspace(max_lat, min_lat, resolution_rows)
        longitudes = np.linspace(min_lon, max_lon, resolution_cols)
        for row, latitude in enumerate(latitudes):
            for col, longitude in enumerate(longitudes):
                cell_index = row * resolution_cols + col
                for product_index, product in enumerate(products):
                    pixel = _pixel_for_coordinate(product, latitude, longitude)
                    if pixel is None:
                        continue
                    line, sample = pixel
                    distance = (
                        ((line - (product["lines"] - 1) / 2) / product["lines"]) ** 2
                        + ((sample - (product["line_samples"] - 1) / 2) / product["line_samples"]) ** 2
                    )
                    candidates_by_cell[cell_index].append(
                        (product["MAP_SCALE"], distance, product_index, line, sample)
                    )
                    cells_by_sample = row_samples.setdefault(
                        (product_index, line), {}
                    ).setdefault(sample, [])
                    cells_by_sample.append(cell_index)

        spans_by_product = [[] for _ in products]
        for (product_index, line), cells_by_sample in row_samples.items():
            product = products[product_index]
            first_sample = min(cells_by_sample)
            last_sample = max(cells_by_sample)
            start = (
                product["image_offset"]
                + line * product["line_samples"] * 4
                + first_sample * 4
            )
            end = (
                product["image_offset"]
                + line * product["line_samples"] * 4
                + (last_sample + 1) * 4
                - 1
            )
            spans_by_product[product_index].append({
                "start": start,
                "end": end,
                "first_sample": first_sample,
                "last_sample": last_sample,
                "cells_by_sample": cells_by_sample,
            })

        batches = []
        for product_index, spans in enumerate(spans_by_product):
            for start in range(0, len(spans), 20):
                batches.append((product_index, products[product_index], spans[start:start + 20]))

        elevation_candidates = [[] for _ in candidates_by_cell]
        with ThreadPoolExecutor(max_workers=4) as executor:
            for results in executor.map(_read_range_batch, batches):
                for cell_index, product_index, value in results:
                    elevation_candidates[cell_index].append((product_index, value))

        elevation = np.full((resolution_rows, resolution_cols), np.nan, dtype=np.float32)
        missing_cells = []
        for cell_index, candidates in enumerate(candidates_by_cell):
            valid_values = elevation_candidates[cell_index]
            if not valid_values:
                missing_cells.append(cell_index)
                continue
            row, col = divmod(cell_index, resolution_cols)
            priorities = {
                product_index: (scale, distance)
                for scale, distance, product_index, _, _ in candidates
            }
            elevation[row, col] = min(
                valid_values,
                key=lambda candidate: priorities[candidate[0]],
            )[1]

        if missing_cells:
            if len(missing_cells) == elevation.size:
                raise ValueError("HiRISE DTMs contain no valid elevations in the requested corridor.")
            distances, nearest_valid = distance_transform_edt(
                ~np.isfinite(elevation),
                return_indices=True,
            )
            if np.any(distances[~np.isfinite(elevation)] > 1.5):
                raise ValueError(
                    f"HiRISE DTMs have no valid elevation samples for "
                    f"{len(missing_cells)} route-grid cells, including gaps larger than one cell."
                )
            missing_mask = ~np.isfinite(elevation)
            elevation[missing_mask] = elevation[
                nearest_valid[0][missing_mask],
                nearest_valid[1][missing_mask],
            ]
    except (requests.RequestException, UnicodeDecodeError, ValueError, KeyError) as error:
        raise TerrainDataError(f"Could not load the NASA HiRISE Jezero DTMs: {error}") from error

    elevation.setflags(write=False)
    return elevation


def generate_jezero_crater_elevation_grid(
    resolution_rows: int = 80,
    resolution_cols: int = 80,
    min_lat: float = JEZERO_MIN_LAT,
    max_lat: float = JEZERO_MAX_LAT,
    min_lon: float = JEZERO_MIN_LON,
    max_lon: float = JEZERO_MAX_LON,
) -> ElevationGrid:
    """Load real NASA PDS HiRISE stereo DTM samples for the Jezero route grid."""
    if resolution_rows < 2 or resolution_cols < 2:
        raise ValueError("Terrain grid dimensions must both be at least 2.")
    if not (JEZERO_MIN_LAT <= min_lat < max_lat <= JEZERO_MAX_LAT):
        raise ValueError("Requested latitude bounds fall outside the Jezero DTM corridor.")
    if not (JEZERO_MIN_LON <= min_lon < max_lon <= JEZERO_MAX_LON):
        raise ValueError("Requested longitude bounds fall outside the Jezero DTM corridor.")

    elevation = _sample_jezero_elevation(
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
