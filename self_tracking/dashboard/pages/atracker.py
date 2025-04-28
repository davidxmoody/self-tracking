from typing import Any, cast
import dash
from dash import Input, Output, dcc, html
import plotly.express as px
import self_tracking.data as d
import dash_mantine_components as dmc
import pandas as pd

dash.register_page(__name__, title="ATracker")


aggregation_periods = {
    "Yearly": "YS",
    "Quarterly": "QS",
    "Monthly": "MS",
    "Weekly": "W-MON",
    "Daily": "D",
}

aggregation_ops = {
    "Daily average": "mean",
    "Total": "sum",
}


def SelectControl(id: str, options: dict[str, str]):
    return dmc.SegmentedControl(
        id=id,
        value=list(options.values())[0],
        data=cast(Any, [{"value": v, "label": k} for k, v in options.items()]),
        persistence_type="local",
        persistence=True,
    )


layout = html.Div(
    [
        dmc.Stack(
            [
                SelectControl("aggregation-period", aggregation_periods),
                SelectControl("aggregation-op", aggregation_ops),
            ],
            align="flex-start",
        ),
        dcc.Graph(id="bar-chart", figure={}),
    ]
)


last_mtime = 0.0
last_df: pd.DataFrame | None = None


def get_df() -> pd.DataFrame:
    global last_mtime
    global last_df
    mtime = d.atracker_mtime()
    if last_df is not None and mtime == last_mtime:
        return last_df
    df = d.atracker()
    last_df = df
    last_mtime = mtime
    return df


@dash.callback(
    Output("bar-chart", "figure"),
    [Input("aggregation-period", "value"), Input("aggregation-op", "value")],
)
def update_graph(rule: str = "MS", op: str = "mean"):
    long = (
        get_df()["2020-05-04":]
        .drop(["sleep"], axis=1)
        .resample("D")
        .asfreq()
        .fillna(0)
        .resample(rule, closed="left", label="left")
        .agg(op)
        .reset_index()
        .melt(id_vars="date", var_name="category", value_name="value")
    )

    color_map = d.atracker_categories()

    fig = px.bar(
        long,
        x="date",
        y="value",
        color="category",
        color_discrete_map=color_map,
        category_orders={"category": reversed(color_map.keys())},
    )
    fig.update_layout(
        legend={"traceorder": "reversed", "x": 1},
        xaxis_title=None,
        yaxis_title=None,
        legend_title=None,
        margin={"l": 20, "r": 0, "t": 20, "b": 0},
    )

    return fig
