import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full", app_title="One Rep Maxes")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import plotly.express as px
    from datetime import timedelta
    from math import ceil

    import self_tracking.data as d

    return ceil, d, mo, pd, px, timedelta


@app.cell
def _(mo):
    mo.md("""
    # One rep maxes

    Estimated one rep max (Brzycki formula) from the heaviest set of each tracked lift per day.
    """)
    return


@app.cell
def _(d, pd):
    # Load raw data. Nothing else in the notebook re-runs this cell unless
    # `d` changes, so the TSV files are only read once per session.
    df = d.strength_exercises()
    df["date"] = pd.to_datetime(df.start.dt.date)

    workout_dates = df.date.unique()
    programs = d.strength_programs()
    programs["num"] = programs.apply(
        lambda row: sum(1 for w in workout_dates if row.start <= w <= row.end),
        axis=1,
    )
    return df, programs


@app.cell
def _(df):
    tracked_exercises = {
        "Deadlift (Barbell)": "Deadlift",
        "Squat (Barbell)": "Squat",
        "Bench Press (Barbell)": "Bench",
        "Overhead Press (Barbell)": "Overhead",
    }

    # Underscore-prefixed names are private to this cell, so they don't
    # clash with `df` from the cell above (marimo forbids redefining a name
    # in two cells).
    _lifts = df.loc[
        df.exercise.isin(tracked_exercises), ["date", "exercise", "weight", "reps"]
    ].copy()
    _lifts["exercise"] = _lifts.exercise.map(tracked_exercises)
    _lifts["onerepmax"] = _lifts.weight / (1.0278 - 0.0278 * _lifts.reps)

    # Keep only the best set per day per exercise, ignoring high volume days
    _best = (
        _lifts.sort_values(["date", "exercise", "onerepmax"])
        .drop_duplicates(subset=["date", "exercise"], keep="last")
        .query("reps < 10")
    )

    outliers = [
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
    onerepmaxes = (
        _best.set_index(["date", "exercise"]).drop(outliers).reset_index()
    )
    return onerepmaxes, tracked_exercises


@app.cell
def _(mo, tracked_exercises):
    # UI elements. Their values are read in *other* cells; when you interact
    # with one, marimo re-runs every cell that references it.
    exercise_picker = mo.ui.multiselect(
        options=list(tracked_exercises.values()),
        value=list(tracked_exercises.values()),
        label="Exercises",
    )
    show_programs = mo.ui.switch(value=True, label="Show programs")
    mo.hstack([exercise_picker, show_programs], justify="start", gap=2)
    return exercise_picker, show_programs


@app.cell
def _(
    ceil,
    exercise_picker,
    mo,
    onerepmaxes,
    programs,
    px,
    show_programs,
    timedelta,
):
    _data = onerepmaxes[onerepmaxes.exercise.isin(exercise_picker.value)]
    mo.stop(_data.empty, mo.md("_Select at least one exercise._"))

    fig = px.line(_data, x="date", y="onerepmax", color="exercise", markers=True)

    _left = programs.iloc[0].start
    _right = onerepmaxes.date.max() + timedelta(days=90)
    _top = ceil(_data.onerepmax.max() / 20) * 20 + 40

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="One rep max (kg)",
        legend_title_text="Exercise",
        hovermode="x unified",
        xaxis_range=[_left, _right],
        yaxis_range=[0, _top],
        height=600,
    )

    if show_programs.value:
        for _i, _p in programs.iterrows():
            if _i != 0:
                fig.add_vline(
                    x=_p.start, line=dict(color="Blue", width=2, dash="dash")
                )
            _end = _right if _i == len(programs) - 1 else _p.end
            _mid = _p.start + (_end - _p.start) / 2
            _months = round(_p.duration.days / 30)
            fig.add_annotation(
                x=_mid, y=0.9, yref="paper", yanchor="bottom", showarrow=False,
                text=_p["name"], font={"size": 18, "weight": "bold"},
            )
            fig.add_annotation(
                x=_mid, y=0.9, yref="paper", yanchor="top", showarrow=False,
                text=f"{_p.num} workouts<br>{_months} months", font={"size": 10},
            )

    fig
    return


@app.cell
def _(exercise_picker, onerepmaxes):
    # Summary table: best ever and most recent estimate per exercise
    _sel = onerepmaxes[onerepmaxes.exercise.isin(exercise_picker.value)]
    summary = _sel.groupby("exercise").agg(
        best=("onerepmax", "max"),
        latest=("onerepmax", "last"),
        latest_date=("date", "last"),
        sessions=("date", "count"),
    ).round(1)
    summary
    return


if __name__ == "__main__":
    app.run()
