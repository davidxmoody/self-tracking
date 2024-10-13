import dash
from dash import html, dcc

app = dash.Dash(__name__, use_pages=True)


app.layout = html.Div(
    [
        html.Div(
            [
                html.Div(dcc.Link(page["name"], href=page["relative_path"]))
                for page in dash.page_registry.values()
            ]
        ),
        dash.page_container,
    ]
)


if __name__ == "__main__":
    app.run_server(debug=True)
