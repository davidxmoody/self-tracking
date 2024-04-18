import calmap
import matplotlib.pyplot as plt
import pandas as pd

import self_tracking.data as d


# %%
def set_window_title(title: str):
    if man := plt.get_current_fig_manager():
        man.set_window_title(title)


# %%
atracker = d.atracker()

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


# %%
rule = "MS"
label_format = "%Y-%m"

exercises = {
    "running": d.running().distance.resample(rule).sum(),
    "cycling_indoor": d.cycling_indoor().calories.resample(rule).sum(),
    "cycling_outdoor": d.cycling_outdoor().calories.resample(rule).sum(),
    "strength": d.strength()
    .drop_duplicates("date")
    .set_index("date")
    .title.resample(rule)
    .size(),
    "climbing": d.climbing().place.resample(rule).size(),
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


# %%
calmap.calendarplot(
    d.net_calories(),
    daylabels="MTWTFSS",
    dayticks=[0, 2, 4, 6],
    cmap="seismic",
    vmin=-1000,
    vmax=1000,
)
set_window_title("Calorie deficit/surplus")
plt.show()


# %%
calmap.calendarplot(
    d.running().distance["2024":],
    dayticks=[],
    vmin=-2,
    vmax=10,
)
set_window_title("Running")
plt.show()


# %%
cat = "project"

calmap.calendarplot(
    d.atracker()[cat].dt.total_seconds(),
    daylabels="MTWTFSS",
    dayticks=[0, 2, 4, 6],
    vmin=0,
)
set_window_title(cat)
plt.show()


# %%
net_calories = d.net_calories()

drange = pd.date_range("2022-01-01", net_calories.index.max())

weight_loss = (
    d.weight()
    .weight.reindex(drange)
    .interpolate()
    .pct_change()
    .rolling(window=14, center=True)
    .mean()
    .dropna()
)

deficit_in_drange = net_calories.reindex(weight_loss.index)

print(weight_loss.corr(deficit_in_drange))
plt.scatter(x=deficit_in_drange, y=weight_loss)
plt.show()
