from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

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

WEEK = pd.Timedelta(days=7)

# Cal per lb of body weight per day, used for the basal estimate. Fixed here on
# purpose; the Energy Balance page is the place to play with this assumption.
BASAL_MULTIPLIER = 11.5

MIN_COLOR = "#E8A33D"
IDEAL_COLOR = "#4C9F70"

# Goal line weights. The stepped lines need more than the flat ones to read as
# equally heavy: their dash pattern restarts at every step, and they sit over a
# filled area and a solid series line rather than alone over bars.
GOAL_WIDTH = 2
STEP_GOAL_WIDTH = 4

DEFICIT_COLOR = "#4C9F70"
SURPLUS_COLOR = "#D1495B"


@dataclass(frozen=True)
class Chart:
    """One row of the dashboard.

    `weekly` is the (minimum, ideal) goal in the chart's own units (hours, or
    Cal for energy balance).

    Cumulative charts are accumulation goals: what matters is the weekly total,
    so daily mode draws a line climbing in real time as events happen, resetting
    each Monday midnight, against a target stepping up a day's share every day.
    They only need `weekly`.

    Non-cumulative charts are genuinely daily quantities, so they stay as bars
    against a flat line and need a separate `daily` threshold.
    """

    key: str
    title: str
    colors: dict[str, str]
    weekly: tuple[float, float]
    daily: tuple[float, float] | None = None
    unit: str = "hours"
    cumulative: bool = True

    def thresholds(self, mode: str) -> tuple[float, float]:
        if mode == "D" and self.daily is not None:
            return self.daily
        return self.weekly


# --- Goal thresholds -------------------------------------------------------
# Placeholder numbers, adjust to taste. Format is (minimum, ideal).
CHARTS = [
    Chart(
        key="meditation",
        title="Meditation",
        colors={"Meditation": "#A588B1"},
        weekly=(70 / 60, 210 / 60),
    ),
    Chart(
        key="project",
        title="Project",
        colors={"Project": "#3AA84F"},
        weekly=(5, 20),
    ),
    Chart(
        key="chores",
        title="Chores",
        colors={"Chores": "#8B529F"},
        weekly=(1, 3),
    ),
    Chart(
        key="cycling",
        title="Cycling",
        colors={"Outdoor": "#3AA8BC", "Indoor": "#1F6E7D"},
        weekly=(1.0, 5.0),
    ),
    Chart(
        key="strength",
        title="Strength training",
        colors={"Strength": "#E07B39"},
        weekly=(0.5, 1.5),
    ),
    Chart(
        key="energy",
        title="Energy balance",
        colors={"Balance": DEFICIT_COLOR},
        daily=(-100, -500),
        weekly=(-700, -3500),
        unit="cal",
        cumulative=False,
    ),
]


def format_hours(hours: float) -> str:
    if pd.isna(hours):
        return "-"
    h, m = divmod(int(round(hours * 60)), 60)
    return f"{h}:{m:02d}"


def rgba(color: str, alpha: float) -> str:
    r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


# --- Interval arithmetic ---------------------------------------------------
# Everything below works on raw events as half-open [start, end) intervals, so
# an event straddling midnight or a week boundary contributes its real share to
# each side instead of landing wholly in one bucket.


def to_hours(values) -> np.ndarray:
    """Timestamps as float hours since the epoch, for interval arithmetic."""
    index = pd.DatetimeIndex(values)
    return index.to_numpy().astype("datetime64[s]").astype(np.int64) / 3600


def intervals(start, duration) -> pd.DataFrame:
    """Events as naive local start/end pairs."""
    start = pd.DatetimeIndex(start).tz_localize(None)
    end = start + pd.to_timedelta(np.asarray(duration, dtype=float), unit="h")
    return pd.DataFrame({"start": start, "end": end})


def overlap_hours(events: pd.DataFrame, lo, hi) -> np.ndarray:
    """Event hours falling inside each [lo[i], hi[i]) window.

    `lo` may hold a single value to measure every window from a common origin,
    which is how the within-week running total is built.
    """
    lo_hours, hi_hours = to_hours(lo), to_hours(hi)
    if events.empty:
        return np.zeros(len(hi_hours))
    starts, ends = to_hours(events.start), to_hours(events.end)
    inside = np.minimum(ends[None, :], hi_hours[:, None]) - np.maximum(
        starts[None, :], lo_hours[:, None]
    )
    return np.clip(inside, 0, None).sum(axis=1)


