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
import plotly.graph_objects as go


# %%
activity = d.activity()
diet = d.diet()
weight = d.weight()


# %%
start_date = diet.index.min()
end_date = diet.index.max()

df = pd.DataFrame(
    {
        "active": activity.active_calories[start_date:end_date],
        "basal_apple": activity.basal_calories[start_date:end_date],
        "eaten": diet.calories,
        "weight": weight.weight[start_date:end_date],
    }
)

df["weight"] = df.weight.interpolate("linear")
df["weight_smoothed"] = df.weight.rolling(
    window=14, center=True, min_periods=1
).median()

df["weight_change"] = df.weight_smoothed.diff().shift(-1).fillna(0)

df["calorie_imbalance"] = df.weight_change * 3500

df["basal_estimate"] = df.eaten - df.active - df.calorie_imbalance

df["basal_smoothed"] = df.basal_estimate.rolling(
    window=21, center=True, min_periods=1
).mean()


# %%
long = df.melt(id_vars="weight", value_vars=["basal_apple", "basal_smoothed"])
fig = px.scatter(long, x="weight", y="value", color="variable", trendline="ols")
fig.update_yaxes(range=[1200, 2600])
fig


# %%
results = px.get_trendline_results(fig)
models = results.set_index("variable").px_fit_results.to_dict()


def predict(model, value):
    return int(round(model.params[0] + value * model.params[1]))


df["basal_pred"] = df.weight_smoothed.apply(
    lambda w: predict(models["basal_smoothed"], w)
)

df["balance"] = df.eaten - df.active - df.basal_pred


# %%
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df.balance.cumsum(),
        name="Energy balance",
        yaxis="y",
        mode="lines",
    )
)
fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df.weight_smoothed,
        name="Weight",
        yaxis="y2",
        mode="lines",
    )
)
fig.update_layout(
    yaxis=dict(title="Calories"),
    yaxis2=dict(title="Weight (lbs)", overlaying="y", side="right"),
)
fig
