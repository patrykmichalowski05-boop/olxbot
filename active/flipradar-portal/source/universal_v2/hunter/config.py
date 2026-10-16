from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .models import Search, integer
from .sources import SourceConfig


@dataclass(frozen=True)
class Config:
    root: Path
    owner_id: str
    database: Path
    sources: list[SourceConfig]
    searches: list[Search]
    interval_seconds: int = 180
    telegram_token_env: str = "TELEGRAM_BOT_TOKEN"
    telegram_chat_env: str = "TELEGRAM_CHAT_ID"

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        path = Path(path).expanduser().resolve()
        if path.stat().st_size > 1_000_000:
            raise ValueError("Plik konfiguracji jest zbyt duży")
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or set(raw) - {
            "owner_id",
            "database",
            "sources",
            "searches",
            "interval_seconds",
            "telegram_token_env",
            "telegram_chat_env",
        }:
            raise ValueError("Nieznane pola konfiguracji")
        owner = raw.get("owner_id")
        if not isinstance(owner, str) or not 1 <= len(owner.strip()) <= 120:
            raise ValueError("Wymagany owner_id właściciela radaru")
        interval = integer(
            raw.get("interval_seconds", 180), "odstęp skanowania", 60, 86400
        )
        envs = [
            raw.get(k, default)
            for k, default in [
                ("telegram_token_env", "TELEGRAM_BOT_TOKEN"),
                ("telegram_chat_env", "TELEGRAM_CHAT_ID"),
            ]
        ]
        if any(
            not isinstance(v, str) or not re.fullmatch(r"[A-Z_][A-Z0-9_]{0,99}", v)
            for v in envs
        ):
            raise ValueError("Nieprawidłowa nazwa zmiennej środowiskowej powiadomień")
        source_rows, search_rows = raw.get("sources", []), raw.get("searches", [])
        if (
            not isinstance(source_rows, list)
            or not isinstance(search_rows, list)
            or len(source_rows) > 5
            or len(search_rows) > 100
        ):
            raise ValueError("Nieprawidłowa liczba źródeł lub wyszukiwań")
        try:
            sources = [SourceConfig(**row) for row in source_rows]
            searches = [Search.from_mapping(row, owner) for row in search_rows]
        except TypeError:
            raise ValueError("Nieprawidłowy obiekt konfiguracji") from None
        if len({s.platform for s in sources}) != len(sources) or len(
            {s.id for s in searches}
        ) != len(searches):
            raise ValueError("Powtórzony identyfikator źródła lub wyszukiwania")
        database = raw.get("database", "runtime/hunter.sqlite3")
        if not isinstance(database, str) or not database.strip():
            raise ValueError("Nieprawidłowa ścieżka bazy")
        db = Path(database).expanduser()
        return cls(
            path.parent,
            owner,
            (db if db.is_absolute() else path.parent / db).resolve(),
            sources,
            searches,
            interval,
            *envs,
        )