def event_series(start_date: pd.Timestamp) -> dict[str, dict[str, pd.DataFrame]]:
    """Raw events per chart, per stacked series."""
    events = d.atracker_events(start_date.strftime("%Y-%m-%d"))
    workouts = d.workouts()

    def logged(category: str) -> pd.DataFrame:
        rows = events.loc[events.category == category]
        return intervals(rows.start, rows.duration)

    def workout(kind: str) -> pd.DataFrame:
        rows = workouts.loc[workouts.type == kind]
        return intervals(rows.index, rows.duration)

    return {
        "meditation": {"Meditation": logged("meditation")},
        "project": {"Project": logged("project")},
        "chores": {"Chores": logged("chores")},
        "cycling": {"Outdoor": workout("cycling"), "Indoor": workout("cycling_indoor")},
        "strength": {"Strength": workout("strength")},
    }


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


def weeks_shown(mode: str) -> pd.DatetimeIndex:
    """Monday midnights, the last being the current week's."""
    today = datetime.now().date()
    current = pd.Timestamp(today - timedelta(days=today.weekday()))
    count = DAILY_WEEKS if mode == "D" else WEEKLY_WEEKS
    return pd.date_range(end=current, periods=count, freq="7D", name="date")


def week_grid(
    series: dict[str, pd.DataFrame], start: pd.Timestamp, limit: pd.Timestamp
) -> pd.DatetimeIndex:
    """Times where the running total changes slope: week edges and event edges.

    The total is piecewise linear between these, so plotting them alone is exact
    and the line rises at a constant rate for the whole of an event.
    """
    points = {start, limit}
    for events in series.values():
        inside = events.loc[(events.end > start) & (events.start < limit)]
        # Edges outside the window clamp onto one of the two already in the set.
        points.update(inside.start[inside.start > start])
        points.update(inside.end[inside.end < limit])
    return pd.DatetimeIndex(sorted(points))


def add_burn_up(
    fig,
    row: int,
    chart: Chart,
    series: dict[str, pd.DataFrame],
    weeks: pd.DatetimeIndex,
    now: pd.Timestamp,
):
    """One line per week, climbing in real time and stacked where a chart has
    more than one series."""
    for start in weeks:
        limit = min(start + WEEK, now)
        if limit <= start:
            continue

        grid = week_grid(series, start, limit)
        origin = pd.DatetimeIndex([start])
        stacked = np.zeros(len(grid))

        for depth, (name, color) in enumerate(chart.colors.items()):
            own = overlap_hours(series[name], origin, grid)
            stacked = stacked + own
            fig.add_trace(
                go.Scatter(
                    x=grid,
                    y=stacked,
                    name=name,
                    mode="lines",
                    line=dict(color=color, width=2),
                    # Fills to the series below, so the top line is the total
                    # that the goal ramp is asking about.
                    fill="tonexty" if depth else "tozeroy",
                    fillcolor=rgba(color, 0.2),
                    customdata=[format_hours(v) for v in own],
                    hovertemplate=f"<b>%{{customdata}}</b> {name}<extra></extra>",
                ),
                row=row,
                col=1,
            )


def goal_steps(weeks: pd.DatetimeIndex, goal: float) -> tuple[list, list]:
    """Target line holding at n/7 of the weekly goal for the whole of day n.

    Stepping rather than sloping means the mark to beat is fixed for the day:
    clear today's step and you're on track, whatever time it is.
    """
    xs: list[Any] = []
    ys: list[Any] = []
    for start in weeks:
        for day in range(7):
            level = goal * (day + 1) / 7
            xs.extend(
                [start + pd.Timedelta(days=day), start + pd.Timedelta(days=day + 1)]
            )
            ys.extend([level, level])
        xs.append(None)
        ys.append(None)
    return xs, ys


