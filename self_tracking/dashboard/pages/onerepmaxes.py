import dash
from dash import dcc
from datetime import timedelta
from math import ceil
import self_tracking.data as d
import plotly.express as px
import pandas as pd

dash.register_page(__name__, title="One Rep Maxes")

df = d.strength()
df["date"] = pd.to_datetime(df.start.dt.date)

workout_dates = df.date.unique()
programs = d.strength_programs()
programs["num"] = programs.apply(
    lambda row: sum(1 for w in workout_dates if w >= row.start and w <= row.end), axis=1
)

tracked_exercises = {
    "Deadlift (Barbell)": "Deadlift",
    "Squat (Barbell)": "Squat",
    "Bench Press (Barbell)": "Bench",
    "Overhead Press (Barbell)": "Overhead",
}

df = df.loc[
    df.exercise.isin(tracked_exercises),
    ["date", "exercise", "weight", "reps"],
]

df["exercise"] = df.exercise.map(tracked_exercises)

df["onerepmax"] = df.weight / (1.0278 - 0.0278 * df.reps)

# Exclude days where the exercise was done for high volume (and ignore warmups)
dfl = (
    df.sort_values(["date", "exercise", "onerepmax"])
    .drop_duplicates(subset=["date", "exercise"], keep="last")
    .query("reps < 10")
)

# Exclude outliers
dfl = (
    dfl.set_index(["date", "exercise"])
    .drop(
        [
            ("2021-03-08", "Squat"),
            ("2021-03-09", "Bench"),
            ("2021-03-11", "Squat"),
            ("2021-04-01", "Squat"),
            ("2021-04-08", "Squat"),
            ("2021-04-17", "Squat"),
            ("2021-06-04", "Squat"),
            ("2022-04-08", "Overhead"),
            ("2023-05-09", "Bench"),
            ("2023-05-09", "Deadlift"),
            ("2023-05-10", "Squat"),
        ]
    )
    .reset_index()
)


fig = px.line(dfl, x="date", y="onerepmax", color="exercise", markers=True)

left_edge = programs.iloc[0].start
right_edge = dfl.iloc[-1].date + timedelta(days=90)
top_edge = ceil(dfl.onerepmax.max() / 20) * 20 + 40

fig.update_layout(
    xaxis_title="Date",
    yaxis_title="One rep max (kg)",
    legend_title_text="Exercise",
    hovermode="x unified",
    xaxis_range=[left_edge, right_edge],
    yaxis_range=[0, top_edge],
)

for i, program in programs.iterrows():
    if i != 0:
        fig.add_shape(
            type="line",
            x0=program.start,
            x1=program.start,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color="Blue", width=2, dash="dash"),
        )

    xmiddle = (
        program.start
        + ((right_edge if i == len(programs) - 1 else program.end) - program.start) / 2
    )
    months = round(program.duration.days / 30)

    fig.add_annotation(
        x=xmiddle,
        y=0.9,
        yref="paper",
        yanchor="bottom",
        text=program["name"],
        showarrow=False,
        font={"size": 18, "weight": "bold"},
    )

    fig.add_annotation(
        x=xmiddle,
        y=0.9,
        yref="paper",
        yanchor="top",
        text=f"{program.num} workouts<br>{months} months",
        showarrow=False,
        font={"size": 10},
    )


layout = dcc.Graph(figure=fig)
