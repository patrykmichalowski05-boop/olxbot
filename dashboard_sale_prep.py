import sqlite3

from flask import (
    Blueprint,
    redirect,
    request,
)

from sale_prep import (
    add_cost,
    delete_cost,
    save_plan,
)

from deal_crm import (
    ensure_deal,
    set_status,
)


sale_prep_bp = Blueprint(
    "sale_prep_dashboard",
    __name__,
)


ALERT_DB = "/opt/olx-bot/alert_history.db"


def get_alert(alert_id):
    conn = sqlite3.connect(ALERT_DB)
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


@sale_prep_bp.post(
    "/offer/<int:alert_id>/prep/cost"
)
def prep_cost(alert_id):

    alert = get_alert(alert_id)

    if not alert:
        return redirect("/control")

    try:
        add_cost(
            offer_key=alert["offer_key"],
            alert_id=alert["id"],
            kind=request.form.get("kind"),
            cost=request.form.get("cost"),
            note=request.form.get("note"),
        )

        ensure_deal(
            offer_key=alert["offer_key"],
            alert_id=alert["id"],
            title=alert["title"],
            url=alert["url"],
        )

        set_status(
            alert["offer_key"],
            "PREPARING",
        )

    except Exception as e:
        print(
            "[SALE PREP COST ERROR]",
            e,
        )

    return redirect(
        f"/offer/{alert_id}"
    )


@sale_prep_bp.post(
    "/offer/<int:alert_id>/prep/plan"
)
def prep_plan(alert_id):

    alert = get_alert(alert_id)

    if not alert:
        return redirect("/control")

    try:
        save_plan(
            offer_key=alert["offer_key"],
            alert_id=alert["id"],
            target_price=request.form.get(
                "target_price"
            ),
            minimum_price=request.form.get(
                "minimum_price"
            ),
        )

        ensure_deal(
            offer_key=alert["offer_key"],
            alert_id=alert["id"],
            title=alert["title"],
            url=alert["url"],
        )

        set_status(
            alert["offer_key"],
            "PREPARING",
        )

    except Exception as e:
        print(
            "[SALE PREP PLAN ERROR]",
            e,
        )

    return redirect(
        f"/offer/{alert_id}"
    )


@sale_prep_bp.post(
    "/offer/<int:alert_id>/prep/ready"
)
def prep_ready(alert_id):

    alert = get_alert(alert_id)

    if not alert:
        return redirect("/control")

    ensure_deal(
        offer_key=alert["offer_key"],
        alert_id=alert["id"],
        title=alert["title"],
        url=alert["url"],
    )

    set_status(
        alert["offer_key"],
        "READY_TO_SELL",
    )

    return redirect(
        f"/offer/{alert_id}"
    )


@sale_prep_bp.post(
    "/offer/<int:alert_id>/prep/cost/<int:cost_id>/delete"
)
def prep_cost_delete(
    alert_id,
    cost_id,
):

    try:
        delete_cost(cost_id)

    except Exception as e:
        print(
            "[SALE PREP DELETE ERROR]",
            e,
        )

    return redirect(
        f"/offer/{alert_id}"
    )
