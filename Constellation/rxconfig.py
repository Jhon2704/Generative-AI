"""
Configuracion principal de Reflex para CONSTELLATION.
"""
import os

import reflex as rx


config = rx.Config(
    app_name="constellation",
    db_url="sqlite:///constellation.db",
    api_url=os.getenv("API_URL", ""),
)
