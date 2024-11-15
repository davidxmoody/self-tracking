import dash
from dash import Input, Output, dcc, html
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import self_tracking.data as d
import dash_mantine_components as dmc

dash.register_page(__name__)


aggregation_periods = {
    "Daily": "D",
    "Weekly": "W-MON",
    "Monthly": "MS",
    "Quarterly": "QS",
    "Yearly": "YS",
}

layout = html.Div(
    [
        dmc.RadioGroup(
            id="exercise-aggregation-period",
            children=[dmc.Radio(k, value=v) for k, v in aggregation_periods.items()],
            value=aggregation_periods["Monthly"],
            label="Aggregation period:",
            size="sm",
        ),
        dcc.Graph(id="exercise-bar-chart", figure={}),
    ]
)


@dash.callback(
    Output("exercise-bar-chart", "figure"),
    [Input("exercise-aggregation-period", "value")],
)
def update_graph(rule: str):
    r = d.running().distance.resample(rule).sum()
    co = d.cycling_outdoor().calories.resample(rule).sum()
    ci = d.cycling_indoor().calories.resample(rule).sum()
    s = (
        d.strength()
        .drop_duplicates("date")
        .set_index("date")
        .title.resample(rule)
        .size()
    )
    c = d.climbing().place.resample(rule).size()

    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        subplot_titles=["Running", "Cycling", "Strength training", "Climbing"],
    )

    fig.add_trace(go.Bar(x=r.index, y=r.values, name="Running"), row=1, col=1)
    fig.update_yaxes(title_text="Miles", row=1, col=1)

    fig.add_trace(
        go.Bar(x=co.index, y=co.values, name="Outdoor"),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Bar(x=ci.index, y=ci.values, name="Indoor"),
        row=2,
        col=1,
    )
    fig.update_yaxes(title_text="Calories", row=2, col=1, tickformat=",.0s")

    fig.add_trace(go.Bar(x=s.index, y=s.values, name="Strength"), row=3, col=1)
    fig.update_yaxes(title_text="Sessions", row=3, col=1)

    fig.add_trace(go.Bar(x=c.index, y=c.values, name="Climbing"), row=4, col=1)
    fig.update_yaxes(title_text="Sessions", row=4, col=1)

    fig.update_layout(barmode="stack", showlegend=False)

    return fig
