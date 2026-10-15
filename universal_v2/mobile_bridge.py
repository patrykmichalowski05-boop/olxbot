"""Rozszerzenie istniejącego FastAPI. Nie uruchamia usługi."""

import os
import sqlite3

from fastapi import (
    Depends,
    Header,
    HTTPException,
    Query,
)

from flip_core.mobile_api import create_app as legacy_mobile_app
from flip_core.auth_store import AuthStore

from .bridge_config import BridgeConfig
from .integration_status import catalog
from .radar_service import RadarService


def create_app():
    cfg = BridgeConfig.from_env()
    app = legacy_mobile_app()
    auth = AuthStore(cfg.auth_db)
    app.state.hunter = None
    hunter_path = os.getenv('FLIP_HUNTER_DB')
    if hunter_path:
        if os.getenv('FLIPRADAR_READ_LEGACY_SNAPSHOTS') == '1':
            raise RuntimeError('Wybierz jedno źródło radaru: FLIP_HUNTER_DB albo snapshoty starego skanera')
        from pathlib import Path
        from .hunter.store import Store
        if not Path(hunter_path).is_absolute():
            raise RuntimeError('FLIP_HUNTER_DB musi być ścieżką absolutną')
        app.state.hunter = Store(hunter_path)

    def current_user(
        authorization: str | None = Header(default=None)
    ):
        parts = (authorization or '').split(' ', 1)

        if (
            len(parts) != 2
            or parts[0].lower() != 'bearer'
        ):
            raise HTTPException(
                status_code=401,
                detail='Unauthorized'
            )

        try:
            return auth.verify_access(parts[1])

        except (ValueError, sqlite3.Error):
            raise HTTPException(
                status_code=401,
                detail='Unauthorized'
            ) from None

    @app.get('/api/v1/universal/status')
    def status(
        user_id: str = Depends(current_user)
    ):
        if app.state.hunter is not None:
            health = app.state.hunter.health(user_id)
            return {
                'user_id': user_id,
                'mode': 'UNIVERSAL_HUNTER',
                'automatic_sources': len({row['platform'] for row in health if row['status'] == 'OK' and row['source_mode'] in {'html', 'browser'}}),
                'platforms': [{'name': row['platform'], 'status': row['status'], 'search_id': row['search_id'], 'mode': row['source_mode']} for row in health],
                'manual_analysis_enabled': cfg.manual_enabled,
            }
        return {
            'user_id': user_id,
            'mode': 'ISOLATED_DEVELOPMENT',
            'automatic_sources': 0,
            'platforms': [
                {
                    'name': item.platform,
                    'status': item.state
                }
                for item in catalog()
            ],
            'manual_analysis_enabled': cfg.manual_enabled,
        }

    @app.get('/api/v1/universal/radar')
    def radar(
        q: str = Query(
            default='',
            max_length=120
        ),
        limit: int = Query(
            default=20,
            ge=1,
            le=100
        ),
        before_id: int | None = Query(
            default=None,
            gt=0
        ),
        user_id: str = Depends(current_user),
    ):
        db = cfg.dev_dir / 'observations.sqlite'

        if not db.is_file():
            return {
                'items': [],
                'next_before_id': None
            }

        try:
            return RadarService(db).page(
                user_id,
                query=q,
                limit=limit,
                before_id=before_id
            )

        except (sqlite3.Error, OSError):
            raise HTTPException(
                503,
                'Test database unavailable'
            ) from None

    from .manual_routes import attach_manual
    attach_manual(app, cfg, current_user)

    from .watch_routes import attach_watch
    attach_watch(app, cfg, current_user)

    from .mobile_radar_routes import attach
    attach(app, cfg, current_user)

    if app.state.hunter is not None:
        from .hunter.api import attach as attach_hunter
        attach_hunter(app, app.state.hunter, current_user)

    return app
