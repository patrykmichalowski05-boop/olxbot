"""Opt-in additions to the existing authenticated Expo API."""

from __future__ import annotations

import sqlite3

from fastapi import Depends, HTTPException, Path

from .models import Search


def attach(app, store, current_user):
    @app.get("/api/v1/universal/searches")
    def searches(user_id: str = Depends(current_user)):
        return {"items": [search.payload() for search in store.searches(user_id)]}

    @app.put("/api/v1/universal/searches/{search_id}")
    def put_search(
        data: dict,
        search_id: str = Path(min_length=1, max_length=80),
        user_id: str = Depends(current_user),
    ):
        try:
            if data.get("id", search_id) != search_id:
                raise ValueError(
                    "Identyfikator wyszukiwania musi zgadzać się z adresem"
                )
            if data.get("owner_id", user_id) != user_id:
                raise HTTPException(403, "Nie możesz zmieniać wyszukiwań innego konta")
            profiles = store.searches(user_id)
            if len(profiles) >= 100 and search_id not in {s.id for s in profiles}:
                raise HTTPException(409, "Osiągnięto limit zapisanych wyszukiwań")
            search = Search.from_mapping({**data, "id": search_id}, user_id)
            store.save_search(search)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        except sqlite3.Error:
            raise HTTPException(
                503, "Nie udało się zapisać wyszukiwania. Spróbuj ponownie."
            ) from None
        return search.payload()

    @app.delete("/api/v1/universal/searches/{search_id}")
    def delete_search(
        search_id: str = Path(min_length=1, max_length=80),
        user_id: str = Depends(current_user),
    ):
        if not store.delete_search(user_id, search_id):
            raise HTTPException(404, "Nie znaleziono wyszukiwania")
        return {"deleted": True}

    @app.get("/api/v1/universal/source-health")
    def source_health(user_id: str = Depends(current_user)):
        return {
            "items": store.health(user_id),
            "notifications": store.queue_summary(user_id),
        }
