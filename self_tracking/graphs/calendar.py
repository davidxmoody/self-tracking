import self_tracking.data as d
import plotly.express as px
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd

# %%
categories = d.atracker_categories()
color_map = categories.set_index("category").color.to_dict()
events = d.atracker_events()
events["end"] = events.start + events.duration


# %%
def split(row):
    if row.start.date() != row.end.date():
        first_event = row.copy()
        first_event["end"] = row.start.replace(hour=23, minute=59, second=59)

        second_event = row.copy()
        second_event["start"] = row.end.replace(hour=0, minute=0, second=0)

        return [first_event, second_event]
    else:
        return [row]


split_events = []
for _, row in events.iterrows():
    split_events.extend(split(row))
events = pd.DataFrame(split_events)


# %%
tz = ZoneInfo("Europe/London")
now = datetime.now(tz)
start_of_week = now - timedelta(days=now.weekday())
start_of_week = start_of_week - timedelta(weeks=1)
start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
end_of_week = start_of_week + timedelta(weeks=1)

events_week = events.loc[
    (events["end"] >= start_of_week) & (events["start"] <= end_of_week)
].copy()

events_week["weekday"] = events_week.end.dt.day_name()

events_week["start_datetime"] = events_week["start"].apply(
    lambda x: start_of_week.replace(hour=x.hour, minute=x.minute, second=x.second)
)
events_week["end_datetime"] = events_week["end"].apply(
    lambda x: start_of_week.replace(hour=x.hour, minute=x.minute, second=x.second)
)

# %%
fig = px.timeline(
    events_week,
    x_start="start_datetime",
    x_end="end_datetime",
    y="weekday",
    color="category",
    title="Weekly Calendar",
    labels={"category": "Event"},
    color_discrete_map=color_map,
    category_orders={
        "category": color_map.keys(),
        "weekday": [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ],
    },
)

fig.update_xaxes(
    tickformat="%H:%M",
    dtick=60 * 60 * 1000,
    showgrid=True,
    range=[
        start_of_week.replace(hour=0, minute=0, second=0),
        start_of_week.replace(hour=23, minute=59, second=59),
    ],
)

fig.show()
