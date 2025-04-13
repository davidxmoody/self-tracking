import self_tracking.data as d
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# %%
hm = d.atracker_heatmap("2021-11-01")
hm = hm.drop(columns=["work", "audiobook"])

# %%
color_map = d.atracker_categories()

# %%
fig = make_subplots(
    rows=1, cols=len(hm.columns), shared_yaxes=True, horizontal_spacing=0.01
)

for i, col in enumerate(hm.columns):
    fig.add_trace(
        go.Bar(
            y=hm.index,
            x=hm[col],
            name=col,
            orientation="h",
            marker=dict(color=color_map[col]),
        ),
        row=1,
        col=i + 1,
    )

for i, col in enumerate(hm.columns):
    fig.update_xaxes(title_text=col, row=1, col=i + 1)

fig.update_layout(
    showlegend=False,
    plot_bgcolor="white",
    xaxis=dict(showgrid=False),
    yaxis=dict(autorange="reversed", showgrid=False),
    bargap=0,
)

fig.show()
