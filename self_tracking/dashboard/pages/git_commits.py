import dash
from dash import Input, Output, dcc, html
import plotly.express as px
import plotly.graph_objects as go
from self_tracking.dashboard.components.controls import Select, Checkbox
import self_tracking.data as d
import dash_mantine_components as dmc

dash.register_page(__name__, title="Git Commits")


periods = {
    "Total": "100YS",
    "Yearly": "YS",
    "Quarterly": "QS",
    "Monthly": "MS",
    "Weekly": "W-MON",
    "Daily": "D",
}


layout = html.Div(
    [
        dmc.Group(
            [
                Select("git-commits-period", periods),
                Checkbox("git-commits-limit", "Limit bars"),
            ],
            gap="xl",
            justify="center",
        ),
        html.Div(id="git-commits-chart"),
    ]
)


@dash.callback(
    Output("git-commits-limit", "disabled"),
    Input("git-commits-period", "value"),
)
def update_controls(rule: str):
    return rule not in ("W-MON", "D")


@dash.callback(
    Output("git-commits-chart", "children"),
    [
        Input("git-commits-period", "value"),
        Input("git-commits-limit", "checked"),
    ],
)
def update_graph(rule: str, limit: bool):
    df = d.git_commits()

    if df.empty:
        return html.P("No git commits found.")

    df = df.set_index("datetime")

    # Assign a unique color to each repo
    repos = sorted(df["repo"].unique())
    palette = px.colors.qualitative.Alphabet
    color_map = {repo: palette[i % len(palette)] for i, repo in enumerate(repos)}

    # Pivot: one column per repo with count 1 per commit
    pivot = df.assign(count=1).pivot_table(
        index="datetime", columns="repo", values="count", aggfunc="sum", fill_value=0
    )

    if rule == "100YS":
        totals = pivot.sum()
        totals = totals[totals > 0].sort_values(ascending=False)

        fig = px.pie(
            values=totals.values,
            names=totals.index,
            color=totals.index,
            color_discrete_map=color_map,
        )
        fig.update_traces(
            textposition="inside",
            texttemplate="%{label}<br>%{percent:.1%}<br>%{value}",
            hovertemplate="<b>%{label}</b><br>%{value} commits<extra></extra>",
        )
        fig.update_layout(
            height=500,
            margin={"l": 40, "r": 0, "t": 20, "b": 0},
            showlegend=False,
        )
        return dcc.Graph(figure=fig)

    resampled = pivot.resample(rule, closed="left", label="left").sum().reset_index()
    resampled = resampled.rename(columns={"datetime": "date"})

    if limit and rule in ("W-MON", "D"):
        resampled = resampled.iloc[-100:]

    # Sort repos by total commits (most active at bottom)
    repo_totals = resampled.drop(columns="date").sum().sort_values()
    active_repos = repo_totals[repo_totals > 0].index.tolist()

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
        legend={"x": 1},
        xaxis_title=None,
        yaxis=dict(
            title=None,
            tickmode="array",
            tickvals=list(range(len(active_repos))),
            ticktext=active_repos,
        ),
        legend_title=None,
        margin={"l": 120, "r": 0, "t": 20, "b": 0},
        hovermode="x unified",
    )

    if rule == "D":
        fig.update_xaxes(hoverformat="%a %b %d, %Y")

    return dcc.Graph(figure=fig)
