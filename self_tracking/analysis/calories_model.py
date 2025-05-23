import pandas as pd
import self_tracking.data as d
import plotly.express as px
import plotly.graph_objects as go
import statsmodels.api as sm
import numpy as np


# %%
activity = d.activity()
diet = d.diet()
weight = d.weight()


# %%
climbing = d.climbing()
climbing.index = pd.to_datetime(climbing.index.tz_convert(None).date).rename("date")
climbing["calories"] = climbing.duration.clip(0, 1.5) * 200


# %%
start_date = diet.index.min()
end_date = diet.index.max()

df = pd.DataFrame(
    {
        "active": activity.active_calories[start_date:end_date]
        + climbing.calories.reindex(pd.date_range(start_date, end_date)).fillna(0),
        "eaten": diet.calories,
        "weight_raw": weight.weight[start_date:end_date],
    }
)

df["weight_rolling"] = (
    df.weight_raw.interpolate("linear")
    .rolling(window=21, center=True, min_periods=1)
    .mean()
)

weight_raw = weight.weight[start_date:end_date]

lowess_result = sm.nonparametric.lowess(
    weight_raw, weight_raw.index.astype(np.int64), frac=0.03
)

df["weight"] = (
    pd.Series(data=lowess_result[:, 1], index=pd.to_datetime(lowess_result[:, 0]))
    .reindex(pd.date_range(start_date, end_date))
    .interpolate(method="time")
)

# df = df["2021-01-01":]


# %%
fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df.weight_raw,
        mode="markers",
        marker=dict(symbol="x-thin", size=8, line=dict(width=1, color="lightgrey")),
        name="Weight",
    )
)

fig.add_trace(
    go.Scatter(x=df.index, y=df.weight_rolling, mode="lines", name="Weight rolling")
)
fig.add_trace(go.Scatter(x=df.index, y=df.weight, mode="lines", name="Weight lowess"))

fig


# %%
df["weight_change"] = -1 * df.weight.diff(-1)
df["balance"] = df.weight_change * 3500
df["basal"] = df.eaten - df.active - df.balance


# %%
px.scatter(df, x="weight", y="basal", trendline="ols")


# %%
X = sm.add_constant(df.iloc[:-1].weight)
y = df.iloc[:-1].basal
model = sm.OLS(y, X).fit()


# %%
demo = pd.DataFrame({"weight": range(150, 171)})
demo["basal"] = model.predict(sm.add_constant(demo.weight)).round(0).astype(int)
demo


# %%
df["basal_pred"] = model.predict(sm.add_constant(df.weight))
df["weight_change_pred"] = (df.eaten - df.active - df.basal_pred) / 3500
df["weight_pred"] = df.iloc[0].weight + df.weight_change_pred.cumsum()

px.line(
    df.reset_index().melt(id_vars="date", value_vars=["weight", "weight_pred"]),
    x="date",
    y="value",
    color="variable",
)


# %%
df["balance_pred"] = df.eaten - df.active - df.basal_pred

px.bar(df.balance_pred.resample("W-MON", label="left", closed="left").sum())
