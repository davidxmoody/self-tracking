from datetime import date, timedelta
from typing import Any, cast

import dash
import dash_leaflet as dl
import dash_mantine_components as dmc
from dash import Input, Output, html
from dash_extensions.javascript import arrow_function, variable

from self_tracking.dashboard.components.controls import Checkbox, Select
from self_tracking.routes import route_index, to_date

dash.register_page(__name__, title="Routes")


# %%
activity_colors = {
    "cycling": "#FF00FF",
    "running": "#00FFFF",
    "walking": "#FFA500",
}

# Sequential amber ramp, mirroring the one in assets/routes.js
date_ramp = ["#FFE0A3", "#FDC161", "#F79E28", "#E67912", "#C25A0A"]

center_point = (51.44919535475215, -2.608414238285152)

routes_url = "/assets/routes.pbf"

routes = route_index()
first_day = min(day for day, _ in routes)
last_day = max(day for day, _ in routes)

presets = {
    "all": "All",
    "year": "This year",
    "12m": "Last 12 months",
    "90d": "Last 90 days",
}


def year_marks():
    years = range(to_date(first_day).year + 1, to_date(last_day).year + 1)
    return [
        {"value": (date(year, 1, 1) - date(1970, 1, 1)).days, "label": f"'{year % 100}"}
        for year in years
    ]


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
                Select("routes-color-by", {"Activity": "activity", "Date": "date"}),
            ],
        ),
        dmc.Group(
            justify="center",
            gap="xs",
            children=[
                dmc.Button(
                    label,
                    id=f"routes-preset-{key}",
                    variant="default",
                    size="compact-sm",
                )
                for key, label in presets.items()
            ],
        ),
        dmc.Box(
            px="xl",
            pb="lg",
            children=dmc.RangeSlider(
                id="routes-range",
                min=first_day,
                max=last_day,
                step=1,
                minRange=0,
                value=[first_day, last_day],
                marks=cast(Any, year_marks()),
                label=None,
                persistence_type="local",
                persistence=True,
            ),
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
            style={"height": "calc(100vh - 260px)", "minHeight": "400px"},
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
    Output("routes-range", "value"),
    [Input(f"routes-preset-{key}", "n_clicks") for key in presets],
    prevent_initial_call=True,
)
def apply_preset(*_):
    today = date.today()
    starts = {
        "all": to_date(first_day),
        "year": date(today.year, 1, 1),
        "12m": today - timedelta(days=365),
        "90d": today - timedelta(days=90),
    }
    key = str(dash.ctx.triggered_id).removeprefix("routes-preset-")
    start = (starts[key] - date(1970, 1, 1)).days
    return [max(first_day, start), last_day]


@dash.callback(
    [
        Output("routes-geojson", "hideout"),
        Output("routes-geojson", "url"),
        Output("routes-readout", "children"),
        Output("routes-legend", "children"),
    ],
    [
        Input("routes-range", "value"),
        Input("routes-color-by", "value"),
        *[Input(f"routes-{activity}", "checked") for activity in activity_colors],
    ],
)
def update_filter(day_range: list[int], color_by: str, *checked: bool):
    (min_day, max_day) = day_range
    activities = [a for a, on in zip(activity_colors, checked) if on]

    hideout = {
        "minDay": min_day,
        "maxDay": max_day,
        "activities": activities,
        "colorBy": color_by,
        "activityColors": activity_colors,
    }

    visible = sum(
        1
        for day, activity in routes
        if min_day <= day <= max_day and activity in activities
    )
    readout = (
        f"{to_date(min_day)} → {to_date(max_day)} · "
        f"{visible} route{'' if visible == 1 else 's'}"
    )

    return (
        hideout,
        routes_url,
        readout,
        legend(color_by, activities, min_day, max_day),
    )


def legend(color_by: str, activities: list[str], min_day: int, max_day: int):
    if color_by == "date":
        gradient = f"linear-gradient(to right, {', '.join(date_ramp)})"
        return dmc.Group(
            gap="xs",
            children=[
                dmc.Text(str(to_date(min_day)), size="xs", c="dimmed"),
                dmc.Box(w=120, h=8, style={"background": gradient, "borderRadius": 4}),
                dmc.Text(str(to_date(max_day)), size="xs", c="dimmed"),
            ],
        )

    return dmc.Group(
        gap="md",
        children=[
            dmc.Group(
                gap=6,
                children=[
                    dmc.Box(
                        w=16,
                        h=3,
                        style={
                            "background": activity_colors[activity],
                            "borderRadius": 2,
                        },
                    ),
                    dmc.Text(activity.title(), size="xs", c="dimmed"),
                ],
            )
            for activity in activities
        ],
    )
