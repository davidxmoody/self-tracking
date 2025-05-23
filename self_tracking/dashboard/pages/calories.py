import dash
from dash import Input, Output, dcc, html
import plotly.graph_objects as go
from self_tracking.dashboard.components.controls import Select
import self_tracking.data as d
import dash_mantine_components as dmc
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
import statsmodels.api as sm

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

    weight_raw = d.weight().weight[start:end]

    lowess_result = sm.nonparametric.lowess(
        weight_raw, weight_raw.index.astype(np.int64), frac=0.03
    )
    weight = (
        pd.Series(data=lowess_result[:, 1], index=pd.to_datetime(lowess_result[:, 0]))
        .reindex(pd.date_range(start, end))
        .interpolate(method="time")
    )

    basal = weight * 12.5  # Approximation from previous analysis

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
        rows=2, cols=1, shared_xaxes=True, row_heights=[0.6, 0.4], vertical_spacing=0.05
    )

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df.eaten - df.active - df.basal,
            name="Energy balance",
            marker_color="red",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=weight_raw.index,
            y=weight_raw,
            name="Weight",
            mode="markers",
            marker=dict(symbol="x-thin", size=8, line=dict(width=1, color="lightgrey")),
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=weight.index,
            y=weight,
            name="Weight smoothed",
            mode="lines",
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        height=650,
        yaxis_title="Energy balance (Cal)",
        yaxis2=dict(title="Weight (lb)", range=[145, 175]),
        xaxis=dict(
            rangeselector=dict(
                buttons=[
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(count=3, label="3y", step="year", stepmode="backward"),
                    dict(step="all", label="All"),
                ]
            ),
        ),
        xaxis2=dict(
            rangeslider=dict(visible=True),
        ),
        showlegend=False,
        margin={"l": 80, "r": 80, "t": 20, "b": 0},
    )

    return dcc.Graph(figure=fig)
