from flask import (
    Blueprint,
    redirect,
)

from deal_crm import (
    set_status_from_alert,
)


crm_bp = Blueprint(
    "crm_dashboard",
    __name__,
)


@crm_bp.post(
    "/offer/<int:alert_id>/crm/<status>"
)
def crm_status(
    alert_id,
    status,
):
    try:
        set_status_from_alert(
            alert_id,
            status,
        )

    except Exception as e:
        print(
            "[CRM ERROR]",
            e,
        )

    return redirect(
        f"/offer/{alert_id}"
    )
