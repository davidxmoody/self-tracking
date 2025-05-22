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
climbing["calories"] = climbing.duration.clip(0, 2) * 250


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

# df = df["2023-01-01":]


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
# df["basal_pred"] = df.basal.mean() - 120
df["weight_change_pred"] = (df.eaten - df.active - df.basal_pred) / 3500
df["weight_pred"] = df.iloc[0].weight + df.weight_change_pred.cumsum()

px.line(
    df.reset_index().melt(id_vars="date", value_vars=["weight", "weight_pred"]),
    x="date",
    y="value",
    color="variable",
)


# %%
df["pred_err"] = (df.weight_change - df.weight_change_pred) * 3500

lowess_result = sm.nonparametric.lowess(
    df.pred_err, df.pred_err.index.astype(np.int64), frac=0.1
)

df["err"] = pd.Series(lowess_result[:, 1], index=pd.to_datetime(lowess_result[:, 0]))

px.line(df.err)


# %%
df["basal_corrected"] = df.basal_pred - df.err
df["weight_change_corrected"] = (df.eaten - df.active - df.basal_corrected) / 3500
df["weight_corrected"] = df.iloc[0].weight + df.weight_change_corrected.cumsum()

px.line(
    df.reset_index().melt(id_vars="date", value_vars=["weight", "weight_corrected"]),
    x="date",
    y="value",
    color="variable",
)


# %%
df["net"] = df.eaten - df.active
df["net_rolling7"] = df.net.rolling(7).mean()
df["net_rolling14"] = df.net.rolling(14).mean()
df["net_rolling21"] = df.net.rolling(21).mean()
df["net_rolling28"] = df.net.rolling(28).mean()


# %%
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.tree import DecisionTreeRegressor

feature_names = [
    "net",
    "net_rolling7",
    "net_rolling14",
    "net_rolling21",
    "net_rolling28",
    "weight",
]

df_notna = df.dropna().copy()

X_train = df_notna[feature_names]
y_train = df_notna.weight_change

# model = Ridge(alpha=1.0)
# model = RandomForestRegressor()
model = DecisionTreeRegressor(max_leaf_nodes=100)

model.fit(X_train, y_train)

df_notna["weight_change_pred"] = model.predict(df_notna[feature_names])
df_notna["weight_pred"] = df_notna.weight.iloc[0] + df_notna.weight_change_pred.cumsum()

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=df_notna.index,
        y=df_notna.weight_raw,
        mode="markers",
        marker=dict(symbol="x-thin", size=8, line=dict(width=1, color="lightgrey")),
        name="Weight",
    )
)

fig.add_trace(
    go.Scatter(x=df_notna.index, y=df_notna.weight, mode="lines", name="Weight lowess")
)
fig.add_trace(
    go.Scatter(
        x=df_notna.index, y=df_notna.weight_pred, mode="lines", name="Weight pred"
    )
)

fig
