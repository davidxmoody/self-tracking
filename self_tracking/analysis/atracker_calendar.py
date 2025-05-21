from datetime import datetime, timedelta
from typing import Any
import self_tracking.data as d
import plotly.graph_objects as go
import pandas as pd


# %%
color_map = d.atracker_color_map()

start = (datetime.now() - timedelta(weeks=4)).date().strftime("%Y-%m-%d")
events = d.atracker_events(start)
events["end"] = (events.start + pd.to_timedelta(events.duration, unit="h")).dt.round(
    "1s"
)


def split(row) -> list[Any]:
    if row.start.date() != row.end.date():
        first_event = row._replace(end=row.start.replace(hour=23, minute=59, second=59))
        second_event = row._replace(start=row.end.replace(hour=0, minute=0, second=0))
        return [first_event, second_event]
    else:
        return [row]


split_events = []
for row in events.itertuples(index=False):
    split_events.extend(split(row))
events = pd.DataFrame(split_events)
events["date"] = pd.to_datetime(events.start.dt.date)

events["y_start"] = (
    events.start - events.start.dt.normalize()
).dt.total_seconds() / 3600
events["height"] = (events.end - events.start).dt.total_seconds() / 3600


def format_duration(hours):
    mins = int(round(hours * 60))
    h, m = divmod(mins, 60)
    return f"{h}h {m}m" if h else f"{m}m"


events["duration_str"] = events.duration.apply(format_duration)


# %%
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
    yaxis=dict(
        title="Time",
        autorange=False,
        range=[24, 0],
        tickmode="array",
        tickvals=list(range(0, 25, 2)),
        ticktext=[f"{str(h % 24).rjust(2, "0")}:00" for h in range(0, 25, 2)],
    ),
    xaxis=dict(
        title="Date",
        autorange=False,
        range=[
            events.date.min() - timedelta(hours=12),
            events.date.max() + timedelta(hours=12),
        ],
    ),
)

fig
