from typing import Any, cast
import dash
from dash import Input, Output, dcc, html
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import self_tracking.data as d
import dash_mantine_components as dmc
import pandas as pd

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
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        subplot_titles=["Running", "Cycling", "Strength training", "Climbing"],
    )

    running = d.running().duration.resample(rule, label="left", closed="left").sum()
    fig.add_trace(
        go.Bar(x=running.index, y=running.values, name="Running"), row=1, col=1
    )
    fig.update_yaxes(title_text="Hours", row=1, col=1)

    cycling = d.cycling().duration.resample(rule, label="left", closed="left").sum()
    fig.add_trace(
        go.Bar(x=cycling.index, y=cycling.values, name="Outdoor"),
        row=2,
        col=1,
    )
    cycling_indoor = (
        d.cycling_indoor().duration.resample(rule, label="left", closed="left").sum()
    )
    fig.add_trace(
        go.Bar(x=cycling_indoor.index, y=cycling_indoor.values, name="Indoor"),
        row=2,
        col=1,
    )
    fig.update_yaxes(title_text="Hours", row=2, col=1, tickformat=",.0s")

    strength = d.strength().reset_index()
    strength = (
        strength.groupby(
            [pd.Grouper(key="start", freq=rule, label="left", closed="left"), "program"]
        )
        .duration.size()
        .reset_index()
    )
    for program, group in strength.groupby("program", sort=False):
        fig.add_trace(
            go.Bar(x=group.start, y=group.duration, name=program), row=3, col=1
        )
    fig.update_yaxes(title_text="Sessions", row=3, col=1)

    climbing = d.climbing().reset_index()
    climbing["duration"] = climbing.duration.clip(0, 3)
    climbing = (
        climbing.groupby(
            [pd.Grouper(key="start", freq=rule, label="left", closed="left"), "place"]
        )
        .duration.sum()
        .reset_index()
    )
    for place, group in climbing.groupby("place", sort=False):
        fig.add_trace(go.Bar(x=group.start, y=group.duration, name=place), row=4, col=1)
    fig.update_yaxes(title_text="Hours", row=4, col=1)

    fig.update_layout(
        height=650,
        barmode="stack",
        showlegend=False,
        margin={"l": 20, "r": 20, "t": 60, "b": 0},
    )

    return dcc.Graph(figure=fig)
