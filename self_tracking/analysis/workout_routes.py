from dataclasses import dataclass
import gzip
from pathlib import Path
from typing import cast
from self_tracking.dirs import diary_dir
import xml.etree.ElementTree as ET
import folium
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import tempfile
import webbrowser


# %%
routes_dir = diary_dir / "data/routes"
map_file = Path(tempfile.gettempdir()) / "routes_map.html"


# %%
@dataclass
class Route:
    date: str
    time: str
    activity: str
    path: list[tuple[float, float]]

    def __init__(self, filepath: Path):
        (self.date, time, self.activity) = filepath.name[:-7].split("_")
        self.time = time.replace("-", ":")[:-3]

        with gzip.open(filepath) as file:
            root = ET.parse(file).getroot()
            self.path = [
                (float(p.attrib["lat"]), float(p.attrib["lon"]))
                for p in root.iter()
                if p.tag.endswith("trkpt")
            ]


routes: dict[Path, Route] = {fp: Route(fp) for fp in routes_dir.glob("*.gpx.gz")}


# %%
def build_map() -> folium.Map:
    center_point = (51.44919535475215, -2.608414238285152)
    fmap = folium.Map(tiles=None, location=center_point, zoom_start=12)

    fmap.add_child(
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
            name="Satellite",
            show=True,
        )
    )
    fmap.add_child(
        folium.TileLayer("CartoDB VoyagerNoLabels", name="Colour", show=False)
    )
    fmap.add_child(
        folium.TileLayer("CartoDB PositronNoLabels", name="Greyscale", show=False)
    )

    activity_colors: list[tuple[str, str, bool]] = [
        ("cycling", "#FF00FF", True),
        ("running", "#00FFFF", False),
        ("walking", "#FFA500", False),
    ]

    for activity, color, show in activity_colors:
        group = folium.FeatureGroup(name=activity.title(), show=show)
        for route in routes.values():
            if route.activity == activity:
                folium.PolyLine(
                    route.path,
                    weight=5,
                    opacity=0.6,
                    color=color,
                    tooltip=route.date,
                ).add_to(group)
        group.add_to(fmap)

    fmap.add_child(
        folium.TileLayer(
            "WaymarkedTrails.cycling", name="Cycling trails", show=False, overlay=True
        )
    )
    fmap.add_child(
        folium.TileLayer(
            "WaymarkedTrails.hiking", name="Hiking trails", show=False, overlay=True
        )
    )
    fmap.add_child(
        folium.TileLayer(
            "CartoDB PositronOnlyLabels", name="Place names", show=False, overlay=True
        )
    )

    folium.LayerControl(collapsed=False).add_to(fmap)

    return fmap


def save_map():
    fmap = build_map()
    fmap.save(str(map_file))
    print(f"Map saved: {map_file}")


# %%
class RouteHandler(FileSystemEventHandler):
    def on_created(self, event):
        src_path = cast(str, event.src_path)
        if src_path.endswith(".gpx.gz"):
            fp = Path(src_path)
            if fp not in routes:
                print(f"New route detected: {fp.name}")
                try:
                    time.sleep(1) # Hack to prevent attempting to read file before it's fully written
                    routes[fp] = Route(fp)
                except Exception as e:
                    print(f"Failed to load new route {fp}: {e}")
            save_map()


# %%
if __name__ == "__main__":
    save_map()

    webbrowser.open(f"file://{map_file}")

    event_handler = RouteHandler()
    observer = Observer()
    observer.schedule(event_handler, str(routes_dir), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
