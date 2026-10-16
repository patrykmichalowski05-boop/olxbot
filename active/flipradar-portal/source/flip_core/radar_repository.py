"""Read-only radar based on latest saved snapshots."""

import sqlite3

from contextlib import closing
from pathlib import Path

from .listing_repository import parse_json, platform_from
from .money import to_minor


class SnapshotRadar:

    def __init__(self, root):
        self.path = Path(root) / "offer_snapshots.db"

    def list(
        self,
        *,
        limit=20,
        before_id=None,
        q="",
    ):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Nieprawidlowy limit")

        if before_id is not None and (
            type(before_id) is not int
            or before_id <= 0
        ):
            raise ValueError("Nieprawidlowy kursor")

        if not self.path.is_file():
            raise FileNotFoundError(self.path.name)

        conditions = []
        params = []

        if before_id is not None:
            conditions.append("s.id < ?")
            params.append(before_id)

        if q:
            escaped = (
                str(q)
                .replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )

            conditions.append(
                "COALESCE(s.title,'') "
                "LIKE ? ESCAPE '\\'"
            )

            params.append("%" + escaped + "%")

        filters = ""

        if conditions:
            filters = (
                " AND " +
                " AND ".join(conditions)
            )

        sql = """
            SELECT s.*
            FROM snapshots s
            WHERE s.id = (
                SELECT MAX(v.id)
                FROM snapshots v
                WHERE v.offer_key=s.offer_key
            )
        """ + filters + """
            ORDER BY s.id DESC
            LIMIT ?
        """

        params.append(limit)

        with closing(sqlite3.connect(
            self.path.resolve().as_uri() + "?mode=ro",
            uri=True,
            timeout=10,
        )) as db:
            db.row_factory = sqlite3.Row

            rows = db.execute(
                sql, params
            ).fetchall()

        result = []

        for record in rows:
            row = dict(record)

            details = parse_json(
                row.get("details_json")
            )

            valuation = parse_json(
                row.get("valuation_json")
            )

            action = parse_json(
                row.get("action_json")
            )

            try:
                price_minor = (
                    to_minor(row["price"])
                    if row["price"] is not None
                    else None
                )
            except ValueError:
                price_minor = None

            result.append({
                "snapshot_id": row["id"],
                "offer_key": row["offer_key"],
                "title": row.get("title"),
                "url": row.get("url"),
                "platform": platform_from(
                    row.get("url"),
                    details.get("_source"),
                ),
                "price_minor": price_minor,
                "currency": "PLN",
                "decision": str(
                    action.get("action")
                    or action.get("decision")
                    or "UNKNOWN"
                ).upper(),
                "valuation": valuation,
                "observed_at": row.get("created_at"),
                "source_status": "UNKNOWN",
            })

        return result
