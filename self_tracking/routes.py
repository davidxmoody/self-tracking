from datetime import date
import gzip
import math
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

import geobuf
import numpy as np
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from yaspin import yaspin

from self_tracking.dirs import diary_dir

# %%
routes_dir = diary_dir / "data/routes"
asset_path = Path(__file__).parent / "dashboard/assets/routes.pbf"

# Douglas-Peucker tolerance in metres. Keeps ~7% of trackpoints with no
# visible difference at any usable zoom level.
simplify_tolerance = 2.0

# Decimal places kept in the output. 5dp is ~1m, matching the tolerance.
coordinate_precision = 5

epoch = date(1970, 1, 1)


# %%
def read_trackpoints(filepath: Path) -> np.ndarray:
    """Parse a gzipped GPX file into an (n, 2) array of (lon, lat)."""
    with gzip.open(filepath) as file:
        root = ET.parse(file).getroot()
        return np.array(
            [
                (float(p.attrib["lon"]), float(p.attrib["lat"]))
                for p in root.iter()
                if p.tag.endswith("trkpt")
            ]
        )


def to_metres(points: np.ndarray) -> np.ndarray:
    """Equirectangular projection so tolerances and distances are in metres."""
    mean_lat = math.radians(points[:, 1].mean())
    return np.column_stack(
        [
            points[:, 0] * 111320 * math.cos(mean_lat),
            points[:, 1] * 110540,
        ]
    )


def simplify(points: np.ndarray, tolerance: float) -> np.ndarray:
    """Douglas-Peucker, iterative to avoid recursion limits on long tracks."""
    if len(points) < 3:
        return points

    projected = to_metres(points)
    keep = np.zeros(len(points), dtype=bool)
    keep[0] = keep[-1] = True

    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        if end <= start + 1:
            continue

        a, b = projected[start], projected[end]
        segment = projected[start + 1 : end]
        ab = b - a
        squared_length = ab @ ab

        if squared_length == 0:
            distances = np.hypot(*(segment - a).T)
        else:
            t = np.clip((segment - a) @ ab / squared_length, 0, 1)
            distances = np.hypot(*(segment - (a + t[:, None] * ab)).T)

        furthest = int(distances.argmax())
        if distances[furthest] > tolerance:
            split = start + 1 + furthest
            keep[split] = True
            stack.append((start, split))
            stack.append((split, end))

    return points[keep]


def total_distance(points: np.ndarray) -> float:
    """Track length in km, measured on the full (unsimplified) track."""
    projected = to_metres(points)
    steps = np.hypot(*np.diff(projected, axis=0).T)
    return float(steps.sum() / 1000)


# %%
def build_feature(filepath: Path) -> dict | None:
    (day, clock, activity) = filepath.name[: -len(".gpx.gz")].split("_")

    points = read_trackpoints(filepath)
    if len(points) < 2:
        return None

    simplified = simplify(points, simplify_tolerance).round(coordinate_precision)

    return {
        "type": "Feature",
        "properties": {
            "date": day,
            "time": clock.replace("-", ":")[:-3],
            "day": (date.fromisoformat(day) - epoch).days,
            "activity": activity,
            "distance": round(total_distance(points), 2),
        },
        "geometry": {
            "type": "LineString",
            "coordinates": simplified.tolist(),
        },
    }


def write_asset(features: dict[Path, dict]):
    collection = {
        "type": "FeatureCollection",
        "features": [features[fp] for fp in sorted(features)],
    }
    encoded = geobuf.encode(collection, coordinate_precision, 2)
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(encoded)

    points = sum(len(f["geometry"]["coordinates"]) for f in collection["features"])
    print(
        f"Wrote {asset_path} "
        f"({len(collection['features'])} routes, {points} points, "
        f"{len(encoded) / 1e6:.2f} MB)"
    )


def build_all() -> dict[Path, dict]:
    filepaths = sorted(routes_dir.glob("*.gpx.gz"))
    features: dict[Path, dict] = {}

    with yaspin(text=f"Parsing {len(filepaths)} routes") as spinner:
        for filepath in filepaths:
            feature = build_feature(filepath)
            if feature is not None:
                features[filepath] = feature
        spinner.ok("✓")

    write_asset(features)
    return features


# %%
class RouteHandler(FileSystemEventHandler):
    def __init__(self, features: dict[Path, dict]):
        self.features = features

    def on_created(self, event):
        filepath = Path(str(event.src_path))
        if filepath.suffixes[-2:] != [".gpx", ".gz"] or filepath in self.features:
            return

        print(f"New route detected: {filepath.name}")
        try:
            # Give the writer a moment to finish flushing the file
            time.sleep(1)
            feature = build_feature(filepath)
        except Exception as e:
            print(f"Failed to load new route {filepath.name}: {e}")
            return

        if feature is not None:
            self.features[filepath] = feature
            write_asset(self.features)


def watch(features: dict[Path, dict]):
    observer = Observer()
    observer.schedule(RouteHandler(features), str(routes_dir), recursive=False)
    observer.start()
    print(f"Watching {routes_dir} for new routes (ctrl-c to stop)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


# %%
def route_index() -> list[tuple[int, str]]:
    """(epoch day, activity) for every route, read from filenames alone."""
    index = []
    for filepath in sorted(routes_dir.glob("*.gpx.gz")):
        (day, _, activity) = filepath.name[: -len(".gpx.gz")].split("_")
        index.append(((date.fromisoformat(day) - epoch).days, activity))
    return index


def to_date(day: int) -> date:
    return date.fromordinal(epoch.toordinal() + day)


# %%
if __name__ == "__main__":
    features = build_all()
    if "--watch" in sys.argv:
        watch(features)
