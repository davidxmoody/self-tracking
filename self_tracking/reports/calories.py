import self_tracking.data as d
from plotly_calplot import calplot


# %%
net_calories = d.net_calories().rename("net_calories").reset_index()

fig = calplot(
    net_calories,
    x="date",
    y="net_calories",
    colorscale="RdBu",
    cmap_min=-1200,
    cmap_max=1200,
)
fig.show()
