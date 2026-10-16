import sqlite3
from datetime import datetime

from flask import (
    Blueprint,
    redirect,
    request,
)

from crm_followup import (
    create_followup,
    schedule_from_mode,
    complete,
    cancel,
)


followup_bp = Blueprint(
    "followup_dashboard",
    __name__,
)


ALERT_DB = "/opt/olx-bot/alert_history.db"


def get_alert(
    alert_id,
):
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


@followup_bp.post(
    "/offer/<int:alert_id>/followup/<mode>"
)
def followup_preset(
    alert_id,
    mode,
):
    alert = get_alert(
        alert_id
    )

    if not alert:
        return redirect(
            "/control"
        )

    try:
        due = schedule_from_mode(
            mode
        )

        create_followup(
            offer_key=alert["offer_key"],
            alert_id=alert["id"],
            title=alert["title"],
            url=alert["url"],
            due_at=due.isoformat(
                timespec="seconds"
            ),
            note=request.form.get(
                "note"
            ),
        )

    except Exception as e:
        print(
            "[FOLLOWUP ERROR]",
            e,
        )

    return redirect(
        f"/offer/{alert_id}"
    )


@followup_bp.post(
    "/offer/<int:alert_id>/followup/custom"
)
def followup_custom(
    alert_id,
):
    alert = get_alert(
        alert_id
    )

    if not alert:
        return redirect(
            "/control"
        )

    raw_due = request.form.get(
        "due_at"
    )

    try:
        due = datetime.fromisoformat(
            raw_due
        )

        create_followup(
            offer_key=alert["offer_key"],
            alert_id=alert["id"],
            title=alert["title"],
            url=alert["url"],
            due_at=due.isoformat(
                timespec="seconds"
            ),
            note=request.form.get(
                "note"
            ),
        )

    except Exception as e:
        print(
            "[FOLLOWUP CUSTOM ERROR]",
            e,
        )

    return redirect(
        f"/offer/{alert_id}"
    )


@followup_bp.post(
    "/followup/<int:followup_id>/done"
)
def followup_done(
    followup_id,
):
    complete(
        followup_id
    )

    return redirect(
        "/control"
    )


@followup_bp.post(
    "/followup/<int:followup_id>/cancel"
)
def followup_cancel(
    followup_id,
):
    cancel(
        followup_id
    )

    return redirect(
        "/control"
    )
