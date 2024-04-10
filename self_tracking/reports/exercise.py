# %% [markdown]
# ---
# title: "Exercise"
# format:
#   html:
#     toc: true
#     code-fold: true
# jupyter: python3
# highlight-style: github
# ---

# %%
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.linear_model import LinearRegression
import pandas as pd

import self_tracking.data as d

# import plotly.io as pio
# pio.renderers.default = "browser"


# %%
running = d.running()
isnull = running.calories.isnull()

X_train = running.loc[~isnull, ["distance"]]
y_train = running.loc[~isnull].calories

model = LinearRegression()
model.fit(X_train, y_train)

X_predict = running.loc[isnull, ["distance"]]
y_predict = model.predict(X_predict).astype(int)

running.loc[isnull, "calories"] = y_predict

running["type"] = "running"


# %%
cycling_indoor = d.cycling_indoor()
cycling_indoor["type"] = "cycling_indoor"

cycling_outdoor = d.cycling_outdoor()
cycling_outdoor["type"] = "cycling_outdoor"


# %%
sources = [
    df.resample("MS").agg({"calories": "sum", "type": "first"})
    for df in [running, cycling_outdoor, cycling_indoor]
]
exercise = pd.concat(sources).reset_index()[["date", "calories", "type"]]


# %%
fig = px.bar(exercise, x="date", y="calories", color="type")
fig.show()

# %%
r = d.running().distance.resample("MS").sum()
co = d.cycling_outdoor().calories.resample("MS").sum()
ci = d.cycling_indoor().calories.resample("MS").sum()
s = d.strength().drop_duplicates("date").set_index("date").title.resample("MS").size()
c = d.climbing().place.resample("MS").size()

fig = make_subplots(
    rows=4,
    cols=1,
    shared_xaxes=True,
    subplot_titles=["Running", "Cycling", "Strength training", "Climbing"],
)

fig.add_trace(go.Bar(x=r.index, y=r.values, name="Running"), row=1, col=1)
fig.update_yaxes(title_text="Miles", range=[0, 80], row=1, col=1)

fig.add_trace(
    go.Bar(x=co.index, y=co.values, name="Outdoor"),
    row=2,
    col=1,
)
fig.add_trace(
    go.Bar(x=ci.index, y=ci.values, name="Indoor"),
    row=2,
    col=1,
)
fig.update_yaxes(title_text="Calories", range=[0, 6000], row=2, col=1)

fig.add_trace(go.Bar(x=s.index, y=s.values, name="Strength"), row=3, col=1)
fig.update_yaxes(title_text="Sessions", range=[0, 20], row=3, col=1)

fig.add_trace(go.Bar(x=c.index, y=c.values, name="Climbing"), row=4, col=1)
fig.update_yaxes(title_text="Sessions", range=[0, 10], row=4, col=1)

fig.update_layout(barmode="stack", showlegend=False)

fig.show()
