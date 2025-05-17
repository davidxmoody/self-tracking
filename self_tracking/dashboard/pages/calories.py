import dash
from dash import dcc
import self_tracking.data as d
import plotly.express as px


dash.register_page(__name__)


def calories_figure():
    return px.bar(d.activity().active_calories.resample("MS").mean())


layout = dcc.Graph(figure=calories_figure())
