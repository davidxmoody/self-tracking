# %% Imports

from glob import glob
import json
from os.path import expandvars
from zipfile import ZipFile

import folium
from folium.plugins import HeatMap
import pandas as pd


# %% Load

filepath = sorted(glob(expandvars("$HOME/Downloads/????-??-??-google-takeout.zip")))[-1]
with ZipFile(filepath) as zf:
    json_data = json.load(zf.open("Takeout/Location History (Timeline)/Records.json"))

df = pd.DataFrame(json_data["locations"])
df = (
    pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                df.timestamp.str.replace(r"(\.\d{3})?Z$", "", regex=True)
            ),
            "lat": df.latitudeE7 / 1e7,
            "lon": df.longitudeE7 / 1e7,
            "accuracy": df.accuracy,
        }
    )
    .drop_duplicates("datetime")
    .set_index("datetime")
    .query("accuracy < 50")
)


# %% Heat map

map = folium.Map(zoom_start=14)
HeatMap(df.values, blur=3, radius=10).add_to(map)
map.show_in_browser()
