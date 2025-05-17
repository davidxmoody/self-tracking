import dash
from dash import Input, Output, dcc, html
import plotly.graph_objects as go
from self_tracking.dashboard.components.controls import Select
import self_tracking.data as d
import dash_mantine_components as dmc
import pandas as pd

dash.register_page(__name__)


periods = {
    "Yearly": "YS",
    "Quarterly": "QS",
    "Monthly": "MS",
    "Weekly": "W-MON",
    "Daily": "D",
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
    weight = (
        weight.interpolate().rolling(window=14, center=True, min_periods=1).median()
    )

    # weight_change = weight.diff().shift(-1)
    # calorie_imbalance = weight_change * 3500
    # basal = eaten - active - calorie_imbalance
    # basal = basal.ffill().rolling(window=14, center=True, min_periods=1).mean()

    basal = weight * 12.93 - 100

    df = pd.DataFrame(
        {
            "active": active,
            "eaten": eaten,
            "basal": basal,
        }
    )

    df = df.resample(rule, closed="left", label="left").agg(agg)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df.eaten,
            name="Eaten",
            offsetgroup=0,
            marker_color="green",
        )
    )

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df.basal,
            name="Basal",
            offsetgroup=1,
            marker_color="orange",
        )
    )

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df.active,
            name="Active",
            offsetgroup=1,
            marker_color="red",
        )
    )

    fig.update_layout(
        height=500,
        xaxis_title=None,
        yaxis_title=None,
        legend_title=None,
        margin={"l": 40, "r": 0, "t": 20, "b": 0},
        barmode="relative",
        bargap=0.4,
    )

    return dcc.Graph(figure=fig)
