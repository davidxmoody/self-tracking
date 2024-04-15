from plotly_calplot import calplot

import self_tracking.data as d


# %%
atracker = d.atracker()["2020":] / (60 * 60)


# %%
data = atracker.youtube.rename("category").dt.total_seconds().reset_index()


# %%

fig = calplot(
    data,
    x="date",
    y="category",
    years_title=True,
    colorscale="reds",
    cmap_min=0,
)
fig.show()
