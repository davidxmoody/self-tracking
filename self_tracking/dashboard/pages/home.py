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

    `weekly` is the (minimum, ideal) goal in the chart's own units (hours, or
    Cal for energy balance).

    Cumulative charts are accumulation goals: what matters is the weekly total,
    so daily mode plots a running total that resets each Monday and compares it
    against a target that ramps up across the week. They only need `weekly`.

    Non-cumulative charts are genuinely daily quantities, so they plot raw daily
    values against a flat line and need a separate `daily` threshold.
    """

    key: str
    title: str
    colors: dict[str, str]
    weekly: tuple[float, float]
    daily: tuple[float, float] | None = None
    unit: str = "hours"
    legend: bool = False
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
        weekly=(3.0, 6.0),
        legend=True,
    ),
    Chart(
        key="strength",
        title="Strength training",
        colors={"Strength": "#E07B39"},
        weekly=(2.0, 3.0),
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


def prepare(
    frame: pd.DataFrame, mode: str, index: pd.DatetimeIndex, cumulative: bool
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bar heights and the per-bar increments they're built from.

    The two differ only for a cumulative chart in daily mode, where the bar is
    the week-to-date total but the hover still wants that day's own value.
    """
    if mode == "W":
        frame = frame.resample("W-MON", closed="left", label="left").sum(min_count=1)
        frame = frame.reindex(index)
        return frame, frame

    frame = frame.reindex(index)

    if not cumulative:
        return frame, frame

    frame = frame.fillna(0.0)
    # Days that haven't happened yet would otherwise draw a flat run of bars out
    # to Sunday, which reads as real data. cumsum leaves them NaN and carries
    # the running total across, though nothing follows them within the week.
    frame.loc[index > pd.Timestamp(datetime.now().date())] = np.nan

    week_start = index - pd.to_timedelta(index.dayofweek, unit="D")
    return frame.groupby(week_start).cumsum(), frame


def ramp(index: pd.DatetimeIndex, goal: float) -> tuple[list, list]:
    """Points for a target line climbing from 0 to `goal` across each week.

    Anchored to the week boundaries (midnight +/- 12h, where the separators sit)
    and passing through goal * n/7 at the right edge of the nth day's bar, so
    "am I above the line" is a fair question on any day of the week, not just
    Sunday.
    """
    day = pd.Timedelta(hours=12)
    xs: list[Any] = []
    ys: list[Any] = []

    for week in range(DAILY_WEEKS):
        days = index[week * 7 : (week + 1) * 7]
        xs.append(days[0] - day)
        ys.append(0.0)
        for n, date in enumerate(days, start=1):
            xs.append(date + day)
            ys.append(goal * n / 7)
        # Break the line so weeks don't get joined up by a diagonal.
        xs.append(None)
        ys.append(None)

    return xs, ys


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
        values, increments = prepare(frames[chart.key], mode, index, chart.cumulative)
        burn_up = mode == "D" and chart.cumulative

        if chart.unit == "hours":
            if mode == "W":
                values = values.fillna(0.0)
                increments = values
            for name, color in chart.colors.items():
                bars = values[name]
                if burn_up:
                    customdata = list(
                        zip(
                            [format_hours(v) for v in increments[name]],
                            [format_hours(v) for v in bars],
                        )
                    )
                    hovertemplate = (
                        f"<b>%{{customdata[0]}}</b> {name}"
                        "  (%{customdata[1]} this week)<extra></extra>"
                    )
                else:
                    customdata = [format_hours(v) for v in bars]
                    hovertemplate = f"<b>%{{customdata}}</b> {name}<extra></extra>"
                fig.add_trace(
                    go.Bar(
                        x=bars.index,
                        y=bars.values,
                        name=name,
                        marker_color=color,
                        showlegend=chart.legend,
                        customdata=customdata,
                        hovertemplate=hovertemplate,
                    ),
                    row=row,
                    col=1,
                )
        else:
            bars = values.Balance
            fig.add_trace(
                go.Bar(
                    x=bars.index,
                    y=bars.values,
                    name="Balance",
                    marker_color=[
                        DEFICIT_COLOR if v < 0 else SURPLUS_COLOR for v in bars
                    ],
                    showlegend=False,
                    hovertemplate="<b>%{y:+,.0f}</b> Cal<extra></extra>",
                ),
                row=row,
                col=1,
            )
            fig.add_hline(y=0, line_width=1, line_color="grey", row=row, col=1)

        minimum, ideal = chart.thresholds(mode)
        for value, color, label in [
            (minimum, MIN_COLOR, "Minimum"),
            (ideal, IDEAL_COLOR, "Ideal"),
        ]:
            if burn_up:
                xs, ys = ramp(index, value)
                fig.add_trace(
                    go.Scatter(
                        x=xs,
                        y=ys,
                        mode="lines",
                        name=label,
                        legendgroup=label,
                        # One entry for the whole figure; the group toggles the rest.
                        showlegend=row == 1,
                        line=dict(color=color, width=1, dash="dash"),
                        hoverinfo="skip",
                    ),
                    row=row,
                    col=1,
                )
            else:
                fig.add_hline(
                    y=value,
                    line_width=1,
                    line_dash="dash",
                    line_color=color,
                    row=row,
                    col=1,
                )

    if mode == "W":
        # Flat threshold lines are shapes rather than traces, so they need dummy
        # traces to appear in the legend. In daily mode the ramps do it themselves.
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
