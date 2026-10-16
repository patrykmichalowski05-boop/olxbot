from flask import (
    abort,
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from . import config
from .security import auth_configured, safe_next, verify_credentials
from .services import (
    alert_detail,
    add_history_entry,
    add_sale_cost,
    analytics_data,
    buy_offer,
    close_watch,
    crm_board,
    dashboard_data,
    health_data,
    inventory_data,
    job_logs,
    market_data,
    mark_listing_action,
    recent_alerts,
    run_job,
    save_sale_plan_action,
    schedule_followup,
    sell_flip,
    set_crm_status,
    system_data,
    update_followup,
    update_pickup_check,
    update_purchase_check,
    change_listing_price_action,
    watchlist_data,
)

bp = Blueprint("main", __name__)


@bp.get("/setup-required")
def setup_required():
    if not config.AUTH_REQUIRED or auth_configured():
        return redirect(url_for("main.dashboard"))
    return render_template("setup_required.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if not config.AUTH_REQUIRED:
        return redirect(url_for("main.dashboard"))

    if not auth_configured():
        return redirect(url_for("main.setup_required"))

    if request.method == "POST":
        if verify_credentials(request.form.get("username"), request.form.get("password")):
            session.clear()
            session["authenticated"] = True
            # Nowy token po logowaniu ogranicza możliwość utrwalenia sesji.
            from .security import ensure_csrf_token
            ensure_csrf_token()
            return redirect(safe_next(request.form.get("next")))
        flash("Nieprawidłowy login lub hasło.", "error")

    return render_template("login.html", next=safe_next(request.args.get("next")))


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))


@bp.get("/")
def dashboard():
    return render_template(
        "dashboard.html",
        page="dashboard",
        data=dashboard_data(),
    )


@bp.get("/offers")
def offers():
    filters = {
        "q": request.args.get("q", ""),
        "source": request.args.get("source", "ALL"),
        "decision": request.args.get("decision", "ALL"),
        "min_score": request.args.get("min_score", ""),
    }
    filters["archived"] = request.args.get("archived", "0")
    return render_template(
        "offers.html",
        page="offers",
        items=recent_alerts(200, filters),
        filters=filters,
    )


@bp.get("/offer/<int:alert_id>")
def offer(alert_id):
    from app_v2.alert_archive import archived_ids
    item = alert_detail(alert_id)
    if item is None:
        flash("Nie znaleziono oferty.", "error")
        return redirect(url_for("main.offers"))
    return render_template(
        "offer.html",
        archived=(alert_id in archived_ids()),
        page="offers",
        item=item,
    )


@bp.get("/watchlist")
def watchlist():
    return render_template(
        "watchlist.html",
        page="watchlist",
        items=watchlist_data(),
    )


@bp.get("/crm")
def crm():
    return render_template(
        "crm.html",
        page="crm",
        board=crm_board(),
    )


@bp.get("/inventory")
def inventory():
    return render_template(
        "inventory.html",
        page="inventory",
        data=inventory_data(),
    )


@bp.get("/analytics")
def analytics():
    return render_template(
        "analytics.html",
        page="analytics",
        data=analytics_data(),
    )


@bp.get("/market")
def market():
    return render_template(
        "market.html",
        page="market",
        data=market_data(),
    )


@bp.get("/system")
def system():
    return render_template(
        "system.html",
        page="system",
        data=system_data(),
    )


@bp.get("/system/logs/<job_key>")
def logs(job_key):
    try:
        data = job_logs(job_key)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.system"))
    return render_template(
        "logs.html",
        page="system",
        job_key=job_key,
        data=data,
    )



@bp.post("/actions/offer/<int:alert_id>/archive")
def action_alert_archive(alert_id):
    from app_v2.alert_archive import set_archived
    if alert_detail(alert_id) is None:
        abort(404)
    set_archived(alert_id, True)
    flash("Oferta przeniesiona do archiwum.", "success")
    return redirect(url_for("main.offers"))


@bp.post("/actions/offer/<int:alert_id>/restore")
def action_alert_restore(alert_id):
    from app_v2.alert_archive import set_archived
    if alert_detail(alert_id) is None:
        abort(404)
    set_archived(alert_id, False)
    flash("Oferta przywrocona.", "success")
    return redirect(url_for("main.offers", archived=1))


@bp.post("/actions/offer/<int:alert_id>/crm/<status>")
def action_crm(alert_id, status):
    try:
        set_crm_status(alert_id, status)
        flash(f"Status CRM zmieniony na {config.CRM_LABELS.get(status.upper(), status)}.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(request.referrer or url_for("main.offer", alert_id=alert_id))


@bp.post("/actions/offer/<int:alert_id>/buy")
def action_buy(alert_id):
    try:
        buy_offer(
            alert_id,
            request.form.get("purchase_price"),
            request.form.get("extra_cost", 0),
        )
        flash("Komputer oznaczony jako kupiony.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.offer", alert_id=alert_id))


@bp.post("/actions/flip/<int:flip_id>/sell")
def action_sell(flip_id):
    try:
        sell_flip(
            flip_id,
            request.form.get("sale_price"),
            request.form.get("extra_cost", 0),
        )
        flash("Sprzedaż zapisana.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(request.referrer or url_for("main.inventory"))


@bp.post("/actions/watchlist/<int:item_id>/close")
def action_watch_close(item_id):
    try:
        close_watch(item_id)
        flash("Pozycja usunięta z aktywnej watchlisty.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.watchlist"))


