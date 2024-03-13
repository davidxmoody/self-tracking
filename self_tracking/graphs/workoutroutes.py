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


# %% Graphs

activity_colors = {
    "running": "red",
    "cycling": "blue",
    "walking": "green",
}

map = folium.Map(tiles="CartoDB Positron")

for route in routes:
    if route.activity == "running":
        folium.PolyLine(
            route.path,
            weight=5,
            opacity=0.6,
            color=activity_colors[route.activity],
            tooltip=f"{route.date} {route.time} {route.activity}",
        ).add_to(map)

map.fit_bounds([[51.48, -2.67], [51.42, -2.56]])

map.show_in_browser()
