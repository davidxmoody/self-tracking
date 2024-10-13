import dash
from dash import dcc
import pandas as pd
from typing import cast
import plotly.graph_objects as go
import self_tracking.data as d


dash.register_page(__name__)


def weight_figure():
    df = d.weight().dropna()

    df = cast(pd.DataFrame, df.rolling(7).mean()).dropna().reset_index()

    df["fat_weight"] = df["weight"] * df["fat"]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df.date,
            y=df.fat_weight,
            fill="tozeroy",
            name="Fat",
            line={"color": "#ff7f0e"},
            hovertemplate="%{customdata[0]:.1f}% (%{y:.1f} lb)",
            customdata=df[["fat"]] * 100,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df.date,
            y=df.weight,
            fill="tonexty",
            name="Weight",
            line={"color": "#1f77b4"},
            hovertemplate="%{y:.1f} lb",
        )
    )

    last = df.iloc[-1]

    fig.add_annotation(
        x=last.date,
        y=last.weight + 2,
        text=f"{last.weight:.1f} lb",
        showarrow=True,
        arrowhead=1,
        ax=0,
        ay=-20,
        font=dict(color="blue", size=12),
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Weight (lb)",
        hovermode="x unified",
    )

    return fig


layout = dcc.Graph(figure=weight_figure())