@dash.callback(
    Output("home-chart", "children"),
    [Input("home-mode", "value")],
)
def update_graph(mode: str):
    weeks = weeks_shown(mode)
    now = pd.Timestamp.now()
    # A day of slack so events running into the first Monday are still fetched.
    series = event_series(weeks[0] - pd.Timedelta(days=1))
    energy = energy_balance()

    fig = make_subplots(
        rows=len(CHARTS),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.035,
        subplot_titles=[c.title for c in CHARTS],
    )

    for row, chart in enumerate(CHARTS, start=1):
        burn_up = mode == "D" and chart.cumulative

        if burn_up:
            add_burn_up(fig, row, chart, series[chart.key], weeks, now)
        elif chart.cumulative:
            totals = {
                name: overlap_hours(events, weeks, weeks + WEEK)
                for name, events in series[chart.key].items()
            }
            for name, color in chart.colors.items():
                values = totals[name]
                fig.add_trace(
                    go.Bar(
                        x=weeks,
                        y=values,
                        name=name,
                        marker_color=color,
                        customdata=[format_hours(v) for v in values],
                        hovertemplate=f"<b>%{{customdata}}</b> {name}<extra></extra>",
                    ),
                    row=row,
                    col=1,
                )
        else:
            if mode == "D":
                days = pd.date_range(weeks[0], periods=DAILY_WEEKS * 7, freq="D")
                values = energy.reindex(days)
                # Centre each bar in its day, so it spans midnight to midnight
                # against the same time axis the lines above are drawn on.
                x = days + pd.Timedelta(hours=12)
            else:
                values = (
                    energy.resample("W-MON", closed="left", label="left")
                    .sum(min_count=1)
                    .reindex(weeks)
                )
                x = weeks
            fig.add_trace(
                go.Bar(
                    x=x,
                    y=values.values,
                    name="Balance",
                    marker_color=[
                        DEFICIT_COLOR if v < 0 else SURPLUS_COLOR for v in values
                    ],
                    hovertemplate="<b>%{y:+,.0f}</b> Cal<extra></extra>",
                ),
                row=row,
                col=1,
            )
            fig.add_hline(y=0, line_width=1, line_color="grey", row=row, col=1)

        minimum, ideal = chart.thresholds(mode)
        for value, color in [(minimum, MIN_COLOR), (ideal, IDEAL_COLOR)]:
            if burn_up:
                xs, ys = goal_steps(weeks, value)
                fig.add_trace(
                    go.Scatter(
                        x=xs,
                        y=ys,
                        mode="lines",
                        line=dict(color=color, width=STEP_GOAL_WIDTH, dash="dash"),
                        hoverinfo="skip",
                    ),
                    row=row,
                    col=1,
                )
            else:
                fig.add_hline(
                    y=value,
                    line_width=GOAL_WIDTH,
                    line_dash="dash",
                    line_color=color,
                    row=row,
                    col=1,
                )

    if mode == "D":
        span = [weeks[0], weeks[-1] + WEEK]
        fig.update_xaxes(
            # Ticks at midday so each label sits under the middle of its day
            # rather than on the boundary between two.
            tick0=weeks[0] + pd.Timedelta(hours=12),
            dtick=24 * 60 * 60 * 1000,
            tickformat="%a<br>%b %d",
            hoverformat="%a %b %d, %H:%M",
        )
        # Separators on the week boundaries, matching the ATracker calendar view.
        for start in weeks[1:]:
            fig.add_vline(x=start, line_width=1, line_dash="dash", line_color="gray")
    else:
        pad = pd.Timedelta(days=4)
        span = [weeks[0] - pad, weeks[-1] + pad]
        fig.update_xaxes(tickformat="%b %d", hoverformat="Week of %b %d")

    fig.update_xaxes(autorange=False, range=span, showgrid=False)
    fig.update_yaxes(showgrid=False, rangemode="tozero")
    fig.update_annotations(font_size=13, xanchor="left", x=0)

    fig.update_layout(
        height=1200,
        barmode="stack",
        bargap=0.2,
        hovermode="x unified",
        showlegend=False,
        margin={"l": 50, "r": 10, "t": 60, "b": 20},
    )

    return dcc.Graph(figure=fig)


layout = html.Div(
    [
        dmc.Group([Select("home-mode", modes)], gap="xl", justify="center"),
        html.Div(id="home-chart"),
    ]
)
