"""Wspolna konfiguracja skanerow Flip Hunter V2."""

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

LOG = logging.getLogger(__name__)

DEFAULTS = {
    "min_profit": 400,
    "hot_profit": 700,
    "ai_min_profit": 300,
    "final_min_profit": 400,
    "facebook_min_profit": 400,
    "min_ram_gb": 16,
    "max_purchase_price": 0,
}


def database_path():
    override = os.getenv("FLIP_SETTINGS_DB")
    if override:
        return Path(override).expanduser().resolve()

    root = Path(
        os.getenv("OLX_BOT_DIR")
        or Path(__file__).resolve().parent
    )
    return root.resolve() / "flip_settings.db"


def _read_connection():
    path = database_path()
    return sqlite3.connect(
        f"file:{path.as_posix()}?mode=ro",
        uri=True,
        timeout=3,
    )


def get_all():
    """Odczyt bez tworzenia bazy; brak bazy = ustawienia domyslne."""
    values = DEFAULTS.copy()

    if not database_path().is_file():
        return values

    try:
        with _read_connection() as db:
            rows = db.execute(
                "SELECT key, value FROM settings"
            ).fetchall()

        for key, value in rows:
            if key in DEFAULTS:
                values[key] = int(value)

    except (sqlite3.Error, ValueError, OSError) as exc:
        LOG.warning("Nie mozna odczytac ustawien: %s", exc)

    return values


def get_int(key):
    if key not in DEFAULTS:
        raise KeyError(f"Nieznane ustawienie: {key}")
    return get_all()[key]


def save_settings(values, actor="admin"):
    """Atomowy zapis ustawien wraz z historia zmian."""
    cleaned = {}

    for key in DEFAULTS:
        raw = values.get(key)

        try:
            if raw is None:
                raise ValueError()
            number = int(str(raw).strip())
        except (ValueError, TypeError):
            raise ValueError(f"Nieprawidlowa wartosc: {key}")

        if key == "min_ram_gb":
            minimum, maximum, unit = 8, 256, "GB"
        elif key == "max_purchase_price":
            minimum, maximum, unit = 0, 100000, "zl"
        else:
            minimum, maximum, unit = 0, 10000, "zl"

        if not minimum <= number <= maximum:
            raise ValueError(
                f"{key}: dozwolony zakres "
                f"{minimum}-{maximum} {unit}"
            )

        cleaned[key] = number

    if cleaned["hot_profit"] < cleaned["min_profit"]:
        raise ValueError(
            "Prog HOT nie moze byc nizszy od minimalnego zysku"
        )

    if cleaned["final_min_profit"] < cleaned["ai_min_profit"]:
        raise ValueError(
            "Prog finalny nie moze byc nizszy od progu AI"
        )

    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    existed = path.exists()
    changes = 0

    try:
        with sqlite3.connect(path, timeout=5) as db:
            db.execute("PRAGMA busy_timeout=5000")
            db.execute("BEGIN IMMEDIATE")

            db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                )
            """)

            db.execute("""
                CREATE TABLE IF NOT EXISTS settings_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    changed_at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    key TEXT NOT NULL,
                    old_value INTEGER NOT NULL,
                    new_value INTEGER NOT NULL
                )
            """)

            existing = dict(
                db.execute("SELECT key, value FROM settings")
            )

            timestamp = datetime.now(
                timezone.utc
            ).isoformat(timespec="seconds")

            for key, new_value in cleaned.items():
                old_value = int(
                    existing.get(key, DEFAULTS[key])
                )

                if old_value == new_value:
                    continue

                db.execute(
                    """
                    INSERT INTO settings (key, value)
                    VALUES (?, ?)
                    ON CONFLICT(key)
                    DO UPDATE SET value=excluded.value
                    """,
                    (key, new_value),
                )

                db.execute(
                    """
                    INSERT INTO settings_history
                    (changed_at, actor, key, old_value, new_value)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        str(actor)[:100],
                        key,
                        old_value,
                        new_value,
                    ),
                )
                changes += 1
    finally:
        if not existed and path.is_file():
            os.chmod(path, 0o600)

    return changes


def get_history(limit=30):
    if not database_path().is_file():
        return []

    try:
        with _read_connection() as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                """
                SELECT changed_at, actor, key,
                       old_value, new_value
                FROM settings_history
                ORDER BY id DESC LIMIT ?
                """,
                (max(1, min(int(limit), 100)),),
            ).fetchall()
            return [dict(row) for row in rows]

    except (sqlite3.Error, OSError) as exc:
        LOG.warning("Nie mozna odczytac historii: %s", exc)
        return []
