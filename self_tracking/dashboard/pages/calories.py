import dash
from dash import dcc
import self_tracking.data as d
from plotly_calplot import calplot


dash.register_page(__name__)


def calories_figure():
    net_calories = d.net_calories().rename("net_calories").reset_index()

    return calplot(
        net_calories,
        x="date",
        y="net_calories",
        colorscale="RdBu",
        cmap_min=-1200,
        cmap_max=1200,
    )


layout = dcc.Graph(figure=calories_figure())