@bp.post("/actions/offer/<int:alert_id>/history")
def action_history_add(alert_id):
    try:
        add_history_entry(
            alert_id,
            request.form.get("kind"),
            request.form.get("amount"),
            request.form.get("note"),
        )
        flash("Wpis dodany do historii negocjacji.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.offer", alert_id=alert_id))


@bp.post("/actions/offer/<int:alert_id>/followup")
def action_followup_add(alert_id):
    try:
        schedule_followup(
            alert_id,
            request.form.get("mode"),
            request.form.get("due_at") or None,
            request.form.get("note"),
        )
        flash("Follow-up zapisany.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.offer", alert_id=alert_id))


@bp.post("/actions/followup/<int:followup_id>/<action>")
def action_followup_update(followup_id, action):
    try:
        update_followup(followup_id, action)
        flash("Follow-up zaktualizowany.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(request.referrer or url_for("main.crm"))


@bp.post("/actions/offer/<int:alert_id>/check/<item_key>/<status>")
def action_purchase_check(alert_id, item_key, status):
    try:
        update_purchase_check(alert_id, item_key, status)
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.offer", alert_id=alert_id))


@bp.post("/actions/offer/<int:alert_id>/pickup/<item_key>/<status>")
def action_pickup_check(alert_id, item_key, status):
    try:
        update_pickup_check(alert_id, item_key, status, request.form.get("note"))
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.offer", alert_id=alert_id))


@bp.post("/actions/offer/<int:alert_id>/sale-cost")
def action_sale_cost(alert_id):
    try:
        add_sale_cost(
            alert_id, request.form.get("kind"), request.form.get("cost"), request.form.get("note")
        )
        flash("Koszt przygotowania dodany.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.offer", alert_id=alert_id))


@bp.post("/actions/offer/<int:alert_id>/sale-plan")
def action_sale_plan(alert_id):
    try:
        save_sale_plan_action(
            alert_id, request.form.get("target_price"), request.form.get("minimum_price")
        )
        flash("Plan sprzedaży zapisany.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.offer", alert_id=alert_id))


@bp.post("/actions/offer/<int:alert_id>/listing")
def action_listing(alert_id):
    try:
        mark_listing_action(
            alert_id, request.form.get("listed_price"), request.form.get("platform") or "OLX"
        )
        flash("Ogłoszenie oznaczone jako wystawione.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.offer", alert_id=alert_id))


@bp.post("/actions/offer/<int:alert_id>/listing/price")
def action_listing_price(alert_id):
    try:
        change_listing_price_action(
            alert_id, request.form.get("new_price"), request.form.get("reason") or "MANUAL"
        )
        flash("Cena ogłoszenia zaktualizowana.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.offer", alert_id=alert_id))


@bp.post("/actions/jobs/<job_key>/run")
def action_run_job(job_key):
    try:
        result = run_job(job_key)
        if result["ok"]:
            flash(f"Uruchomiono {result['service']}.", "success")
        else:
            flash(result["stderr"] or f"Nie udało się uruchomić {result['service']}.", "error")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.system"))


@bp.get("/api/overview")
def api_overview():
    return jsonify(dashboard_data())


@bp.get("/api/health")
def api_health():
    return jsonify(health_data())


@bp.get("/api/offers")
def api_offers():
    filters = {
        "q": request.args.get("q", ""),
        "source": request.args.get("source", "ALL"),
        "decision": request.args.get("decision", "ALL"),
        "min_score": request.args.get("min_score", ""),
    }
    return jsonify(recent_alerts(request.args.get("limit", 100), filters))


@bp.route("/settings", methods=["GET", "POST"])
def scanner_settings_page():
    import sqlite3
    from flask import current_app
    from scanner_settings import (
        get_all, get_history, save_settings
    )

    fields = [
        ("min_profit", "Minimalny zysk", "Prog rentownosci okazji"),
        ("hot_profit", "Prog HOT", "Bardzo dobra okazja"),
        ("ai_min_profit", "Prog przed AI", "Wstepna analiza OLX"),
        ("final_min_profit", "Prog koncowy OLX", "Filtr po analizie AI"),
        ("facebook_min_profit", "Prog Facebook", "Facebook Marketplace"),
        ("min_ram_gb", "Minimalny RAM", "Minimum pamieci komputera"),
        ("max_purchase_price", "Maks. cena zakupu", "0 = bez limitu; filtr ceny podlaczymy do skanerow"),
    ]

    if request.method == "POST":
        try:
            changes = save_settings(
                request.form,
                actor=config.DASHBOARD_USERNAME
            )
            flash(
                f"Zapisano {changes} zmian ustawien.",
                "success"
            )
        except ValueError as exc:
            flash(str(exc), "error")
        except (sqlite3.Error, OSError):
            current_app.logger.exception("Blad zapisu ustawien")
            flash("Blad zapisu ustawien.", "error")

        return redirect(url_for("main.scanner_settings_page"))

    return render_template(
        "settings.html",
        page="settings",
        fields=fields,
        settings=get_all(),
        history=get_history(30),
    )
