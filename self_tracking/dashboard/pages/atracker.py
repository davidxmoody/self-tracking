import dash
from dash import Input, Output, dcc, html
from typing import cast
from pandas import DataFrame
import plotly.express as px
import self_tracking.data as d
import dash_mantine_components as dmc

dash.register_page(__name__)


aggregation_rules = {
    "Daily": "D",
    "Weekly": "W-MON",
    "Monthly": "MS",
    "Quarterly": "QS",
    "Yearly": "YS",
}


layout = html.Div(
    [
        dmc.RadioGroup(
            id="aggregation-selector",
            children=[dmc.Radio(k, value=v) for k, v in aggregation_rules.items()],
            value=aggregation_rules["Monthly"],
            label="Aggregation period:",
            size="sm",
        ),
        dcc.Graph(id="bar-chart", figure={}),
    ]
)


@dash.callback(
    Output("bar-chart", "figure"),
    Input("aggregation-selector", "value"),
)
def update_graph(rule: str = "MS"):
    atracker = cast(
        DataFrame,
        d.atracker()["2020":].apply(lambda x: x.dt.total_seconds() / (60 * 60)),
    )

    long = (
        atracker.drop(["sleep", "workout"], axis=1)
        .resample("D")
        .sum()
        .resample(rule, closed="left", label="left")
        .mean()
        .reset_index()
        .melt(id_vars="date", var_name="category", value_name="value")
    )

    long["hours"] = long.value.astype(int)
    long["minutes"] = ((long.value - long.hours) * 60).astype(int)

    color_map = dict(d.atracker_categories().values)

    fig = px.bar(
        long,
        x="date",
        y="value",
        color="category",
        color_discrete_map=color_map,
        category_orders={"category": reversed(color_map.keys())},
        labels={"value": "Daily average hours", "date": "Date", "category": "Category"},
        custom_data=["hours", "minutes"],
    )
    fig.update_layout(legend={"traceorder": "reversed"})
    # fig.update_traces(hovertemplate="%{customdata[0]}h %{customdata[1]}m")

    return fig
