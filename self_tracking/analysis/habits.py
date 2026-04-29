from datetime import timedelta
from typing import Any, cast

import pandas as pd
from rich.console import Console
from rich.text import Text

import self_tracking.data as d


console = Console()

SURFACE_0 = (49, 50, 68)
TEXT = (205, 214, 244)


def _parse_hex(value: str) -> tuple[int, int, int]:
    h = value.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _blend(
    fg: tuple[int, int, int], bg: tuple[int, int, int], alpha: float
) -> tuple[int, int, int]:
    alpha = max(0.0, min(1.0, alpha))
    return (
        int(fg[0] * alpha + bg[0] * (1 - alpha)),
        int(fg[1] * alpha + bg[1] * (1 - alpha)),
        int(fg[2] * alpha + bg[2] * (1 - alpha)),
    )


def _rgb(c: tuple[int, int, int]) -> str:
    return f"rgb({c[0]},{c[1]},{c[2]})"


def print_habit_calendar(
    title: str,
    series: pd.Series,
    color: str,
    num_weeks: int = 30,
    max_value: float | None = None,
):
    idx: Any = pd.DatetimeIndex(series.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    series = series.copy()
    series.index = idx.normalize()
    series = series.groupby(series.index).sum()

    today = pd.Timestamp.today().normalize()
    end_sunday = today + timedelta(days=6 - today.weekday())
    start_monday = end_sunday - timedelta(days=num_weeks * 7 - 1)

    full_range = pd.date_range(start_monday, end_sunday, freq="D")
    series = series.reindex(full_range, fill_value=0.0)

    resolved_max = max_value if max_value else float(series.max())
    if not resolved_max or pd.isna(resolved_max):
        resolved_max = 1.0

    full_color = _parse_hex(color)
    bg = _rgb(SURFACE_0)
    text_style = f"{_rgb(TEXT)} on {bg}"
    bg_style = f"on {bg}"

    pixel_width = 3
    pad_h = "   "
    content_width = num_weeks * pixel_width
    total_width = len(pad_h) * 2 + content_width

    month_row = [""] * num_weeks
    for week_idx in range(num_weeks):
        monday = start_monday + timedelta(days=week_idx * 7)
        if monday.day <= 7:
            month_row[week_idx] = monday.strftime("%b")

    def blank_line() -> Text:
        return Text(" " * total_width, style=bg_style)

    console.print()  # top margin

    console.print(blank_line())

    title_line = Text()
    title_line.append(pad_h, style=bg_style)
    title_line.append(title.ljust(content_width), style=f"bold {text_style}")
    title_line.append(pad_h, style=bg_style)
    console.print(title_line)

    console.print(blank_line())

    month_line = Text()
    month_line.append(pad_h, style=bg_style)
    for col in range(num_weeks):
        chunk = month_row[col].ljust(pixel_width)[:pixel_width]
        month_line.append(chunk, style=text_style)
    month_line.append(pad_h, style=bg_style)
    console.print(month_line)

    values = cast(Any, series.values).reshape(num_weeks, 7).T

    for dow in range(7):
        line = Text()
        line.append(pad_h, style=bg_style)
        for week_idx in range(num_weeks):
            date = start_monday + timedelta(days=week_idx * 7 + dow)
            if date > today:
                line.append("   ", style=bg_style)
                continue
            value = float(values[dow, week_idx])
            alpha = 0.1 + 0.9 * (value / resolved_max)
            cell = _rgb(_blend(full_color, SURFACE_0, alpha))
            line.append("██", style=f"{cell} on {bg}")
            line.append(" ", style=bg_style)
        line.append(pad_h, style=bg_style)
        console.print(line)

    console.print(blank_line())
    console.print()  # bottom margin


if __name__ == "__main__":
    print_habit_calendar("Project work", d.atracker().project, color="#3AA84F")

    workouts = d.workouts()
    workout_idx: Any = pd.DatetimeIndex(workouts.index)
    workout_daily = workouts.duration.groupby(
        workout_idx.tz_convert(None).normalize()
    ).sum()
    print_habit_calendar("Workouts", workout_daily, color="#3AA8BC")
