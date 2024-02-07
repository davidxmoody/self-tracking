# %% Imports

from glob import glob
import json
from os.path import expandvars
from zipfile import ZipFile

import matplotlib.pyplot as plt
import pandas as pd


# %% Load

filepath = sorted(glob(expandvars("$HOME/Downloads/????-??-??-google-takeout.zip")))[-1]
with ZipFile(filepath) as zf:
    json_data = json.load(zf.open("Takeout/Location History (Timeline)/Records.json"))

df = pd.DataFrame(json_data["locations"])
df = pd.DataFrame(
    {
        "datetime": pd.to_datetime(
            df.timestamp.str.replace(r"(\.\d{3})?Z$", "", regex=True)
        ),
        "lat": df.latitudeE7,
        "lon": df.longitudeE7,
        "acc": df.accuracy,
    }
).drop_duplicates()


# %% Analyse

df.plot.scatter(x="lon", y="lat")
plt.xlim(-6e7, 1e7)
plt.ylim(48e7, 56e7)
plt.show()
