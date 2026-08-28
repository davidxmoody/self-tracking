from typing import Any, cast

import dash
import dash_leaflet as dl
import dash_mantine_components as dmc
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html
from dash_extensions.javascript import arrow_function, variable

from self_tracking.dashboard.components.controls import Checkbox, Select
from self_tracking.routes import route_metadata, to_date

dash.register_page(__name__, title="Routes")


# %%
activity_colors = {
    "cycling": "#FF00FF",
    "running": "#00FFFF",
    "walking": "#FFA500",
}

# Sequential amber ramp, mirroring the one in assets/routes.js
date_ramp = ["#FFE0A3", "#FDC161", "#F79E28", "#E67912", "#C25A0A"]

# The chart shares the map's colours, so it takes the map's dark surface too -
# the bright activity hues are unreadable on a light background
surface = "#1a1a19"

center_point = (51.44919535475215, -2.608414238285152)

routes_url = "/assets/routes.pbf"

periods = {
    "Day": "D",
    "Week": "W-MON",
    "Month": "MS",
    "Quarter": "QS",
    "Year": "YS",
}

routes = route_metadata()
epoch = pd.Timestamp("1970-01-01")
full_range = (routes.date.min(), routes.date.max())


def to_day(timestamp: pd.Timestamp) -> int:
    return int((timestamp.normalize() - epoch).days)


