"""Kontrakt radaru dla istniejącego klienta Expo."""

import os
import sqlite3

from fastapi import Depends, HTTPException, Path as ApiPath, Query
from .radar_service import RadarService
from .legacy_snapshot_mobile import page as legacy_page, get_snapshot as legacy_get


def normalize(page):
    result = []

    for item in page['items']:
        result.append({
            'snapshot_id': item['id'],
            'title': item['title'],
            'platform': item['source'],
            'decision': item['decision'],
            'valuation': item['analysis'],
            'observed_at': item.get('observed_at'),
            'price_minor': item.get('price_minor'),
            'url': item.get('url'),
        })

    return {
        'items': result,
        'next_before_id': page['next_before_id']
    }


def attach(app, cfg, current_user):

    @app.get('/api/v1/universal/mobile-radar')
    def mobile_radar(
        q: str = Query(default='', max_length=120),
        limit: int = Query(default=20, ge=1, le=100),
        before_id: int | None = Query(default=None, gt=0),
        user_id: str = Depends(current_user),
    ):
        hunter = getattr(app.state, 'hunter', None)
        if hunter is not None:
            try:
                return hunter.radar(user_id, query=q, limit=limit, before_id=before_id)
            except (sqlite3.Error, OSError):
                raise HTTPException(503, 'Nie udało się pobrać ofert. Spróbuj ponownie.') from None
        if os.getenv('FLIPRADAR_READ_LEGACY_SNAPSHOTS') == '1':
            if user_id != os.getenv('FLIPRADAR_LEGACY_OWNER_ID'):
                raise HTTPException(403, 'Snapshot access forbidden')
            try:
                return legacy_page(
                    limit=limit, before_id=before_id, q=q
                )
            except (sqlite3.Error, OSError, ValueError):
                raise HTTPException(
                    503, 'Snapshot radar unavailable'
                ) from None

        path = cfg.dev_dir / 'observations.sqlite'

        if not path.is_file():
            return {
                'items': [],
                'next_before_id': None
            }

        try:
            page = RadarService(path).page(
                user_id,
                query=q,
                limit=limit,
                before_id=before_id,
            )
            return normalize(page)

        except (sqlite3.Error, OSError):
            raise HTTPException(
                503, 'Development radar unavailable'
            ) from None


    @app.get('/api/v1/universal/mobile-radar/{snapshot_id}')
    def mobile_radar_detail(
        snapshot_id: int = ApiPath(gt=0),
        user_id: str = Depends(current_user),
    ):
        hunter = getattr(app.state, 'hunter', None)
        if hunter is not None:
            try:
                item = hunter.detail(user_id, snapshot_id)
            except (sqlite3.Error, OSError):
                raise HTTPException(503, 'Nie udało się pobrać oferty. Spróbuj ponownie.') from None
            if item is None:
                raise HTTPException(404, 'Nie znaleziono oferty')
            return item
        if os.getenv('FLIPRADAR_READ_LEGACY_SNAPSHOTS') != '1':
            raise HTTPException(404, 'Snapshot not found')

        if user_id != os.getenv('FLIPRADAR_LEGACY_OWNER_ID'):
            raise HTTPException(403, 'Snapshot access forbidden')

        try:
            item = legacy_get(snapshot_id)
        except (sqlite3.Error, OSError, ValueError):
            raise HTTPException(
                503, 'Snapshot unavailable'
            ) from None

        if item is None:
            raise HTTPException(404, 'Snapshot not found')

        return item
