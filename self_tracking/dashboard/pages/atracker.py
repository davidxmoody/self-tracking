from typing import Any, cast
import dash
from dash import Input, Output, clientside_callback, dcc, html
import plotly.express as px
import self_tracking.data as d
import dash_mantine_components as dmc
import pandas as pd
from self_tracking.importers.atracker import import_events

dash.register_page(__name__, title="ATracker")


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


def SelectControl(id: str, options: dict[str, str]):
    return dmc.SegmentedControl(
        id=id,
        value=list(options.values())[0],
        data=cast(Any, [{"value": v, "label": k} for k, v in options.items()]),
        persistence_type="local",
        persistence=True,
    )


def Checkbox(id: str, label: str, checked=True):
    return dmc.Checkbox(
        id=id,
        label=label,
        checked=checked,
        persistence_type="local",
        persistence=True,
    )


layout = html.Div(
    [
        dmc.Group(
            [
                SelectControl("atracker-period", periods),
                SelectControl("atracker-agg", aggregations),
                Checkbox("atracker-limit", "Limit bars"),
                Checkbox("atracker-omit-last", "Omit last day"),
                dmc.Button(
                    id="atracker-refresh-button",
                    children="Refresh",
                    variant="outline",
                    loaderProps={"type": "dots"},
                ),
                dcc.Store(id="atracker-refresh-counter", data=0),
            ],
            gap="xl",
            justify="center",
        ),
        html.Div(id="atracker-chart"),
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


clientside_callback(
    """
    function updateLoadingState(n_clicks) {
        return true
    }
    """,
    Output("atracker-refresh-button", "loading", allow_duplicate=True),
    Input("atracker-refresh-button", "n_clicks"),
    prevent_initial_call=True,
)


@dash.callback(
    Output("atracker-refresh-counter", "data"),
    Output("atracker-refresh-button", "loading"),
    Input("atracker-refresh-button", "n_clicks"),
    prevent_initial_call=True,
)
def trigger_refresh(n_clicks):
    import_events()
    return (n_clicks, False)


def format_duration(hours: float):
    h, m = divmod(round(hours * 60), 60)
    return f"{h:02d}:{m:02d}"


@dash.callback(
    Output("atracker-chart", "children"),
    [
        Input("atracker-period", "value"),
        Input("atracker-agg", "value"),
        Input("atracker-limit", "checked"),
        Input("atracker-omit-last", "checked"),
        Input("atracker-refresh-counter", "data"),
    ],
)
def update_graph(rule: str, agg: str, limit: bool, omit_last: bool, n_clicks: int):
    df = get_df().drop(["sleep"], axis=1)

    if omit_last:
        df = df.iloc[:-1]

    df = df.resample(rule, closed="left", label="left").agg(agg).reset_index()

    if limit:
        df = df.iloc[-100:]

    long = df.melt(id_vars="date", var_name="category", value_name="value")
    long = long.loc[long.value > 0]
    long["duration"] = long.value.apply(format_duration)

    color_map = d.atracker_color_map()

    fig = px.bar(
        long,
        x="date",
        y="value",
        color="category",
        color_discrete_map=color_map,
        category_orders={"category": reversed(color_map.keys())},
        custom_data=["category", "duration"],
    )
    fig.update_traces(
        hovertemplate="<b>%{customdata[1]}</b> %{customdata[0]}<extra></extra>"
    )
    fig.update_layout(
        height=500,
        legend={"traceorder": "reversed", "x": 1},
        xaxis_title=None,
        yaxis_title=None,
        legend_title=None,
        margin={"l": 40, "r": 0, "t": 20, "b": 0},
        hovermode="x unified",
    )

    return dcc.Graph(figure=fig)