# %%
def build_figure(rule: str, activities: list[str], x_range) -> go.Figure:
    selected = routes[routes.activity.isin(activities)]

    fig = go.Figure()
    if not selected.empty:
        binned = (
            selected.set_index("date")
            .groupby("activity")
            .duration.resample(rule, label="left", closed="left")
            .sum()
            .unstack("activity")
            .fillna(0)
        )
        # Fixed order, so a hidden activity never repaints the others
        for activity in activity_colors:
            if activity not in binned:
                continue
            fig.add_trace(
                go.Bar(
                    x=binned.index,
                    y=binned[activity],
                    name=activity.title(),
                    marker_color=activity_colors[activity],
                    hovertemplate="%{x|%Y-%m-%d}<br>%{y:.1f} h<extra>%{fullData.name}</extra>",
                )
            )

    fig.update_layout(
        barmode="stack",
        bargap=0.15,
        height=230,
        margin=dict(l=45, r=15, t=25, b=5),
        paper_bgcolor=surface,
        plot_bgcolor=surface,
        font=dict(color="#c3c2b7", size=11),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            traceorder="normal",
            x=1,
            y=1.12,
            xanchor="right",
            yanchor="top",
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    fig.update_yaxes(
        title=dict(text="Hours", font=dict(size=11)),
        gridcolor="#33332f",
        zerolinecolor="#33332f",
    )
    fig.update_xaxes(
        type="date",
        range=list(x_range),
        showgrid=False,
        rangeslider=dict(
            visible=True,
            thickness=0.28,
            bgcolor=surface,
            bordercolor="#4a4a45",
            borderwidth=1,
        ),
    )
    return fig


def selected_range(relayout: dict | None):
    """Pull the range out of a graph relayout, whose shape varies by gesture."""
    if not relayout or relayout.get("xaxis.autorange"):
        return full_range

    if "xaxis.range" in relayout:
        (low, high) = relayout["xaxis.range"]
    elif "xaxis.range[0]" in relayout:
        (low, high) = (relayout["xaxis.range[0]"], relayout["xaxis.range[1]"])
    else:
        return full_range

    return (pd.to_datetime(low), pd.to_datetime(high))


# %%
def base_layers():
    return [
        dl.BaseLayer(
            dl.TileLayer(
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attribution="Tiles &copy; Esri",
                maxZoom=19,
            ),
            name="Satellite",
            checked=True,
        ),
        dl.BaseLayer(
            dl.TileLayer(
                url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png",
                attribution="&copy; OpenStreetMap contributors &copy; CARTO",
            ),
            name="Colour",
        ),
        dl.BaseLayer(
            dl.TileLayer(
                url="https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png",
                attribution="&copy; OpenStreetMap contributors &copy; CARTO",
            ),
            name="Greyscale",
        ),
    ]


def overlays():
    return [
        dl.Overlay(
            dl.TileLayer(
                url="https://tile.waymarkedtrails.org/cycling/{z}/{x}/{y}.png",
                attribution="&copy; waymarkedtrails.org",
            ),
            name="Cycling trails",
            checked=False,
        ),
        dl.Overlay(
            dl.TileLayer(
                url="https://tile.waymarkedtrails.org/hiking/{z}/{x}/{y}.png",
                attribution="&copy; waymarkedtrails.org",
            ),
            name="Hiking trails",
            checked=False,
        ),
        dl.Overlay(
            dl.TileLayer(
                url="https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png",
                attribution="&copy; OpenStreetMap contributors &copy; CARTO",
            ),
            name="Place names",
            checked=False,
        ),
    ]


# %%
layout = dmc.Stack(
    gap="sm",
    children=[
        dmc.Group(
            justify="center",
            gap="xl",
            children=[
                dmc.Group(
                    gap="md",
                    children=[
                        Checkbox(f"routes-{activity}", activity.title())
                        for activity in activity_colors
                    ],
                ),
                dmc.SegmentedControl(
                    id="routes-period",
                    value=periods["Month"],
                    data=cast(
                        Any, [{"value": v, "label": k} for k, v in periods.items()]
                    ),
                    persistence_type="local",
                    persistence=True,
                ),
                Select("routes-color-by", {"Activity": "activity", "Date": "date"}),
            ],
        ),
        dcc.Graph(
            id="routes-chart",
            config={"displayModeBar": False},
            figure=build_figure(periods["Month"], list(activity_colors), full_range),
        ),
        dmc.Group(
            justify="center",
            gap="lg",
            mih=24,
            children=[
                dmc.Text(id="routes-readout", size="sm", c="dimmed"),
                html.Div(id="routes-legend"),
            ],
        ),
        dl.Map(
            id="routes-map",
            center=cast(Any, center_point),
            zoom=12,
            preferCanvas=True,
            style={"height": "calc(100vh - 400px)", "minHeight": "360px"},
            children=[
                dl.LayersControl(base_layers() + overlays()),
                dl.GeoJSON(
                    id="routes-geojson",
                    # url is supplied by the callback below, so the geometry only
                    # loads once hideout reflects the (persisted) control values
                    format="geobuf",
                    filter=variable("dashExtensions", "routes", "filter"),
                    style=variable("dashExtensions", "routes", "style"),
                    onEachFeature=variable("dashExtensions", "routes", "onEachFeature"),
                    hoverStyle=arrow_function(dict(weight=6, opacity=1)),
                ),
            ],
        ),
    ],
)


# %%
@dash.callback(
    Output("routes-chart", "figure"),
    [
        Input("routes-period", "value"),
        *[Input(f"routes-{activity}", "checked") for activity in activity_colors],
    ],
    State("routes-chart", "relayoutData"),
)
def update_chart(rule: str, *args):
    (*checked, relayout) = args
    activities = [a for a, on in zip(activity_colors, checked) if on]
    # Rebuilding resets the axis, so carry the current selection across
    return build_figure(rule, activities, selected_range(relayout))


@dash.callback(
    [
        Output("routes-geojson", "hideout"),
        Output("routes-geojson", "url"),
        Output("routes-readout", "children"),
        Output("routes-legend", "children"),
    ],
    [
        Input("routes-chart", "relayoutData"),
        Input("routes-color-by", "value"),
        *[Input(f"routes-{activity}", "checked") for activity in activity_colors],
    ],
)
def update_filter(relayout: dict | None, color_by: str, *checked: bool):
    (low, high) = selected_range(relayout)
    (min_day, max_day) = (to_day(low), to_day(high))
    activities = [a for a, on in zip(activity_colors, checked) if on]

    hideout = {
        "minDay": min_day,
        "maxDay": max_day,
        "activities": activities,
        "colorBy": color_by,
        "activityColors": activity_colors,
    }

    visible = routes[
        routes.day.between(min_day, max_day) & routes.activity.isin(activities)
    ]
    readout = (
        f"{to_date(min_day)} → {to_date(max_day)} · "
        f"{len(visible)} route{'' if len(visible) == 1 else 's'} · "
        f"{visible.duration.sum():.1f} h"
    )

    return hideout, routes_url, readout, legend(color_by, min_day, max_day)


def legend(color_by: str, min_day: int, max_day: int):
    # Activity identity is already carried by the chart legend, so the map only
    # needs one of its own for the date ramp
    if color_by != "date":
        return None

    gradient = f"linear-gradient(to right, {', '.join(date_ramp)})"
    return dmc.Group(
        gap="xs",
        children=[
            dmc.Text(str(to_date(min_day)), size="xs", c="dimmed"),
            dmc.Box(w=120, h=8, style={"background": gradient, "borderRadius": 4}),
            dmc.Text(str(to_date(max_day)), size="xs", c="dimmed"),
        ],
    )
