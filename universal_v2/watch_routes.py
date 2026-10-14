from fastapi import Depends, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .watchlist_v2 import Watchlist


class WatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(
        min_length=1,
        max_length=240
    )
    label: str = Field(
        min_length=1,
        max_length=240
    )

    @field_validator('key', 'label')
    @classmethod
    def strip_nonempty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('Puste pole watchlisty')
        return cleaned


class CloseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(
        min_length=1,
        max_length=240
    )

    @field_validator('key')
    @classmethod
    def strip_nonempty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('Pusty identyfikator')
        return cleaned


def attach_watch(app, cfg, current_user):

    def repo():
        db = Watchlist(
            cfg.dev_dir / 'watchlist.sqlite'
        )
        db.init()
        return db

    @app.get('/api/v1/universal/watchlist')
    def get_watchlist(
        limit: int = Query(
            default=30,
            ge=1,
            le=100
        ),
        user_id: str = Depends(current_user)
    ):
        return {
            'items': repo().get(
                user_id,
                limit
            )
        }

    @app.post('/api/v1/universal/watchlist')
    def put_watchlist(
        data: WatchRequest,
        user_id: str = Depends(current_user)
    ):
        repo().put(
            user_id,
            data.key,
            data.label
        )

        return {'ok': True}

    @app.post('/api/v1/universal/watchlist/close')
    def close_watchlist(
        data: CloseRequest,
        user_id: str = Depends(current_user)
    ):
        return {
            'closed': repo().close(
                user_id,
                data.key
            )
        }
