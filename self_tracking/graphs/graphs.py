import calmap
import matplotlib.pyplot as plt
import pandas as pd

import self_tracking.data as d


# %%
def set_window_title(title: str):
    if man := plt.get_current_fig_manager():
        man.set_window_title(title)


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
