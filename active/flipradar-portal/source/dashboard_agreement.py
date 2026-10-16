import sqlite3

from flask import (
    Blueprint,
    redirect,
    request,
)

from crm_history import add_entry
from deal_crm import (
    ensure_deal,
    set_status,
)


agreement_bp = Blueprint(
    "agreement_dashboard",
    __name__,
)


ALERT_DB = "/opt/olx-bot/alert_history.db"


def get_alert(alert_id):
    conn = sqlite3.connect(ALERT_DB)
    conn.row_factory = sqlite3.Row

    row = conn.execute(
        """
        SELECT *
        FROM alerts
        WHERE id = ?
        """,
        (alert_id,),
    ).fetchone()

    conn.close()

    return row


@agreement_bp.post(
    "/offer/<int:alert_id>/agreement"
)
def agreement(alert_id):

    alert = get_alert(alert_id)

    if not alert:
        return redirect("/control")

    try:
        price = float(
            request.form.get("price")
        )

        if price <= 0:
            raise ValueError(
                "Nieprawidłowa cena"
            )

        add_entry(
            offer_key=alert["offer_key"],
            alert_id=alert["id"],
            kind="SELLER_OFFER",
            amount=price,
            note="Cena uzgodniona ze sprzedającym",
        )

        ensure_deal(
            offer_key=alert["offer_key"],
            alert_id=alert["id"],
            title=alert["title"],
            url=alert["url"],
        )

        set_status(
            alert["offer_key"],
            "PICKUP",
        )

    except Exception as e:
        print(
            "[AGREEMENT ERROR]",
            e,
        )

    return redirect(
        f"/offer/{alert_id}"
    )
