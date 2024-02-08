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

df = pd.DataFrame(json_data["locations"]).query("accuracy < 60")
df = (
    pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                df.timestamp.str.replace(r"(\.\d{3})?Z$", "", regex=True)
            ),
            "lat": df.latitudeE7 / 1e7,
            "lon": df.longitudeE7 / 1e7,
        }
    )
    .drop_duplicates("datetime")
    .set_index("datetime")
)


# %% Heat map

start_location = list(df.loc["2020":].median())
map = folium.Map(location=start_location, zoom_start=12)
HeatMap(df, blur=12, radius=15).add_to(map)
map.show_in_browser()
