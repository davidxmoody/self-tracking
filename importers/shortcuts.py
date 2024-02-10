# %% Imports

from io import StringIO
from os.path import expandvars
import subprocess

import pandas as pd


# %% Run

result = subprocess.run(
    ["shortcuts", "run", "Climbing Export"], check=True, capture_output=True, text=True
)


# %% Format

df = pd.read_table(
    StringIO(result.stdout), header=None, names=["start", "end", "title"]
)
df["start"] = df.start.astype("datetime64[s, Europe/London]")
df["end"] = df.end.astype("datetime64[s, Europe/London]")
df["duration"] = ((df.end - df.start).dt.total_seconds() / 60).astype(int)
df["date"] = df.start.dt.date
df["place"] = df.title.str.replace("Climbing at ", "")
df = df[["date", "duration", "place"]]

if df.date.duplicated().any():
    raise Exception("Unexpected duplicated dates")


# %% Write

df.to_csv(expandvars("$DIARY_DIR/data/climbing.tsv"), sep="\t", index=False)
