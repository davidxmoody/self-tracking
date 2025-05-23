from typing import Any, cast
import dash
from dash import Input, Output, dcc, html
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import self_tracking.data as d
import dash_mantine_components as dmc

dash.register_page(__name__)


periods = {
    "Quarterly": "QS",
    "Monthly": "MS",
    "Weekly": "W-MON",
}

layout = html.Div(
    [
        dmc.Group(
            [
                dmc.SegmentedControl(
                    id="exercise-period",
                    value=periods["Monthly"],
                    data=cast(
                        Any, [{"value": v, "label": k} for k, v in periods.items()]
                    ),
                    persistence_type="local",
                    persistence=True,
                ),
            ],
            gap="xl",
            justify="center",
        ),
        html.Div(id="exercise-chart"),
    ]
)


@dash.callback(
    Output("exercise-chart", "children"),
    [Input("exercise-period", "value")],
)
def update_graph(rule: str):
    r = d.running().distance.resample(rule).sum()
    co = d.cycling().calories.resample(rule).sum()
    ci = d.cycling_indoor().calories.resample(rule).sum()
    s = d.strength().duration.resample(rule).size()
    c = d.climbing().duration.clip(0, 3).resample(rule).sum()

    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        subplot_titles=["Running", "Cycling", "Strength training", "Climbing"],
    )

    fig.add_trace(go.Bar(x=r.index, y=r.values, name="Running"), row=1, col=1)
    fig.update_yaxes(title_text="Miles", row=1, col=1)

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
    fig.update_yaxes(title_text="Calories", row=2, col=1, tickformat=",.0s")

    fig.add_trace(go.Bar(x=s.index, y=s.values, name="Strength"), row=3, col=1)
    fig.update_yaxes(title_text="Sessions", row=3, col=1)

    fig.add_trace(go.Bar(x=c.index, y=c.values, name="Climbing"), row=4, col=1)
    fig.update_yaxes(title_text="Hours", row=4, col=1)

    fig.update_layout(
        height=650,
        barmode="stack",
        showlegend=False,
        margin={"l": 20, "r": 20, "t": 60, "b": 0},
    )

    return dcc.Graph(figure=fig)
