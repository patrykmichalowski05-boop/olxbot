"""WSGI factory for the existing server. Defaults to a read-only staging UI."""
from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys

from runtime_check import HERE, REPO, inspect_runtime


def create_app():
    mode = os.getenv('FLIPRADAR_GUI_MODE', 'stage')
    if mode not in ('stage', 'live'):
        raise RuntimeError('FLIPRADAR_GUI_MODE musi mieć wartość stage albo live')
    bot = Path(os.getenv('OLX_BOT_DIR', str(REPO))).resolve()
    overlay = Path(os.getenv('FLIPRADAR_OVERLAY_DIR', '/opt/olx-bot-budget-dev')).resolve()
    dist = Path(os.getenv('FLIPRADAR_V12_DIST', str(HERE / 'dist'))).resolve()
    status = inspect_runtime(bot, overlay, dist)
    if not status['ready']:
        details = ', '.join(status['missing_modules']) or 'niepełny eksport lub błędna składnia'
        raise RuntimeError('Brak wymaganej części istniejącej instalacji: ' + details + '. Uruchom runtime_check.py dla właściwych katalogów.')
    for path in (bot, overlay, HERE):
        sys.path.insert(0, str(path))
    os.environ['OLX_BOT_DIR'] = str(bot)
    os.environ['FLIPRADAR_V12_DIST'] = str(dist)
    app = importlib.import_module('flip_v2_overlay_dev').app
    from v12_bridge import install
    install(app, preview=mode == 'stage')
    return app
