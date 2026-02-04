from datetime import datetime, timedelta

import dash
from dash import Input, Output, clientside_callback, dcc, html
import plotly.express as px
import plotly.graph_objects as go
from self_tracking.dashboard.components.controls import Select, Checkbox
import self_tracking.data as d
import dash_mantine_components as dmc
import pandas as pd
from self_tracking.importers.atracker import import_events

dash.register_page(__name__, title="ATracker")


periods = {
    "Total": "100YS",
    "Yearly": "YS",
    "Quarterly": "QS",
    "Monthly": "MS",
    "Weekly": "W-MON",
    "Daily": "D",
    "Calendar": "calendar",
}

aggregations = {
    "Daily average": "mean",
    "Total": "sum",
}


layout = html.Div(
    [
        dmc.Group(
            [
                Select("atracker-period", periods),
                Select("atracker-agg", aggregations),
                Checkbox("atracker-limit", "Limit bars"),
                Checkbox("atracker-omit-last", "Omit last day"),
                Checkbox("atracker-hide-sleep", "Hide Sleep"),
                dmc.Button(
                    id="atracker-refresh-button",
                    children="Refresh",
                    variant="outline",
                    loaderProps={"type": "dots"},
                ),
            ],
            gap="xl",
            justify="center",
        ),
        html.Div(id="atracker-chart"),
        dcc.Store(id="atracker-refresh-counter", data=0),
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
    df = d.atracker(use_names=True)
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


@dash.callback(
    Output("atracker-agg", "disabled"),
    Output("atracker-omit-last", "disabled"),
    Output("atracker-hide-sleep", "disabled"),
    Input("atracker-period", "value"),
)
def update_controls(rule: str):
    is_daily = rule == "D"
    is_calendar = rule == "calendar"
    return is_daily or is_calendar, is_calendar, is_calendar


def format_duration(hours: float):
    h, m = divmod(round(hours * 60), 60)
    return f"{h:02d}:{m:02d}"


def format_duration_long(hours: float):
    mins = int(round(hours * 60))
    h, m = divmod(mins, 60)
    return f"{h}h {m}m" if h else f"{m}m"


def split_event(row):
    if row.start.date() != row.end.date():
        first_event = row._replace(end=row.start.replace(hour=23, minute=59, second=59))
        second_event = row._replace(start=row.end.replace(hour=0, minute=0, second=0))
        return [first_event, second_event]
    else:
        return [row]


def create_calendar_chart(limit: bool):
    color_map = d.atracker_color_map(use_names=True)
    category_names = d.atracker_categories().name

    start = (datetime.now() - timedelta(weeks=4)).date().strftime("%Y-%m-%d")
    events = d.atracker_events(start)
    events["category"] = events.category.map(category_names)
    events["end"] = (
        events.start + pd.to_timedelta(events.duration, unit="h")
    ).dt.round("1s")

    split_events = []
    for row in events.itertuples(index=False):
        split_events.extend(split_event(row))
    events = pd.DataFrame(split_events)
    events["date"] = pd.to_datetime(events.start.dt.date)

    events["y_start"] = (
        events.start - events.start.dt.normalize()
    ).dt.total_seconds() / 3600
    events["height"] = (events.end - events.start).dt.total_seconds() / 3600
    events["duration_str"] = events.duration.apply(format_duration_long)

    if limit:
        cutoff_date = events.date.max() - timedelta(days=99)
        events = events.loc[events.date >= cutoff_date]

    fig = go.Figure()

    for category in reversed(color_map):
        cevents = events.loc[events.category == category]

        fig.add_trace(
            go.Bar(
                x=cevents.date,
                y=cevents.height,
                base=cevents.y_start,
                orientation="v",
                name=category,
                marker_color=color_map[category],
                customdata=cevents.duration_str,
                hovertemplate=f"{category}: %{{customdata}}<extra></extra>",
            )
        )

    fig.update_layout(
        barmode="stack",
        height=500,
        legend={"traceorder": "reversed", "x": 1},
        xaxis_title=None,
        legend_title=None,
        margin={"l": 40, "r": 0, "t": 20, "b": 0},
        yaxis=dict(
            title=None,
            autorange=False,
            range=[24, 0],
            tickmode="array",
            tickvals=list(range(0, 25, 2)),
            ticktext=[f"{str(h % 24).rjust(2, '0')}:00" for h in range(0, 25, 2)],
        ),
        xaxis=dict(
            autorange=False,
            range=[
                events.date.min() - timedelta(hours=12),
                events.date.max() + timedelta(hours=12),
            ],
        ),
    )

    return fig


@dash.callback(
    Output("atracker-chart", "children"),
    [
        Input("atracker-period", "value"),
        Input("atracker-agg", "value"),
        Input("atracker-limit", "checked"),
        Input("atracker-omit-last", "checked"),
        Input("atracker-hide-sleep", "checked"),
        Input("atracker-refresh-counter", "data"),
    ],
)
def update_graph(
    rule: str, agg: str, limit: bool, omit_last: bool, hide_sleep: bool, _n_clicks: int
):
    if rule == "calendar":
        fig = create_calendar_chart(limit)
        return dcc.Graph(figure=fig)

    df = get_df()

    if hide_sleep:
        df = df.drop(["Sleep"], axis=1)

    if omit_last:
        df = df.iloc[:-1]

    df = df.resample(rule, closed="left", label="left").agg(agg).reset_index()

    if limit:
        df = df.iloc[-100:]

    long = df.melt(id_vars="date", var_name="category", value_name="value")
    long = long.loc[long.value > 0]
    long["duration"] = long.value.apply(format_duration)

    color_map = d.atracker_color_map(use_names=True)

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
