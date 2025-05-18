from dataclasses import dataclass
import gzip
from pathlib import Path
from self_tracking.dirs import diary_dir
import xml.etree.ElementTree as ET

import folium


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


routes = [Route(fp) for fp in diary_dir.glob("data/routes/*.gpx.gz")]


# %%
center_point = (51.44919535475215, -2.608414238285152)
map = folium.Map(tiles=None, location=center_point, zoom_start=12)

map.add_child(
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
        name="Satellite",
        show=True,
    )
)
map.add_child(folium.TileLayer("CartoDB VoyagerNoLabels", name="Colour", show=False))
map.add_child(
    folium.TileLayer("CartoDB PositronNoLabels", name="Greyscale", show=False)
)

activity_colors: list[tuple[str, str, bool]] = [
    ("cycling", "#FF00FF", True),
    ("running", "#00FFFF", False),
    ("walking", "#FFA500", False),
]

for activity, color, show in activity_colors:
    group = folium.FeatureGroup(name=activity.title(), show=show)
    for route in routes:
        if route.activity == activity:
            folium.PolyLine(
                route.path,
                weight=5,
                opacity=0.6,
                color=color,
                tooltip=route.date,
            ).add_to(group)
    group.add_to(map)

map.add_child(
    folium.TileLayer(
        "WaymarkedTrails.cycling", name="Cycling trails", show=False, overlay=True
    )
)
map.add_child(
    folium.TileLayer(
        "WaymarkedTrails.hiking", name="Hiking trails", show=False, overlay=True
    )
)
map.add_child(
    folium.TileLayer(
        "CartoDB PositronOnlyLabels", name="Place names", show=False, overlay=True
    )
)

folium.LayerControl(collapsed=False).add_to(map)

map.show_in_browser()
