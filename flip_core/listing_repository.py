"""Read-only, paginated view of legacy alerts."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import urlparse

from .money import to_minor


def platform_from(url, source=None):
    source = str(source or "").strip().upper()

    if source in {"FACEBOOK", "FB", "FACEBOOK MARKETPLACE"}:
        return "FACEBOOK"

    if source == "OLX":
        return "OLX"

    host = (urlparse(str(url or "")).hostname or "").lower()

    if host in {"facebook.com", "fb.com"} or (
        host.endswith(".facebook.com")
    ):
        return "FACEBOOK"

    if host == "olx.pl" or host.endswith(".olx.pl"):
        return "OLX"

    return "UNKNOWN"


def parse_json(value):
    try:
        result = json.loads(value or "{}")
        return result if isinstance(result, dict) else {}
    except (ValueError, TypeError):
        return {}


class LegacyListingReader:

    def __init__(self, root):
        root = Path(root)
        self.alerts = root / "alert_history.db"
        self.snapshots = root / "offer_snapshots.db"

    def _open(self, path):
        if not path.is_file():
            raise FileNotFoundError(
                f"Database unavailable: {path.name}"
            )

        db = sqlite3.connect(
            path.resolve().as_uri() + "?mode=ro",
            uri=True,
            timeout=10,
        )
        db.row_factory = sqlite3.Row
        return db

    def _latest(self, keys):
        if not keys or not self.snapshots.is_file():
            return {}

        keys = list(dict.fromkeys(
            key for key in keys if key
        ))

        if not keys:
            return {}

        marks = ",".join("?" for _ in keys)
        result = {}

        with closing(self._open(self.snapshots)) as db:
            rows = db.execute(f"""
                SELECT *
                FROM snapshots
                WHERE offer_key IN ({marks})
                ORDER BY id DESC
            """, keys).fetchall()

        for row in rows:
            if row["offer_key"] not in result:
                result[row["offer_key"]] = dict(row)

        return result

    def _prepare(self, row, snapshot):
        row = dict(row)
        snapshot = snapshot or {}

        details = parse_json(snapshot.get("details_json"))
        valuation = parse_json(snapshot.get("valuation_json"))
        action = parse_json(snapshot.get("action_json"))

        price = row.get("price")
        price_minor = None

        if price is not None:
            try:
                price_minor = to_minor(price)
            except ValueError:
                pass

        source = platform_from(
            row.get("url"),
            details.get("_source"),
        )

        return {
            "id": row["id"],
            "id_type": "legacy_alert_id",
            "offer_key": row.get("offer_key"),
            "platform": source,
            "title": row.get("title"),
            "url": row.get("url"),
            "price_minor": price_minor,
            "currency": "PLN",
            "score": row.get("score"),
            "created_at": row.get("created_at"),
            "source_status": "UNKNOWN",
            "current_analysis": {
                "valuation": valuation,
                "decision": action,
                "snapshot_id": snapshot.get("id"),
            } if snapshot else None,
        }

    def list(self, limit=20, before_id=None, q=""):
        if not 1 <= limit <= 100:
            raise ValueError("Limit poza zakresem")

        where = []
        params = []

        if before_id is not None:
            if type(before_id) is not int or before_id <= 0:
                raise ValueError("Nieprawidlowy kursor")

            where.append("id < ?")
            params.append(before_id)

        q = str(q or "").strip()

        if q:
            escaped = (
                q.replace("\\", "\\\\")
                 .replace("%", "\\%")
                 .replace("_", "\\_")
            )

            where.append(
                "(COALESCE(title,'') LIKE ? ESCAPE '\\' "
                "OR COALESCE(offer_key,'') LIKE ? ESCAPE '\\')"
            )
            params.extend([f"%{escaped}%", f"%{escaped}%"])

        clause = ("WHERE " + " AND ".join(where)) if where else ""

        with closing(self._open(self.alerts)) as db:
            rows = db.execute(f"""
                SELECT *
                FROM alerts
                {clause}
                ORDER BY id DESC
                LIMIT ?
            """, (*params, limit)).fetchall()

        snapshots = self._latest([
            row["offer_key"] for row in rows
        ])

        return [
            self._prepare(
                row,
                snapshots.get(row["offer_key"]),
            )
            for row in rows
        ]

    def get(self, alert_id):
        with closing(self._open(self.alerts)) as db:
            row = db.execute("""
                SELECT *
                FROM alerts
                WHERE id=?
            """, (alert_id,)).fetchone()

        if row is None:
            return None

        snapshots = self._latest([row["offer_key"]])

        return self._prepare(
            row,
            snapshots.get(row["offer_key"]),
        )

    def history(self, alert_id, limit=50):
        listing = self.get(alert_id)

        if listing is None:
            return None

        if not self.snapshots.is_file():
            return []

        key = listing["offer_key"]

        with closing(self._open(self.snapshots)) as db:
            rows = db.execute("""
                SELECT id, created_at, price,
                       valuation_json, action_json
                FROM snapshots
                WHERE offer_key=?
                ORDER BY id DESC
                LIMIT ?
            """, (key, min(max(limit, 1), 100))).fetchall()

        return [{
            "snapshot_id": row["id"],
            "created_at": row["created_at"],
            "price": row["price"],
            "valuation": parse_json(row["valuation_json"]),
            "decision": parse_json(row["action_json"]),
        } for row in rows]
