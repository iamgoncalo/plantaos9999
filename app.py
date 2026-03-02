"""PlantaOS MVP — Entry point.

Initializes the Dash application with Mantine components,
configures the layout, and starts the development server.
"""

from __future__ import annotations

import dash
import dash_mantine_components as dmc
from loguru import logger

from config.settings import settings
from config.theme import MANTINE_THEME
from views.callbacks import register_callbacks
from views.layout import create_layout

# ── App Initialization ────────────────────────
logger.info("Initializing PlantaOS MVP")

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="PlantaOS — Building Intelligence",
    update_title="PlantaOS | Loading...",
)

server = app.server

# ── Layout ────────────────────────────────────
app.layout = dmc.MantineProvider(
    theme=MANTINE_THEME,
    children=[create_layout()],
)

# ── Callbacks ─────────────────────────────────
register_callbacks(app)

# ── Server ────────────────────────────────────
if __name__ == "__main__":
    logger.info(f"Starting PlantaOS on {settings.APP_HOST}:{settings.APP_PORT}")
    app.run(
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        debug=settings.DEBUG,
    )
