import dash
from dash import dcc
import self_tracking.data as d
import plotly.express as px


dash.register_page(__name__)


def calories_figure():
    net_calories = d.net_calories().rename("net_calories")

    return px.bar(net_calories.resample("MS").sum())


layout = dcc.Graph(figure=calories_figure())
