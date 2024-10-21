import dash
from dash import Input, Output, dcc, html
from typing import cast
from pandas import DataFrame
import plotly.express as px
import self_tracking.data as d
import dash_mantine_components as dmc

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
            value=aggregation_ops["Total"],
            label="Aggregation operation:",
            size="sm",
        ),
        dcc.Graph(id="bar-chart", figure={}),
    ]
)


@dash.callback(
    Output("bar-chart", "figure"),
    [Input("aggregation-period", "value"), Input("aggregation-op", "value")],
)
def update_graph(rule: str = "MS", op: str = "sum"):
    atracker = cast(
        DataFrame,
        d.atracker()["2020":].apply(lambda x: x.dt.total_seconds() / (60 * 60)),
    )

    long = (
        atracker.drop(["sleep", "workout"], axis=1)
        .resample(rule, closed="left", label="left")
        .agg(op)
        .reset_index()
        .melt(id_vars="date", var_name="category", value_name="value")
    )

    long["hours"] = long.value.fillna(0).astype(int)
    long["minutes"] = ((long.value.fillna(0) - long.hours) * 60).astype(int)

    color_map = dict(d.atracker_categories().values)

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
        custom_data=["hours", "minutes"],
    )
    fig.update_layout(legend={"traceorder": "reversed"})
    # fig.update_traces(hovertemplate="%{customdata[0]}h %{customdata[1]}m")

    return fig
