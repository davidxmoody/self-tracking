import dash
from dash import Input, Output, dcc, html
import plotly.graph_objects as go
from self_tracking.dashboard.components.controls import Select
import self_tracking.data as d
import dash_mantine_components as dmc
import pandas as pd
from plotly.subplots import make_subplots

dash.register_page(__name__)


periods = {
    "Yearly": "YS",
    "Quarterly": "QS",
    "Monthly": "MS",
    "Weekly": "W-MON",
    "Daily": "D",
}

period_offsets = {
    "YS": pd.Timedelta(days=365 / 2),
    "QS": pd.Timedelta(days=365 / 8),
    "MS": pd.Timedelta(days=15),
    "W-MON": pd.Timedelta(days=3.5),
    "D": pd.Timedelta(hours=12),
}

aggregations = {
    "Daily average": "mean",
    "Total": "sum",
}


layout = html.Div(
    [
        dmc.Group(
            [
                Select("calories-period", periods),
                Select("calories-agg", aggregations),
            ],
            gap="xl",
            justify="center",
        ),
        html.Div(id="calories-chart"),
    ]
)


@dash.callback(
    Output("calories-chart", "children"),
    [
        Input("calories-period", "value"),
        Input("calories-agg", "value"),
    ],
)
def update_graph(rule: str, agg: str):
    eaten = d.diet().calories
    start = eaten.index.min()
    end = eaten.index.max()

    active = d.activity().active_calories[start:end]

    weight = d.weight().weight.reindex(pd.date_range(start, end, freq="D"))
    weight = weight.interpolate().rolling(window=14, center=True, min_periods=1).mean()

    basal = weight * 12.93 - 100 # From previous analysis, TODO re-calculate here

    df = pd.DataFrame(
        {
            "active": active,
            "eaten": eaten,
            "basal": basal,
        }
    )

    df = df.resample(rule, closed="left", label="left").agg(agg)
    df.index = df.index + period_offsets[rule]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05
    )

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df.eaten,
            name="Eaten",
            offsetgroup=0,
            marker_color="green",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df.basal,
            name="Basal",
            offsetgroup=1,
            marker_color="orange",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df.active,
            name="Active",
            offsetgroup=1,
            marker_color="red",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=weight.index,
            y=weight,
            name="Weight",
            mode="lines",
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        height=650,
        xaxis_title=None,
        yaxis_title=None,
        legend_title=None,
        margin={"l": 40, "r": 0, "t": 20, "b": 0},
        barmode="relative",
        bargap=0.4,
    )

    return dcc.Graph(figure=fig)
