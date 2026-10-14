"""Kontrakt radaru dla istniejącego klienta Expo."""

import sqlite3

from fastapi import Depends, HTTPException, Query
from .radar_service import RadarService


def normalize(page):
    result = []

    for item in page['items']:
        result.append({
            'snapshot_id': item['id'],
            'title': item['title'],
            'platform': item['source'],
            'decision': item['decision'],
            'valuation': item['analysis'],
            'observed_at': None,
            'price_minor': None,
            'url': None,
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
