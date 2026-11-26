import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full", app_title="Food meals")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import plotly.graph_objects as go

    import self_tracking.analysis.food_meals as fm

    return fm, go, mo, pd


@app.cell
def _(mo):
    mo.md("""
    # Food meals

    Logged food names are grouped into broad ingredients (items), and each
    logged meal's set of items is matched to a recurring meal type. Rules are
    in `self_tracking/analysis/food_meals.py`. Values are the % of days in each
    period that had the item or meal type at least once.
    """)
    return


@app.cell
def _(fm):
    foods = fm.foods()
    meals = fm.meals(foods)
    return foods, meals


@app.cell
def _(mo):
    period = mo.ui.dropdown(
        {"Quarter": "Q", "Half-year": "6M", "Year": "Y"},
        value="Half-year",
        label="Period",
    )
    period
    return (period,)


@app.cell
def _(pd, period):
    def period_start(dates: pd.Series) -> pd.Series:
        freq = period.value
        if freq == "6M":
            return pd.to_datetime(
                dates.dt.year.astype(str) + "-" + (1 + 6 * (dates.dt.month > 6)).astype(str) + "-01"
            )
        return dates.dt.to_period(freq).dt.start_time

    def pct_of_days(df: pd.DataFrame, column: str) -> pd.DataFrame:
        """% of days in each period that had each value of ``column``."""
        starts = period_start(df.date)
        days = df.date.groupby(starts).nunique()
        counts = df.date.groupby([df[column], starts]).nunique().unstack(fill_value=0)
        return counts.div(days, axis=1).mul(100).round()

    return (pct_of_days,)


@app.cell
def _(go):
    def heatmap(table, title):
        labels = [f"{c:%Y}" + (f" {c:%b}" if c.month != 1 or len(table.columns) > 8 else "") for c in table.columns]
        fig = go.Figure(
            go.Heatmap(
                z=table.values,
                x=labels,
                y=table.index,
                colorscale="Blues",
                zmin=0,
                text=table.values.astype(int),
                texttemplate="%{text}",
                hovertemplate="%{y}<br>%{x}: %{z:.0f}% of days<extra></extra>",
                colorbar=dict(title="% days"),
            )
        )
        fig.update_layout(
            title=title,
            height=max(300, 24 * len(table) + 120),
            yaxis=dict(autorange="reversed"),
            margin=dict(l=10, r=10, t=50, b=10),
        )
        return fig

    return (heatmap,)


@app.cell
def _(fm, heatmap, meals, mo, pct_of_days):
    _table = pct_of_days(meals.dropna(subset=["meal_type"]), "meal_type")
    _order = [name for name, _, _ in fm.MEAL_RULES]
    _breakfast = _table.reindex([m for m in _order if m in fm.BREAKFASTS]).fillna(0)
    _main = _table.reindex([m for m in _order if m not in fm.BREAKFASTS]).fillna(0)
    _unmatched = meals[meals.meal != "snacks"].meal_type.isna().mean()
    mo.vstack(
        [
            heatmap(_breakfast, "Breakfast-type meals"),
            heatmap(_main, "Lunch/dinner-type meals"),
            mo.md(f"_{_unmatched:.0%} of non-snack meals match no meal type._"),
        ]
    )
    return


@app.cell
def _(foods, heatmap, pct_of_days):
    _table = pct_of_days(foods, "item")
    _table = _table[_table.max(axis=1) >= 10]
    heatmap(_table.loc[_table.mean(axis=1).sort_values(ascending=False).index], "Items")
    return


@app.cell
def _(fm, mo):
    meal_type = mo.ui.dropdown(
        [name for name, _, _ in fm.MEAL_RULES], value="Protein pancakes", label="Meal type"
    )
    meal_type
    return (meal_type,)


@app.cell
def _(heatmap, meal_type, meals, mo, pd):
    _df = meals[meals.meal_type == meal_type.value]
    _year = _df.date.dt.year
    _n = _year.value_counts().sort_index()
    _exploded = _df.assign(year=_year).explode("items")
    _table = _exploded.groupby(["items", "year"]).size().unstack(fill_value=0).div(_n, axis=1).mul(100).round()
    _table = _table[_table.max(axis=1) >= 15]
    _table = _table.loc[_table.mean(axis=1).sort_values(ascending=False).index]
    _table.columns = pd.to_datetime(_table.columns.astype(str))
    _fig = heatmap(_table, f"{meal_type.value}: % of these meals containing each item, by year")
    _fig.data[0].hovertemplate = "%{y}<br>%{x}: in %{z:.0f}% of meals<extra></extra>"
    mo.vstack([mo.md(" · ".join(f"{y}: {c} meals" for y, c in _n.items())), _fig])
    return


@app.cell
def _(foods, mo):
    _other = foods[foods.item == "other"].desc.value_counts()
    mo.vstack(
        [
            mo.md(f"### Unmapped foods\n{len(_other)} names, {_other.sum()} entries map to no item."),
            _other.rename("entries").head(50).to_frame(),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
