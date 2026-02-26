from datetime import datetime, timedelta

import dash
from dash import Input, Output, dcc, html
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from self_tracking.dashboard.components.controls import Select
import self_tracking.data as d
import dash_mantine_components as dmc

dash.register_page(__name__, title="ATracker Heatmap")


def get_start_dates():
    today = datetime.now().date()
    return {
        "All time": "2020-05-04",
        "Last 4 years": (today - timedelta(days=4 * 365)).strftime("%Y-%m-%d"),
        "Last 2 years": (today - timedelta(days=2 * 365)).strftime("%Y-%m-%d"),
        "Last year": (today - timedelta(days=365)).strftime("%Y-%m-%d"),
        "Last 6 months": (today - timedelta(days=182)).strftime("%Y-%m-%d"),
    }


layout = html.Div(
    [
        dmc.Group(
            [
                Select("heatmap-start-date", get_start_dates()),
            ],
            gap="xl",
            justify="center",
        ),
        dcc.Loading(
            html.Div(id="heatmap-chart", style={"minHeight": 600}),
        ),
    ]
)


@dash.callback(
    Output("heatmap-chart", "children"),
    Input("heatmap-start-date", "value"),
)
def update_graph(start_date: str):
    hm = d.atracker_heatmap(start_date)
    hm.columns = d.atracker_categories().name[hm.columns].values
    color_map = d.atracker_color_map(use_names=True)

    # Drop categories with no data
    hm = hm.loc[:, hm.sum() > 0]

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
                marker=dict(color=color_map.get(col)),
            ),
            row=1,
            col=i + 1,
        )

    for i, col in enumerate(hm.columns):
        fig.update_xaxes(title_text=col, row=1, col=i + 1)

    # Format y-axis as hours
    tick_vals = list(range(0, 24 * 60, 120))
    tick_text = [f"{m // 60:02d}:00" for m in tick_vals]

    fig.update_layout(
        showlegend=False,
        plot_bgcolor="white",
        height=600,
        margin={"l": 40, "r": 0, "t": 20, "b": 0},
        xaxis=dict(showgrid=False),
        yaxis=dict(
            autorange="reversed",
            showgrid=False,
            tickmode="array",
            tickvals=tick_vals,
            ticktext=tick_text,
        ),
        bargap=0,
    )

    return dcc.Graph(figure=fig)
