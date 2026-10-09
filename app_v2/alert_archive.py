import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

def db_path():
    return Path(os.getenv(
        "FLIP_ALERT_ARCHIVE_DB",
        str(Path(__file__).resolve().parents[1] / "alert_archive.db")
    )).expanduser().resolve()

def archived_ids():
    path = db_path()
    if not path.exists():
        return set()

    with sqlite3.connect(
        path.as_uri() + "?mode=ro",
        uri=True
    ) as db:
        return {
            row[0] for row in db.execute(
                "SELECT alert_id FROM archived_alerts"
            )
        }

def set_archived(alert_id, archived=True):
    alert_id = int(alert_id)
    if alert_id <= 0:
        raise ValueError("Nieprawidlowy ID")

    path = db_path()
    if not archived and not path.exists():
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS archived_alerts (
                alert_id INTEGER PRIMARY KEY,
                archived_at TEXT NOT NULL
            )
        """)
        if archived:
            db.execute("""
                INSERT OR REPLACE INTO archived_alerts
                VALUES (?, ?)
            """, (
                alert_id,
                datetime.now(timezone.utc).isoformat()
            ))
        else:
            db.execute(
                "DELETE FROM archived_alerts WHERE alert_id=?",
                (alert_id,)
            )

    os.chmod(path, 0o600)
