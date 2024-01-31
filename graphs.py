# %% Imports

from datetime import timedelta
from os import environ, path

import calmap
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import pandas as pd

load_dotenv()


# %% Load data


def read_data(name: str):
    filename = path.join(environ["DIARY_DIR"], "data", f"{name}.tsv")
    df = pd.read_table(filename, parse_dates=["date"], index_col="date")
    return df


activity_data = read_data("activity")
diet_data = read_data("diet")
weight_data = read_data("weight")
strength_data = read_data("strength")
running_data = read_data("running")


# %% Calorie deficit graph

calmap.calendarplot(
    (
        diet_data["calories"]
        - activity_data["active_calories"]
        - activity_data["basal_calories"]
    )
    .dropna()
    .iloc[:-1],
    daylabels="MTWTFSS",
    dayticks=[0, 2, 4, 6],
    cmap="seismic",
    vmin=-1500,
    vmax=1500,
)
plt.show(block=False)


# %% Running graph

fig, ax = calmap.calendarplot(
    running_data["distance"]["2024":],
    dayticks=[],
    vmin=-2,
    vmax=10,
)
man = plt.get_current_fig_manager()
if man:
    man.set_window_title("Running")
plt.show(block=False)


# %% Load ATracker data

ad = pd.read_table(path.join(environ["DIARY_DIR"], "data/atracker.tsv"))
ad["start"] = ad["start"].astype("datetime64[s, Europe/London]")
# ad["duration"] = ad["duration"].astype("Int64")

hours_offset = 4
ad["date"] = pd.to_datetime((ad["start"] - timedelta(hours=hours_offset)).dt.date)

pivot_categories = environ["ATRACKER_CATEGORIES"].split(",")
ap = ad.loc[ad["category"].isin(pivot_categories)].pivot_table(
    values="duration", index="date", columns="category", aggfunc="sum"
)

ap = ap.fillna(ap.mask(ap.ffill().notna(), 0))


# %% ATracker graph

cat = "project"

calmap.calendarplot(
    ap[cat],
    daylabels="MTWTFSS",
    dayticks=[0, 2, 4, 6],
    vmin=0,
)
if man := plt.get_current_fig_manager():
    man.set_window_title(cat)
plt.show(block=False)
