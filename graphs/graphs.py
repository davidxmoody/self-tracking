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


def read_data(name: str, index_col: str | None = "date"):
    return pd.read_table(
        expandvars(f"$DIARY_DIR/data/{name}.tsv"),
        parse_dates=["date"],
        index_col=index_col,
    )


activity = read_data("activity")
diet = read_data("diet")
weight = read_data("weight")
strength = read_data("strength", index_col=None)
running = read_data("running")
cycling_indoor = read_data("cycling-indoor")
cycling_outdoor = read_data("cycling-outdoor")
climbing = read_data("climbing")


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


# %% Combined graph

cats = ["project", "workout", "youtube"]

fig, ax = plt.subplots(nrows=len(cats), ncols=1, sharey=True)

for i, cat in enumerate(cats):
    monthly = atracker[cat].resample("MS").sum() / (60 * 60)
    monthly.plot(kind="bar", ax=ax[i])
    ax[i].set_xticklabels([x.strftime("%Y-%m") for x in monthly.index])
    ax[i].set_xlabel("")
    ax[i].set_title(cat)

plt.subplots_adjust(hspace=1)
set_window_title("ATracker combined graph")
plt.show()


# %% Exercise type comparison

rule = "MS"
label_format = "%Y-%m"

exercises = {
    "running": running.distance.resample(rule).sum(),
    "cycling_indoor": cycling_indoor.calories.resample(rule).sum(),
    "cycling_outdoor": cycling_outdoor.calories.resample(rule).sum(),
    "strength": strength.drop_duplicates("date")
    .set_index("date")
    .program.resample(rule)
    .size(),
    "climbing": climbing.place.resample(rule).size(),
}

mindate = min(e.index.min() for e in exercises.values())
maxdate = max(e.index.max() for e in exercises.values())
drange = pd.date_range(mindate, maxdate, freq=rule)

exercises = {k: v.reindex(drange) for k, v in exercises.items()}

fig, ax = plt.subplots(nrows=len(exercises), ncols=1, sharex=True)

# TODO try plotting indoor/outdoor on same graph as stacked bar chart

for i, (name, exercise) in enumerate(exercises.items()):
    exercise.plot(kind="bar", ax=ax[i])
    ax[i].set_xticklabels(
        [(x.strftime(label_format) if x.month % 3 == 0 else "") for x in exercise.index]
    )
    ax[i].set_xlabel("")
    ax[i].set_title(name)

plt.subplots_adjust(hspace=0.5)
plt.show()


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
