import re
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

DB = Path(
    "/opt/olx-bot-ui-dev/data/flip_radar_dev.sqlite3"
)

DEFAULTS = {
    "min_profit_zl": 400,
    "min_roi_pct": 30.0,
    "reserve_zl": 150,
    "hot_profit_zl": 750,
}

FIELDS = tuple(DEFAULTS)


def checked_db(path):
    path = Path(path)

    if path.is_symlink() or not path.is_file():
        raise RuntimeError("Brak bezpiecznej bazy Flip Radar")

    return path


def initialize(path=DB):
    path = checked_db(path)

    with sqlite3.connect(path, timeout=10) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS
            flip_profit_settings (
                id INTEGER PRIMARY KEY CHECK(id=1),
                min_profit_zl INTEGER NOT NULL,
                min_roi_pct REAL NOT NULL,
                reserve_zl INTEGER NOT NULL,
                hot_profit_zl INTEGER NOT NULL,
                updated_utc TEXT NOT NULL
            )
        """)

        db.execute("""
            INSERT OR IGNORE INTO flip_profit_settings (
                id, min_profit_zl, min_roi_pct,
                reserve_zl, hot_profit_zl, updated_utc
            )
            VALUES (1, ?, ?, ?, ?, ?)
        """, (
            DEFAULTS["min_profit_zl"],
            DEFAULTS["min_roi_pct"],
            DEFAULTS["reserve_zl"],
            DEFAULTS["hot_profit_zl"],
            datetime.now(timezone.utc).isoformat(),
        ))


def read_policy(path=DB):
    path = checked_db(path)

    with sqlite3.connect(
        path.resolve().as_uri() + "?mode=ro",
        uri=True
    ) as db:
        db.row_factory = sqlite3.Row

        row = db.execute("""
            SELECT min_profit_zl, min_roi_pct,
                   reserve_zl, hot_profit_zl,
                   updated_utc
            FROM flip_profit_settings
            WHERE id=1
        """).fetchone()

    if row is None:
        raise RuntimeError("Brak konfiguracji opłacalności")

    return dict(row)


def validate(form):
    result = {}

    for key in (
        "min_profit_zl",
        "reserve_zl",
        "hot_profit_zl",
    ):
        raw = str(form.get(key, "")).strip()

        if not re.fullmatch(r"[0-9]{1,7}", raw):
            raise ValueError(
                "Nieprawidłowa kwota: " + key
            )

        value = int(raw)

        if value > 1000000:
            raise ValueError(
                "Kwota przekracza dozwolony zakres"
            )

        result[key] = value

    try:
        roi = Decimal(
            str(form.get("min_roi_pct", "")).strip()
            .replace(",", ".")
        )
    except InvalidOperation:
        raise ValueError("Nieprawidłowe ROI")

    if not roi.is_finite() or not 0 <= roi <= 300:
        raise ValueError(
            "ROI musi być od 0 do 300%"
        )

    result["min_roi_pct"] = float(roi)

    if result["hot_profit_zl"] < result["min_profit_zl"]:
        raise ValueError(
            "Próg HOT nie może być niższy "
            "niż minimalny zysk"
        )

    return result


def save_policy(form, path=DB):
    values = validate(form)
    path = checked_db(path)

    with sqlite3.connect(path, timeout=10) as db:
        db.execute("PRAGMA busy_timeout=10000")

        changed = db.execute("""
            UPDATE flip_profit_settings
            SET min_profit_zl=?,
                min_roi_pct=?,
                reserve_zl=?,
                hot_profit_zl=?,
                updated_utc=?
            WHERE id=1
        """, (
            values["min_profit_zl"],
            values["min_roi_pct"],
            values["reserve_zl"],
            values["hot_profit_zl"],
            datetime.now(timezone.utc).isoformat(),
        ))

        if changed.rowcount != 1:
            raise RuntimeError(
                "Nie zapisano konfiguracji"
            )

    return values
