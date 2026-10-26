"""
Punto de entrada de CONSTELLATION.
on_load en /index ejecuta dos handlers en orden:
  1. AuthState.restore_session → restaura/verifica sesión
  2. AppState.on_load          → carga datos (lee auth ya restaurado)
  3. GraphState.load_graph     → carga nodos del grafo
"""
import reflex as rx
from .pages.auth import auth
from .pages.index import index
from .state.auth_state import AuthState
from .state.app_state import AppState
from .state.graph_state import GraphState

app = rx.App(
    style={
        "font_family": "Barlow, sans-serif",
        "background_color": "#0a0a0a",
        "color": "#e5e5e5",
    },
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;900&family=Barlow:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap",
    ],
)

# Los on_load se ejecutan en orden: primero restore_session, luego on_load
app.add_page(
    index,
    route="/",
    title="Constellation",
    on_load=[AuthState.restore_session, AppState.on_load, GraphState.load_graph],
)

app.add_page(auth, route="/auth", title="Constellation")
