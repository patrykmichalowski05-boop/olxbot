import sqlite3

from flask import (
    Blueprint,
    redirect,
)

from pickup_checklist import (
    set_check,
)


pickup_bp = Blueprint(
    "pickup_dashboard",
    __name__,
)


ALERT_DB = "/opt/olx-bot/alert_history.db"


def get_offer_key(
    alert_id,
):
    conn = sqlite3.connect(
        ALERT_DB
    )

    conn.row_factory = sqlite3.Row

    row = conn.execute("""
        SELECT offer_key
        FROM alerts
        WHERE id = ?
    """, (
        alert_id,
    )).fetchone()

    conn.close()

    return (
        row["offer_key"]
        if row
        else None
    )


@pickup_bp.post(
    "/offer/<int:alert_id>/pickup/check/<item_key>/<status>"
)
def pickup_check(
    alert_id,
    item_key,
    status,
):
    offer_key = get_offer_key(
        alert_id
    )

    if offer_key:

        try:
            set_check(
                offer_key,
                item_key,
                status,
            )

        except Exception as e:
            print(
                "[PICKUP CHECK ERROR]",
                e,
            )

    return redirect(
        f"/offer/{alert_id}"
    )
