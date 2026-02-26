import dash
from dash import Input, Output, dcc, html
import plotly.express as px
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

    long = resampled.melt(id_vars="date", var_name="repo", value_name="commits")
    long = long.loc[long.commits > 0]

    fig = px.bar(
        long,
        x="date",
        y="commits",
        color="repo",
        color_discrete_map=color_map,
        custom_data=["repo", "commits"],
    )
    fig.update_traces(
        hovertemplate="<b>%{customdata[1]}</b> %{customdata[0]}<extra></extra>"
    )
    fig.update_layout(
        height=500,
        legend={"traceorder": "reversed", "x": 1},
        xaxis_title=None,
        yaxis_title=None,
        legend_title=None,
        margin={"l": 40, "r": 0, "t": 20, "b": 0},
        hovermode="x unified",
    )

    if rule == "D":
        fig.update_xaxes(hoverformat="%a %b %d, %Y")

    return dcc.Graph(figure=fig)
