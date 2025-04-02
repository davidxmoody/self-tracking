import dash
from dash._dash_renderer import _set_react_version
from dash import page_registry, page_container
import dash_mantine_components as dmc

_set_react_version("18.2.0")

app = dash.Dash(__name__, use_pages=True, external_stylesheets=list(dmc.styles.ALL))


app.layout = dmc.MantineProvider(
    dmc.AppShell(
        header={"height": 60},
        padding="sm",
        children=[
            dmc.AppShellHeader(
                dmc.Group(
                    h="100%",
                    mx="lg",
                    gap="lg",
                    children=[
                        dmc.Anchor(
                            page["name"],
                            href=page["path"],
                            size="lg",
                            underline="always",
                        )
                        for page in page_registry.values()
                    ],
                )
            ),
            dmc.AppShellMain(page_container),
        ],
    )
)


if __name__ == "__main__":
    app.run(debug=True)
