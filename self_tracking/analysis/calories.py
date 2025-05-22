# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
import pandas as pd
import self_tracking.data as d
import plotly.express as px


# %%
activity = d.activity()
diet = d.diet()
weight = d.weight()


# %%
climbing = d.climbing()
climbing.index = pd.to_datetime(climbing.index.tz_convert(None).date).rename("date")
climbing["calories"] = climbing.duration.clip(0, 2) * 200


# %%
start_date = diet.index.min()
# start_date = "2024-07-01"
end_date = diet.index.max()

df = pd.DataFrame(
    {
        "active": activity.active_calories[start_date:end_date]
        + climbing.calories.reindex(pd.date_range(start_date, end_date)).fillna(0),
        "eaten": diet.calories,
        "weight": weight.weight[start_date:end_date],
    }
)

df["weight"] = df.weight.interpolate("linear")
df["weight_smoothed"] = df.weight.rolling(
    window=14, center=True, min_periods=1
).median()

df["weight_change"] = df.weight_smoothed.diff().shift(-1)

df = df.dropna()

df["calorie_imbalance"] = df.weight_change * 3500

df["basal_estimate"] = df.eaten - df.active - df.calorie_imbalance

df["basal_smoothed"] = df.basal_estimate.rolling(
    window=21, center=True, min_periods=1
).mean()


# %%
fig = px.scatter(df, x="weight", y="basal_smoothed", trendline="ols")
fig.update_yaxes(range=[1200, 2600])
fig


# %%
model = px.get_trendline_results(fig).iloc[0, 0]

df["basal_pred"] = df.weight_smoothed.apply(
    lambda x: int(round(model.params[0] + x * model.params[1]))
)

df["balance"] = df.eaten - df.active - df.basal_pred
df["weight_pred"] = df.weight.iloc[0] + (df.balance.cumsum() / 3500)


# %%
fig = px.line(
    df.reset_index().melt(
        id_vars="date", value_vars=["weight_pred", "weight_smoothed"]
    ),
    x="date",
    y="value",
    color="variable",
)
fig.update_layout(yaxis=dict(title="Weight (lb)"))
fig


# %%
df["basal_pred2"] = (
    df.eaten.cumsum() - df.active.cumsum() - df.weight_smoothed * 3500
).diff()

# weight = cum(eaten) - cum(active) - cum(basal)
# basal = diff(cum(eaten) - cum(active) - weight)


# %%
px.line((df.eaten - df.active).cumsum())
