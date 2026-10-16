"""Separate localhost-only instance of the ORIGINAL React UI and existing Flask backend."""
from flip_v2_overlay_dev import app
from v12_bridge import install
install(app, preview=True)
