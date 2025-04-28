import dash
from dash import Input, Output, dcc, html
import plotly.express as px
import self_tracking.data as d
import dash_mantine_components as dmc
import pandas as pd

dash.register_page(__name__)


aggregation_periods = {
    "Daily": "D",
    "Weekly": "W-MON",
    "Monthly": "MS",
    "Quarterly": "QS",
    "Yearly": "YS",
}

aggregation_ops = {
    "Daily average": "mean",
    "Total": "sum",
}


layout = html.Div(
    [
        dmc.RadioGroup(
            id="aggregation-period",
            children=[dmc.Radio(k, value=v) for k, v in aggregation_periods.items()],
            value=aggregation_periods["Monthly"],
            label="Aggregation period:",
            size="sm",
        ),
        dmc.RadioGroup(
            id="aggregation-op",
            children=[dmc.Radio(k, value=v) for k, v in aggregation_ops.items()],
            value=aggregation_ops["Daily average"],
            label="Aggregation operation:",
            size="sm",
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
        labels={
            "value": f"{[k for k, v in aggregation_ops.items() if v == op][0]} (hours)",
            "date": "Date",
            "category": "Category",
        },
    )
    fig.update_layout(legend={"traceorder": "reversed"})

    return fig
