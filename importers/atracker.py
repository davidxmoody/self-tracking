# %% Imports

from os import environ
from os.path import expandvars

from dotenv import load_dotenv
from icalendar import Calendar
import pandas as pd
import requests

load_dotenv()


# %% Fetch

req = requests.get(environ["ATRACKER_URL"])

cal = Calendar.from_ical(req.text)


# %% Clean

df = pd.DataFrame(
    (
        {
            "start": pd.to_datetime(e["DTSTART"].dt),
            "end": pd.to_datetime(e["DTEND"].dt),
            "category": e["SUMMARY"].lower(),
        }
        for e in cal.walk("VEVENT")
    )
).sort_values("start")

df["duration"] = (df["end"] - df["start"]).dt.total_seconds().astype(int)

df.loc[df["category"] == "side project", "category"] = "project"

df = df[["start", "duration", "category"]]


# %% Write

df.to_csv(expandvars("$DIARY_DIR/data/atracker.tsv"), sep="\t", index=False)
