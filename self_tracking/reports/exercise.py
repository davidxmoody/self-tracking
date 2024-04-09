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
import plotly.io as pio

import self_tracking.data as d

pio.renderers.default = "browser"


# %%
running = d.running()
cycling_indoor = d.cycling_indoor()
cycling_outdoor = d.cycling_outdoor()

running = d.running()
running_not_null = running.dropna()

X_train = running_not_null[["distance"]]
y_train = running_not_null.calories

model = LinearRegression()
model.fit(X_train, y_train)

X_predict = running.loc[running.calories.isnull(), ["distance"]]
y_predict = model.predict(X_predict).astype(int)

max_dist = X_train.sort_values(by="distance").iloc[-1:]
max_dist.iloc[0, 0]

running.loc[running.calories.isnull(), "calories"] = y_predict
running["predicted"] = running.duration.isnull()

fig = px.scatter(running, y="calories", x="distance", color="predicted")
fig.add_shape(
    type="line",
    x0=0,
    y0=model.intercept_,
    x1=max_dist.iloc[0, 0],
    y1=model.predict(max_dist)[0],
)
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

fig.add_trace(
    go.Bar(x=r.index, y=r.values, name="Running", legendgroup="1"), row=1, col=1
)
fig.update_yaxes(title_text="Miles", range=[0, 80], row=1, col=1)

fig.add_trace(
    go.Bar(x=co.index, y=co.values, name="Cycling (outdoor)", legendgroup="2"),
    row=2,
    col=1,
)
fig.add_trace(
    go.Bar(x=ci.index, y=ci.values, name="Cycling (indoor)", legendgroup="2"),
    row=2,
    col=1,
)
fig.update_yaxes(title_text="Calories", range=[0, 6000], row=2, col=1)

fig.add_trace(
    go.Bar(x=s.index, y=s.values, name="Strength", legendgroup="3"), row=3, col=1
)
fig.update_yaxes(title_text="Sessions", range=[0, 20], row=3, col=1)

fig.add_trace(
    go.Bar(x=c.index, y=c.values, name="Climbing", legendgroup="4"), row=4, col=1
)
fig.update_yaxes(title_text="Sessions", range=[0, 10], row=4, col=1)

fig.update_layout(barmode="stack", legend_tracegroupgap=180)

fig.show()
