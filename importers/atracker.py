# %% Imports

import pandas as pd
import matplotlib.pyplot as plt
import requests
from icalendar import Calendar
import calmap
from os import environ
from dotenv import load_dotenv

load_dotenv()


# %% Fetch data

req = requests.get(environ["ATRACKER_URL"])

cal = Calendar.from_ical(req.text)

df = pd.DataFrame(
    (
        {
            "start": pd.to_datetime(e["DTSTART"].dt),
            "end": pd.to_datetime(e["DTEND"].dt),
            "category": e["SUMMARY"].lower(),
        }
        for e in cal.walk("VEVENT")
    )
)


# %% Clean data

df.loc[df["category"] == "side project", "category"] = "project"

df = df.sort_values("start")
df["duration"] = df["end"] - df["start"]
df["date"] = pd.to_datetime(df["end"].dt.date)


# %% Analyse data

daily = (
    df.groupby(["date", "category"])["duration"]
    .sum()
    .reset_index()
    .sort_values(["date", "duration"], ascending=[True, False])
    .reset_index(drop=True)
)

cat = "project"

calmap.calendarplot(
    daily.loc[daily["category"] == cat]
    .set_index("date")["duration"]
    .dt.total_seconds(),
    daylabels="MTWTFSS",
    dayticks=[0, 2, 4, 6],
    vmin=0,
)
man = plt.get_current_fig_manager()
if man:
    man.set_window_title(cat)
plt.show(block=False)
