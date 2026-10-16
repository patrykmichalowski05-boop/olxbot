import secrets

from . import config


def create_app():
    from flask import Flask, flash, jsonify, redirect, request, url_for
    from .security import auth_configured, csrf_valid, ensure_csrf_token, logged_in, request_is_api

    app = Flask(
        __name__,
        template_folder=str(config.PROJECT_ROOT / "templates_v2"),
        static_folder=str(config.PROJECT_ROOT / "static_v2"),
        static_url_path="/static/v2",
    )

    app.secret_key = config.DASHBOARD_SECRET_KEY or secrets.token_hex(32)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=config.COOKIE_SECURE,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )

    from .routes import bp
    app.register_blueprint(bp)

    from .flip_radar_routes_dev import flip_bp
    app.register_blueprint(flip_bp)

    @app.before_request
    def protect_application():
        ensure_csrf_token()

        public_get = {
            "main.login",
            "main.setup_required",
            "static",
        }

        if request.endpoint in public_get or request.path.startswith("/static/v2/"):
            # Login POST nadal ma ochronę CSRF.
            if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
                token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
                if not csrf_valid(token):
                    flash("Sesja formularza wygasła. Odśwież stronę i spróbuj ponownie.", "error")
                    return redirect(url_for("main.login"))
            return None

        if config.AUTH_REQUIRED:
            if not auth_configured():
                if request_is_api():
                    return jsonify({"ok": False, "error": "DASHBOARD_PASSWORD nie jest skonfigurowane"}), 503
                return redirect(url_for("main.setup_required"))

            if not logged_in():
                if request_is_api():
                    return jsonify({"ok": False, "error": "Brak autoryzacji"}), 401
                return redirect(url_for("main.login", next=request.full_path))

        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
            if not csrf_valid(token):
                if request_is_api():
                    return jsonify({"ok": False, "error": "Nieprawidłowy token CSRF"}), 400
                flash("Sesja formularza wygasła. Odśwież stronę i spróbuj ponownie.", "error")
                return redirect(request.referrer or url_for("main.dashboard"))

        return None

    @app.context_processor
    def inject_globals():
        def money(value):
            try:
                if value is None:
                    return "—"
                return f"{int(round(float(value))):,}".replace(",", " ") + " zł"
            except (TypeError, ValueError):
                return "—"

        def percent(value):
            try:
                if value is None:
                    return "—"
                return f"{float(value):.1f}%"
            except (TypeError, ValueError):
                return "—"

        return {
            "csrf_token": ensure_csrf_token,
            "money": money,
            "percent": percent,
            "crm_labels": config.CRM_LABELS,
            "crm_statuses": config.CRM_STATUSES,
            "refresh_seconds": config.REFRESH_SECONDS,
        }

    return app
