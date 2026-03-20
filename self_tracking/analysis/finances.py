import plotly.graph_objects as go
import self_tracking.data as d

df = d.money()

account_order = ["monzo", "santander", "coop"]
columns = [c for c in account_order if c in df.columns]
# Include any accounts not in the predefined order
columns += [c for c in df.columns if c not in columns]

fig = go.Figure()

for col in columns:
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col],
            name=col.title(),
            stackgroup="one",
            hovertemplate="%{x|%d %b %Y}<br>%{y:,.0f}<extra>%{fullData.name}</extra>",
        )
    )

fig.update_layout(
    width=1100,
    height=650,
    xaxis_title="",
    yaxis_title="Balance (£)",
    yaxis_tickformat=",",
    hovermode="x unified",
    margin={"l": 20, "r": 20, "t": 20, "b": 0},
)
fig
