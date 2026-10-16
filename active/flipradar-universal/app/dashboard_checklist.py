import sqlite3

from flask import (
    Blueprint,
    redirect,
)

from purchase_checklist import (
    set_status,
)


checklist_bp = Blueprint(
    "purchase_checklist_dashboard",
    __name__,
)


ALERT_DB = "/opt/olx-bot/alert_history.db"


def offer_key_for_alert(
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

    if not row:
        return None

    return row[
        "offer_key"
    ]


@checklist_bp.post(
    "/offer/<int:alert_id>/check/"
    "<item_key>/<status>"
)
def update_check(
    alert_id,
    item_key,
    status,
):
    offer_key = (
        offer_key_for_alert(
            alert_id
        )
    )

    if offer_key:

        try:

            set_status(
                offer_key,
                item_key,
                status,
            )

        except Exception as e:

            print(
                "[CHECKLIST ERROR]",
                e,
            )

    return redirect(
        f"/offer/{alert_id}"
    )
