import dash
from dash import dcc, html
from typing import cast
from pandas import DataFrame
import plotly.express as px
import self_tracking.data as d

dash.register_page(__name__)


def layout():
    atracker = cast(
        DataFrame,
        d.atracker()["2020":].apply(lambda x: x.dt.total_seconds() / (60 * 60)),
    )

    color_map = dict(d.atracker_categories().values)

    rule = "MS"

    long = (
        atracker.drop(["sleep", "workout"], axis=1)
        .resample("D")
        .sum()
        .resample(rule)
        .mean()
        .reset_index()
        .melt(id_vars="date", var_name="category", value_name="value")
    )

    fig2 = px.bar(
        long,
        x="date",
        y="value",
        color="category",
        color_discrete_map=color_map,
        category_orders={"category": reversed(color_map.keys())},
        labels={"value": "Daily average hours", "date": "Date", "category": "Category"},
    )
    fig2.update_layout(legend={"traceorder": "reversed"})

    # TODO add aggregation controls and filters

    print("atracker loaded")

    return html.Div(
        [
            dcc.Graph(figure=fig2),
        ]
    )
