import json
from pathlib import Path
import pandas as pd
import plotly.express as px


# %%
export_path = Path("~/Downloads/apple-media").expanduser()


# %%
games_path = export_path / "Game Center/Game Center Data.json"

with open(games_path) as f:
    data = json.load(f)

games = (
    pd.DataFrame(
        [
            {
                "name": game["game_name"],
                "last_played": pd.to_datetime(
                    game["last_played_utc"], dayfirst=False, utc=True
                ).tz_convert("Europe/London"),
                "achievements": len(game["achievements"]),
            }
            for game in data["game_state"]
        ]
    )
    .sort_values("last_played")
    .reset_index(drop=True)
)

games


# %%
music_path = (
    export_path
    / "Apple Media Services information Part 1 of 2/Apple_Media_Services/Apple Music Activity/Apple Music - Play History Daily Tracks.csv"
)

music = pd.read_csv(music_path)
music["date"] = pd.to_datetime(music["Date Played"], format="%Y%m%d")
music["duration"] = music["Play Duration Milliseconds"] / (1000 * 60 * 60)

df = music.groupby("date").duration.sum().to_frame()
df = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="D")).fillna(0)

px.bar(df.duration.resample("MS").sum())
