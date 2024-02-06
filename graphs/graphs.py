# %% Imports

from datetime import timedelta
from os.path import expandvars

import calmap
import matplotlib.pyplot as plt
import pandas as pd


# %% Helpers


def set_window_title(title: str):
    if man := plt.get_current_fig_manager():
        man.set_window_title(title)


# %% Load


def read_data(name: str):
    return pd.read_table(
        expandvars(f"$DIARY_DIR/data/{name}.tsv"),
        parse_dates=["date"],
        index_col="date",
    )


activity = read_data("activity")
diet = read_data("diet")
weight = read_data("weight")
strength = read_data("strength")
running = read_data("running")


atracker_events = pd.read_table(expandvars("$DIARY_DIR/data/atracker.tsv"))
atracker_events["start"] = atracker_events.start.astype("datetime64[s, Europe/London]")
atracker_events["date"] = pd.to_datetime(
    (atracker_events.start - timedelta(hours=4)).dt.date
)
atracker_events = atracker_events.query("date >= '2020'")

atracker = atracker_events.pivot_table(
    values="duration", index="date", columns="category", aggfunc="sum"
)
atracker = atracker.fillna(atracker.mask(atracker.ffill().notna(), 0))


# %% Calorie deficit graph

deficit = (diet.calories - activity.active_calories - activity.basal_calories).dropna()
calmap.calendarplot(
    deficit,
    daylabels="MTWTFSS",
    dayticks=[0, 2, 4, 6],
    cmap="seismic",
    vmin=-1000,
    vmax=1000,
)
set_window_title("Calorie deficit/surplus")
plt.show()


# %% Running graph

fig, ax = calmap.calendarplot(
    running["distance"]["2024":],
    dayticks=[],
    vmin=-2,
    vmax=10,
)
set_window_title("Running")
plt.show()


# %% ATracker graph

cat = "project"

calmap.calendarplot(
    atracker[cat],
    daylabels="MTWTFSS",
    dayticks=[0, 2, 4, 6],
    vmin=0,
)
set_window_title(cat)
plt.show()
