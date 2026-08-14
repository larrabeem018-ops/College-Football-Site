from dash import Dash, dcc, html, page_container
import dash_bootstrap_components as dbc

app = Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = dbc.Container([
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dcc.Link("Home", href="/", className="nav-link")),
            dbc.NavItem(dcc.Link("Transfers", href="/transfers", className="nav-link")),
            dbc.NavItem(dcc.Link("QB Visuals", href="/qb-visuals", className="nav-link")),
        ],
        brand="🏈 College Football Analytics Hub",
        color="primary",
        dark=True,
        sticky="top",
    ),
    html.Div(page_container, style={"marginTop": "20px"})
], fluid=True)

if __name__ == "__main__":
    app.run(debug=True)

