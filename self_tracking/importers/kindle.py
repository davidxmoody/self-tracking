from pathlib import Path
import pandas as pd


# %%
kindle_dir = Path("~/Downloads/kindle").expanduser()


insights = pd.read_csv(
    kindle_dir.joinpath(
        "Kindle.ReadingInsights/datasets/Kindle.reading-insights-sessions_with_adjustments/Kindle.reading-insights-sessions_with_adjustments.csv"
    )
)

insights["start"] = (
    pd.to_datetime(insights.start_time, format="ISO8601", utc=True)
    .dt.tz_convert("Europe/London")
    .dt.round("1s")
)

insights["duration"] = pd.to_timedelta(
    insights.total_reading_milliseconds, unit="ms"
).dt.round("1s")


whispersync = pd.read_csv(
    kindle_dir.joinpath("Digital.Content.Whispersync/whispersync.csv")
)

book_titles = whispersync.drop_duplicates("ASIN").set_index("ASIN")["Product Name"]


insights["title"] = insights.ASIN.map(book_titles).fillna("Not Available")

insights = insights[["start", "duration", "title"]]
