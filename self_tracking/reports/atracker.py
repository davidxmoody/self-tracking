from plotly_calplot import calplot
import plotly.express as px

import self_tracking.data as d


# %%
atracker = d.atracker()["2020":]
color_map = dict(d.atracker_categories().values)


# %%
data = (atracker.reading.rename("category").dt.total_seconds() / 60 / 60).reset_index()

fig = calplot(
    data,
    x="date",
    y="category",
    years_title=True,
    colorscale="blues",
    cmap_min=0,
)

fig.show()


# %%
long = (
    atracker.drop(["sleep", "workout"], axis=1)
    .resample("QS")
    .sum()
    .apply(lambda x: x.dt.total_seconds() / (60 * 60))
    .reset_index()
    .melt(id_vars="date", var_name="category", value_name="value")
)

fig = px.bar(
    long,
    x="date",
    y="value",
    color="category",
    color_discrete_map=color_map,
    category_orders={"category": reversed(color_map.keys())},
)
fig.update_layout(legend={"traceorder": "reversed"})
fig.show()
