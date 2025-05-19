import self_tracking.data as d
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# %%
eaten = d.diet().calories
start = eaten.index.min()
end = eaten.index.max()

active = d.activity().active_calories[start:end]

weight = d.weight().weight.reindex(pd.date_range(start, end, freq="D"))
weight = weight.interpolate().rolling(window=14, center=True, min_periods=1).mean()

basal = weight * 12.93 - 100  # From previous analysis, TODO re-calculate here

df = pd.DataFrame(
    {
        "active": active,
        "eaten": eaten,
        "basal": basal,
    }
)

df["net"] = df.eaten - df.basal - df.active


# %%
df["week"] = df.index.to_period("W").start_time
df["dow"] = df.index.weekday  # 0=Monday, 6=Sunday

heatmap_df = df.pivot(index="dow", columns="week", values="net").sort_index()

weekly_mean = df.groupby("week")["net"].mean()
weekly_pos = weekly_mean.copy()
weekly_pos[weekly_pos < 0] = 0
weekly_neg = weekly_mean.copy()
weekly_neg[weekly_neg > 0] = 0

cmax = weekly_mean.abs().max()

fig = make_subplots(
    rows=3,
    cols=1,
    shared_xaxes=True,
    row_heights=[0.4, 0.2, 0.4],
    vertical_spacing=0.02,
)

fig.add_trace(
    go.Bar(
        x=weekly_pos.index,
        y=weekly_pos.values,
        marker=dict(
            color=weekly_pos.values,
            colorscale="RdBu",
            cmin=-cmax,
            cmax=cmax,
        ),
        showlegend=False,
    ),
    row=1,
    col=1,
)
fig.update_yaxes(range=[0, 900], row=3, col=1)

fig.add_trace(
    go.Heatmap(
        z=heatmap_df.values,
        x=heatmap_df.columns,
        y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        colorscale="RdBu",
        zmid=0,
        zmin=-cmax,
        zmax=cmax,
    ),
    row=2,
    col=1,
)
fig.update_yaxes(autorange="reversed", row=2, col=1)

fig.add_trace(
    go.Bar(
        x=weekly_neg.index,
        y=weekly_neg.values,
        marker=dict(
            color=weekly_neg.values,
            colorscale="RdBu",
            cmin=-cmax,
            cmax=cmax,
        ),
        showlegend=False,
    ),
    row=3,
    col=1,
)
fig.update_yaxes(range=[-900, 0], row=3, col=1)

fig.update_traces(showscale=False, selector=dict(type="heatmap"))

fig.update_layout(
    height=700,
    margin=dict(t=40, b=40),
    title="Calorie deficit/surplus",
)

fig.show()
