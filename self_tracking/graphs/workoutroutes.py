# %% Imports

from dataclasses import dataclass
from glob import glob
import gzip
from os.path import basename, expandvars
import xml.etree.ElementTree as ET

import folium


# %% Load


@dataclass
class Route:
    date: str
    time: str
    activity: str
    path: list[tuple[float, float]]

    def __init__(self, filepath: str):
        (self.date, time, self.activity) = basename(filepath)[:-7].split("_")
        self.time = time.replace("-", ":")[:-3]

        with gzip.open(filepath) as file:
            root = ET.parse(file).getroot()
            self.path = [
                (float(p.attrib["lat"]), float(p.attrib["lon"]))
                for p in root.iter()
                if p.tag.endswith("trkpt")
            ]


routes = [Route(fp) for fp in glob(expandvars("$DIARY_DIR/data/routes/*.gpx.gz"))]


# %% Map

activity_colors = {
    "running": "red",
    "cycling": "blue",
    "walking": "green",
}

map = folium.Map(tiles=None)

map.add_child(
    folium.TileLayer("CartoDB PositronNoLabels", name="Greyscale map", show=True)
)
map.add_child(
    folium.TileLayer("CartoDB VoyagerNoLabels", name="Colour map", show=False)
)
map.add_child(
    folium.TileLayer(
        "WaymarkedTrails.hiking", name="Hiking trails", show=False, overlay=True
    )
)
map.add_child(
    folium.TileLayer(
        "WaymarkedTrails.cycling", name="Cycling trails", show=False, overlay=True
    )
)
map.add_child(
    folium.TileLayer(
        "CartoDB PositronOnlyLabels", name="Place names", show=False, overlay=True
    )
)

for activity, color in activity_colors.items():
    group = folium.FeatureGroup(name=activity.title())
    for route in routes:
        if route.activity == activity:
            folium.PolyLine(
                route.path,
                weight=5,
                opacity=0.6,
                color=activity_colors[route.activity],
                tooltip=f"{route.date}",
            ).add_to(group)
    group.add_to(map)

folium.LayerControl(collapsed=False).add_to(map)

map.fit_bounds([[51.48, -2.67], [51.42, -2.56]])

map.show_in_browser()
