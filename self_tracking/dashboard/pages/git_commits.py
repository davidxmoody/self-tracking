import dash
from dash import dcc, html
import plotly.express as px
import plotly.graph_objects as go
import self_tracking.data as d

dash.register_page(__name__, title="Git Commits")


layout = html.Div(id="git-commits-chart")


@dash.callback(
    dash.Output("git-commits-chart", "children"),
    dash.Input("git-commits-chart", "id"),
)
def update_graph(_):
    df = d.git_commits()

    if df.empty:
        return html.P("No git commits found.")

    df = df.set_index("datetime")

    # Pivot: one column per repo with count 1 per commit
    pivot = df.assign(count=1).pivot_table(
        index="datetime", columns="repo", values="count", aggfunc="sum", fill_value=0
    )

    # Group repos with <50 total commits into "other"
    repo_commit_totals = pivot.sum()
    minor_repos = repo_commit_totals[repo_commit_totals < 50].index.tolist()
    if minor_repos:
        pivot["other"] = pivot[minor_repos].sum(axis=1)
        pivot = pivot.drop(columns=minor_repos)

    # Assign a unique color to each series
    series = sorted(c for c in pivot.columns if c != "other")
    palette = px.colors.qualitative.Alphabet
    color_map = {s: palette[i % len(palette)] for i, s in enumerate(series)}
    if "other" in pivot.columns:
        color_map["other"] = "#999999"

    resampled = pivot.resample("MS", closed="left", label="left").sum().reset_index()
    resampled = resampled.rename(columns={"datetime": "date"})

    # Sort repos by total commits (most active at bottom), with "other" first (bottom)
    repo_totals = resampled.drop(columns="date").sum().sort_values()
    active_repos = repo_totals[repo_totals > 0].index.tolist()
    if "other" in active_repos:
        active_repos.remove("other")
        active_repos.insert(0, "other")

    # Normalize each repo's values to [0, 1] for consistent ridge heights
    max_val = resampled[active_repos].max().max()
    if max_val == 0:
        max_val = 1

    fig = go.Figure()

    for i, repo in enumerate(active_repos):
        y_values = resampled[repo] / max_val
        # Baseline trace (invisible, defines the bottom of the fill)
        fig.add_trace(
            go.Scatter(
                x=resampled["date"],
                y=[i] * len(resampled),
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
            )
        )
        # Ridge trace (fills down to baseline)
        fig.add_trace(
            go.Scatter(
                x=resampled["date"],
                y=y_values + i,
                fill="tonexty",
                mode="lines",
                line={"color": color_map[repo], "width": 0.5},
                fillcolor=color_map[repo],
                name=repo,
                customdata=resampled[repo],
                hovertemplate="<b>%{customdata}</b> commits<extra>%{fullData.name}</extra>",
            )
        )

    fig.update_layout(
        height=max(400, len(active_repos) * 60 + 80),
        showlegend=False,
        xaxis_title=None,
        yaxis=dict(
            title=None,
            tickmode="array",
            tickvals=list(range(len(active_repos))),
            ticktext=active_repos,
        ),
        margin={"l": 120, "r": 0, "t": 20, "b": 0},
        hovermode="x unified",
    )

    return dcc.Graph(figure=fig)
