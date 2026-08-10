from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, cast

import dash
import dash_mantine_components as dmc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import statsmodels.api as sm
from dash import Input, Output, dcc, html
from plotly.subplots import make_subplots

import self_tracking.data as d
from self_tracking.dashboard.components.controls import Select

dash.register_page(__name__, path="/", title="Home")


modes = {
    "Daily": "D",
    "Weekly": "W",
}

# Daily mode shows this many Mon-Sun weeks, the last being the current one.
DAILY_WEEKS = 3

# Weekly mode shows this many weeks, the last being the current (partial) one.
WEEKLY_WEEKS = 20

# Cal per lb of body weight per day, used for the basal estimate. Fixed here on
# purpose; the Energy Balance page is the place to play with this assumption.
BASAL_MULTIPLIER = 11.5

MIN_COLOR = "#E8A33D"
IDEAL_COLOR = "#4C9F70"

DEFICIT_COLOR = "#4C9F70"
SURPLUS_COLOR = "#D1495B"


@dataclass(frozen=True)
class Chart:
    """One row of the dashboard.

    `daily` / `weekly` are (minimum, ideal) goal thresholds in the chart's own
    units (hours, or Cal for energy balance). They're set independently rather
    than derived as daily x 7 because most goals don't scale that way.
    """

    key: str
    title: str
    colors: dict[str, str]
    daily: tuple[float, float]
    weekly: tuple[float, float]
    unit: str = "hours"
    legend: bool = False

    def thresholds(self, mode: str) -> tuple[float, float]:
        return self.daily if mode == "D" else self.weekly


# --- Goal thresholds -------------------------------------------------------
# Placeholder numbers, adjust to taste. Format is (minimum, ideal).
CHARTS = [
    Chart(
        key="meditation",
        title="Meditation",
        colors={"Meditation": "#A588B1"},
        daily=(10 / 60, 30 / 60),
        weekly=(70 / 60, 210 / 60),
    ),
    Chart(
        key="project",
        title="Project",
        colors={"Project": "#3AA84F"},
        daily=(5 / 7, 20 / 7),
        weekly=(5, 20),
    ),
    Chart(
        key="chores",
        title="Chores",
        colors={"Chores": "#8B529F"},
        daily=(1 / 7, 3 / 7),
        weekly=(1, 3),
    ),
    Chart(
        key="cycling",
        title="Cycling",
        colors={"Outdoor": "#3AA8BC", "Indoor": "#1F6E7D"},
        daily=(0.5, 1.0),
        weekly=(3.0, 6.0),
        legend=True,
    ),
    Chart(
        key="strength",
        title="Strength training",
        colors={"Strength": "#E07B39"},
        daily=(0.5, 1.0),
        weekly=(2.0, 3.0),
    ),
    Chart(
        key="energy",
        title="Energy balance",
        colors={"Balance": DEFICIT_COLOR},
        daily=(-100, -500),
        weekly=(-700, -3500),
        unit="cal",
    ),
]


def format_hours(hours: float) -> str:
    h, m = divmod(int(round(hours * 60)), 60)
    return f"{h}:{m:02d}"


def workout_hours(workout_type: str) -> pd.Series:
    """Daily hours for one workout type, using ATracker's 6am day boundary."""
    df = d.workouts()
    df = df.loc[df.type == workout_type]
    date = pd.to_datetime((cast(Any, df.index) - pd.Timedelta(hours=6)).date)
    return df.duration.groupby(date).sum().rename_axis("date")


def energy_balance() -> pd.Series:
    """Daily eaten - active - basal, in Cal."""
    eaten = d.diet().calories
    start, end = eaten.index.min(), eaten.index.max()

    active = d.activity().active_calories[start:end]
    weight_raw = d.weight().weight[start:end].dropna()

    lowess_result = sm.nonparametric.lowess(
        weight_raw, weight_raw.index.astype(np.int64), frac=0.03
    )
    weight = (
        pd.Series(data=lowess_result[:, 1], index=pd.to_datetime(lowess_result[:, 0]))
        .reindex(pd.date_range(start, end))
        .interpolate(method="time")
        # Carry the last smoothed weight forward so a few days without a
        # weigh-in don't blank out the most recent bars.
        .ffill()
    )

    return (eaten - active - weight * BASAL_MULTIPLIER).round().rename_axis("date")


