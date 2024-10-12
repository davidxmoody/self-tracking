import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import numpy as np
from self_tracking.dashboard.calories import calories_figure

from self_tracking.dashboard.weight import weight_figure

app = dash.Dash(__name__)

df = pd.DataFrame(
    {
        "date": pd.date_range(start="2022-01-01", periods=365, freq="D"),
        "value1": np.random.randint(0, 100, 365),
        "value2": np.random.randint(0, 200, 365),
        "value3": np.random.randint(0, 150, 365),
    }
)


def aggregate_data(df, period):
    if period == "Yearly":
        df["date"] = df["date"].dt.to_period("Y").dt.start_time
    elif period == "Monthly":
        df["date"] = df["date"].dt.to_period("M").dt.start_time
    elif period == "Daily":
        df["date"] = df["date"].dt.to_period("D").dt.start_time
    return df.groupby("date").sum().reset_index()


app.layout = html.Div(
    [
        dcc.Tabs(
            [
                dcc.Tab(
                    label="Overview",
                    children=[
                        html.Div(
                            [
                                html.Label("Select Time Aggregation:"),
                                dcc.Dropdown(
                                    id="time-aggregation-dropdown",
                                    options=[
                                        {"label": "Yearly", "value": "Yearly"},
                                        {"label": "Monthly", "value": "Monthly"},
                                        {"label": "Daily", "value": "Daily"},
                                    ],
                                    value="Daily",
                                ),
                                dcc.Graph(id="bar-graph1"),
                                dcc.Graph(id="bar-graph2"),
                                dcc.Graph(id="bar-graph3"),
                            ]
                        )
                    ],
                ),
                dcc.Tab(
                    label="Weight",
                    children=[dcc.Graph(figure=weight_figure())],
                ),
                dcc.Tab(
                    label="Calories",
                    children=[dcc.Graph(figure=calories_figure())],
                ),
                dcc.Tab(
                    label="Tab 4",
                    children=[html.Div("Tab 4 content goes here.")],
                ),
                dcc.Tab(
                    label="Tab 5",
                    children=[html.Div("Tab 5 content goes here.")],
                ),
            ]
        )
    ]
)


@app.callback(
    [
        Output("bar-graph1", "figure"),
        Output("bar-graph2", "figure"),
        Output("bar-graph3", "figure"),
    ],
    Input("time-aggregation-dropdown", "value"),
)
def update_graphs(period):
    aggregated_df = aggregate_data(df.copy(), period)

    fig1 = px.bar(aggregated_df, x="date", y="value1", title="Graph 1: Value 1")
    fig2 = px.bar(aggregated_df, x="date", y="value2", title="Graph 2: Value 2")
    fig3 = px.bar(aggregated_df, x="date", y="value3", title="Graph 3: Value 3")

    fig1.update_layout(xaxis=dict(matches="x"))
    fig2.update_layout(xaxis=dict(matches="x"))
    fig3.update_layout(xaxis=dict(matches="x"))

    return fig1, fig2, fig3


if __name__ == "__main__":
    app.run_server(debug=True)
