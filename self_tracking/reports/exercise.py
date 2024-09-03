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
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import self_tracking.data as d


# %%
rule = "MS"

r = d.running().distance.resample(rule).sum()
co = d.cycling_outdoor().calories.resample(rule).sum()
ci = d.cycling_indoor().calories.resample(rule).sum()
s = d.strength().drop_duplicates("date").set_index("date").title.resample(rule).size()
c = d.climbing().place.resample(rule).size()

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