def daily_frames() -> dict[str, pd.DataFrame]:
    """Per-chart daily values, one column per stacked series."""
    atracker = d.atracker(use_names=True)

    return {
        "meditation": atracker[["Meditation"]],
        "project": atracker[["Project"]],
        "chores": atracker[["Chores"]],
        "cycling": pd.DataFrame(
            {
                "Outdoor": workout_hours("cycling"),
                "Indoor": workout_hours("cycling_indoor"),
            }
        ),
        "strength": pd.DataFrame({"Strength": workout_hours("strength")}),
        "energy": pd.DataFrame({"Balance": energy_balance()}),
    }


def target_index(mode: str) -> pd.DatetimeIndex:
    """The x values to plot, padded into the future where data doesn't exist."""
    today = datetime.now().date()
    current_week_start = pd.Timestamp(today - timedelta(days=today.weekday()))

    if mode == "D":
        start = current_week_start - pd.Timedelta(weeks=DAILY_WEEKS - 1)
        return pd.date_range(start, periods=DAILY_WEEKS * 7, freq="D", name="date")

    return pd.date_range(
        end=current_week_start, periods=WEEKLY_WEEKS, freq="7D", name="date"
    )


def prepare(frame: pd.DataFrame, mode: str, index: pd.DatetimeIndex) -> pd.DataFrame:
    if mode == "W":
        frame = frame.resample("W-MON", closed="left", label="left").sum(min_count=1)
    return frame.reindex(index)


@dash.callback(
    Output("home-chart", "children"),
    [Input("home-mode", "value")],
)
def update_graph(mode: str):
    frames = daily_frames()
    index = target_index(mode)

    fig = make_subplots(
        rows=len(CHARTS),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.035,
        subplot_titles=[c.title for c in CHARTS],
    )

    for row, chart in enumerate(CHARTS, start=1):
        frame = prepare(frames[chart.key], mode, index)

        if chart.unit == "hours":
            frame = frame.fillna(0.0)
            for name, color in chart.colors.items():
                values = frame[name]
                fig.add_trace(
                    go.Bar(
                        x=values.index,
                        y=values.values,
                        name=name,
                        marker_color=color,
                        showlegend=chart.legend,
                        customdata=[format_hours(v) for v in values],
                        hovertemplate=f"<b>%{{customdata}}</b> {name}<extra></extra>",
                    ),
                    row=row,
                    col=1,
                )
        else:
            values = frame.Balance
            fig.add_trace(
                go.Bar(
                    x=values.index,
                    y=values.values,
                    name="Balance",
                    marker_color=[
                        DEFICIT_COLOR if v < 0 else SURPLUS_COLOR for v in values
                    ],
                    showlegend=False,
                    hovertemplate="<b>%{y:+,.0f}</b> Cal<extra></extra>",
                ),
                row=row,
                col=1,
            )
            fig.add_hline(y=0, line_width=1, line_color="grey", row=row, col=1)

        minimum, ideal = chart.thresholds(mode)
        for value, color in [(minimum, MIN_COLOR), (ideal, IDEAL_COLOR)]:
            fig.add_hline(
                y=value,
                line_width=1,
                line_dash="dash",
                line_color=color,
                row=row,
                col=1,
            )

    # Dummy traces so the dashed threshold lines get a single shared legend
    # entry instead of being annotated on every subplot.
    for label, color in [("Minimum", MIN_COLOR), ("Ideal", IDEAL_COLOR)]:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                name=label,
                line=dict(color=color, width=1, dash="dash"),
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )

    if mode == "D":
        pad = pd.Timedelta(hours=12)
        fig.update_xaxes(tickformat="%a<br>%b %d", dtick="D1", hoverformat="%a %b %d")
        # Separators between the weeks, matching the ATracker calendar view.
        for week in range(1, DAILY_WEEKS):
            fig.add_vline(
                x=index[week * 7] - pad,
                line_width=1,
                line_dash="dash",
                line_color="gray",
            )
    else:
        pad = pd.Timedelta(days=4)
        fig.update_xaxes(tickformat="%b %d", hoverformat="Week of %b %d")

    fig.update_xaxes(
        autorange=False, range=[index[0] - pad, index[-1] + pad], showgrid=False
    )
    fig.update_yaxes(showgrid=False)
    fig.update_annotations(font_size=13, xanchor="left", x=0)

    fig.update_layout(
        height=1200,
        barmode="stack",
        bargap=0.2,
        hovermode="x unified",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "x": 1,
            "xanchor": "right",
        },
        margin={"l": 50, "r": 10, "t": 60, "b": 20},
    )

    return dcc.Graph(figure=fig)


layout = html.Div(
    [
        dmc.Group([Select("home-mode", modes)], gap="xl", justify="center"),
        html.Div(id="home-chart"),
    ]
)
