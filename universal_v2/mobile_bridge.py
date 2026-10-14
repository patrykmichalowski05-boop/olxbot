"""Rozszerzenie istniejącego FastAPI. Nie uruchamia usługi."""

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

    return app
