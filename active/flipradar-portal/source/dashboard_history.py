import sqlite3

from flask import (
    Blueprint,
    redirect,
    request,
)

from crm_history import (
    add_entry,
)

from deal_crm import (
    status_for_offer,
    set_status_from_alert,
)


history_bp = Blueprint(
    "history_dashboard",
    __name__,
)


ALERT_DB = "/opt/olx-bot/alert_history.db"


def get_alert(alert_id):
    conn = sqlite3.connect(
        ALERT_DB
    )

    conn.row_factory = sqlite3.Row

    row = conn.execute("""
        SELECT *
        FROM alerts
        WHERE id = ?
    """, (
        alert_id,
    )).fetchone()

    conn.close()

    return row


@history_bp.post(
    "/offer/<int:alert_id>/history/add"
)
def history_add(
    alert_id,
):
    alert = get_alert(
        alert_id
    )

    if not alert:
        return redirect(
            "/control"
        )

    kind = request.form.get(
        "kind",
        "NOTE"
    ).upper()

    amount = request.form.get(
        "amount"
    )

    note = request.form.get(
        "note"
    )

    try:
        add_entry(
            offer_key=alert["offer_key"],
            alert_id=alert["id"],
            kind=kind,
            amount=amount,
            note=note,
        )

        current = status_for_offer(
            alert["offer_key"]
        )

        # Pierwsza wiadomość = KONTAKT
        if (
            kind in {
                "NOTE",
                "MESSAGE",
            }
            and current == "NEW"
        ):
            set_status_from_alert(
                alert_id,
                "CONTACTED",
            )

        # Oferta cenowa = NEGOCJACJE
        if (
            kind in {
                "MY_OFFER",
                "SELLER_OFFER",
            }
            and current in {
                "NEW",
                "CONTACTED",
            }
        ):
            set_status_from_alert(
                alert_id,
                "NEGOTIATING",
            )

    except Exception as e:
        print(
            "[CRM HISTORY ERROR]",
            e,
        )

    return redirect(
        f"/offer/{alert_id}"
    )
