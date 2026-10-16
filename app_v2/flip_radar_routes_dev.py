from flask import Blueprint, jsonify, render_template, request

from .flip_radar_store_dev import (
    summary,
    search_offers,
    price_history,
)

flip_bp = Blueprint(
    "flip_radar",
    __name__,
    url_prefix="/flip-radar",
)


@flip_bp.route("/", methods=["GET"])
def flip_page():
    return render_template("flip_radar_dev.html")


@flip_bp.route("/api/summary", methods=["GET"])
def flip_summary():
    return jsonify(summary())


@flip_bp.route("/api/offers", methods=["GET"])
def flip_offers():
    try:
        return jsonify(search_offers(
            q=request.args.get("q", ""),
            source=request.args.get("source", ""),
            sort=request.args.get("sort", "recent"),
            page=int(request.args.get("page", 1)),
            page_size=30,
        ))
    except (ValueError, TypeError) as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 400


@flip_bp.route(
    "/api/history/<source>/<listing_id>",
    methods=["GET"]
)
def flip_history(source, listing_id):
    try:
        return jsonify({
            "items": price_history(source, listing_id)
        })
    except ValueError as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 400


from flask import flash, redirect, url_for

from .flip_profit_settings_v1 import read_policy, save_policy
from .flip_radar_store_dev import min_resale


@flip_bp.route("/settings", methods=["GET", "POST"])
def flip_policy_settings():
    if request.method == "POST":
        try:
            save_policy(request.form)
            flash("Ustawienia opłacalności zapisane.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        except Exception:
            from flask import current_app
            current_app.logger.exception(
                "Błąd zapisu ustawień Flip Radar"
            )
            flash("Nie udało się zapisać ustawień.", "error")

        return redirect(
            url_for("flip_radar.flip_policy_settings")
        )

    policy = read_policy()

    return render_template(
        "flip_profit_settings_v1.html",
        policy=policy,
        example_required=min_resale(1500, policy)
    )


# Saved Searches V1
from flask import abort, flash, redirect, render_template, request, url_for
from .saved_searches_v1 import (
    initialize, all_searches, one_search,
    save_search, change_status
)
from .flip_profit_settings_v1 import read_policy


@flip_bp.route('/searches', methods=['GET', 'POST'])
def search_page():
    if request.method == 'POST':
        try:
            save_search(request.form)
            flash('Wyszukiwanie dodane.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')

        return redirect(
            url_for('flip_radar.search_page')
        )

    return render_template(
        'saved_searches_v1.html',
        searches=all_searches(),
        search_stats=get_search_stats(),
        editing=None,
        policy=read_policy()
    )


@flip_bp.route(
    '/searches/<int:search_id>/edit',
    methods=['GET', 'POST']
)
def search_edit(search_id):
    existing = one_search(search_id)

    if existing is None:
        abort(404)

    if request.method == 'POST':
        try:
            save_search(request.form, search_id)
            flash('Zapisano zmiany.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')

        return redirect(
            url_for('flip_radar.search_page')
        )

    return render_template(
        'saved_searches_v1.html',
        searches=all_searches(),
        search_stats=get_search_stats(),
        editing=existing,
        policy=read_policy()
    )


@flip_bp.route(
    '/searches/<int:search_id>/action',
    methods=['POST']
)
def search_action(search_id):
    try:
        change_status(
            search_id,
            request.form.get('action')
        )
        flash('Zmieniono status.', 'success')
    except ValueError as exc:
        flash(str(exc), 'error')

    return redirect(
        url_for('flip_radar.search_page')
    )


from flask import abort
from .saved_searches_v1 import one_search as search_detail
import sqlite3 as _sqlite3
from pathlib import Path as _Path


@flip_bp.route(
    "/searches/<int:search_id>/results",
    methods=["GET"]
)
def saved_search_results_page(search_id):
    search = search_detail(search_id)

    if search is None:
        abort(404)

    path = _Path(
        "/opt/olx-bot-ui-dev/data/flip_radar_dev.sqlite3"
    )

    with _sqlite3.connect(
        path.resolve().as_uri() + "?mode=ro",
        uri=True
    ) as db:
        db.row_factory = _sqlite3.Row

        matches = db.execute("""
            SELECT title, asking_price_zl, url,
                   first_seen_utc, last_seen_utc,
                   match_status, match_reason
            FROM saved_search_matches
            WHERE search_id=? AND match_status != 'REJECT'
            ORDER BY last_seen_utc DESC,
                     asking_price_zl ASC
            LIMIT 200
        """, (search_id,)).fetchall()

        run = db.execute("""
            SELECT last_attempt_utc, status,
                   scanned_cards, saved_matches,
                   message
            FROM saved_search_runs
            WHERE search_id=?
        """, (search_id,)).fetchone()

    return render_template(
        "saved_search_results_v1.html",
        search=search,
        offers=[dict(x) for x in matches],
        market=get_market_snapshot(search_id),
        peer_finance=evaluate_search(search),
        gpu_guard=(evaluate_gpu_guard(search) if search["category"] == "gpu" else {}),
        run=dict(run) if run else None,
        new_cutoff=(_fh_datetime.now(_fh_timezone.utc) - _fh_timedelta(hours=24)).isoformat()
    )

from .saved_search_status_v1 import get_search_stats
from datetime import datetime as _fh_datetime, timezone as _fh_timezone, timedelta as _fh_timedelta

from .market_snapshot_v1 import get_market_snapshot
from .peer_valuation_v1 import evaluate_search
from .gpu_peer_filter_v3 import evaluate as evaluate_gpu_guard



from .review_queue_v1 import get_review_queue


@flip_bp.route("/review", methods=["GET"])
def review_queue_page():
    return render_template(
        "review_queue_v1.html",
        report=attach_history(attach_notes(prepare_queue(get_review_queue()))),
        review_token=make_review_token
    )


from flask import request as _review_request
from flask import abort as _review_abort
from flask import redirect as _review_redirect
from flask import url_for as _review_url_for
from flask import flash as _review_flash

from .review_decisions_v1 import (
    initialize as initialize_review,
    set_decision,
    prepare_queue
)

from .review_csrf_v1 import (
    make_review_token,
    verify_review_token
)


@flip_bp.route("/review/decision", methods=["POST"])
def review_set_decision():
    try:
        sid = int(_review_request.form.get("search_id", ""))
    except (TypeError, ValueError):
        _review_abort(400)

    listing_id = str(
        _review_request.form.get("listing_id") or ""
    ).strip()

    decision = _review_request.form.get("decision")

    if sid < 1 or decision not in (
        "interest", "checked", "rejected", "pending"
    ):
        _review_abort(400)

    if not verify_review_token(
        _review_request.form.get("review_token"),
        sid,
        listing_id
    ):
        _review_abort(403)

    try:
        set_decision(sid, listing_id, decision)
    except ValueError:
        _review_abort(404)

    _review_flash("Zapisano decyzję.", "success")

    return _review_redirect(
        _review_url_for("flip_radar.review_queue_page"),
        code=303
    )


from .review_notes_v1 import attach_notes
from .review_history_v1 import (
    attach_history,
    save_with_history as save_review_notes
)
from flask import (
    request as _note_request,
    abort as _note_abort,
    flash as _note_flash,
    redirect as _note_redirect,
    url_for as _note_url_for
)


@flip_bp.route("/review/notes", methods=["POST"])
def review_save_note():
    try:
        sid = int(
            _note_request.form.get("search_id", "")
        )
    except (ValueError, TypeError):
        _note_abort(400)

    listing_id = str(
        _note_request.form.get("listing_id") or ""
    ).strip()

    if sid < 1 or not 1 <= len(listing_id) <= 120:
        _note_abort(400)

    if not verify_review_token(
        _note_request.form.get("review_token"),
        sid,
        listing_id
    ):
        _note_abort(403)

    try:
        save_review_notes(
            sid,
            listing_id,
            _note_request.form.get("seller_name"),
            _note_request.form.get("contact_status"),
            _note_request.form.get("note_text")
        )
    except ValueError as exc:
        _note_abort(400, description=str(exc))

    _note_flash("Notatka zapisana.", "success")

    return _note_redirect(
        _note_url_for("flip_radar.review_queue_page"),
        code=303
    )


from .price_drops_view_v1 import get_price_drops_report


@flip_bp.route("/price-drops", methods=["GET"])
def price_drops_page():
    return render_template(
        "saved_price_drops_v1.html",
        report=get_price_drops_report()
    )


# SELLER_QUESTIONS_PREVIEW_V1
@flip_bp.route("/seller-questions-preview", methods=["GET"])
def seller_questions_preview_page():
    from flask import render_template
    from app_v2.seller_questions_preview_v1 import list_candidates

    from flask import request

    try:
        page = int(request.args.get("page", "1"))
    except (ValueError, TypeError):
        page = 1

    page = max(1, min(page, 1000))
    all_rows, total = list_candidates(limit=5000)
    per_page = 40
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    rows = all_rows[(page - 1) * per_page:page * per_page]

    return render_template(
        "seller_questions_preview_v1.html",
        rows=rows,
        total=total,
        page=page,
        pages=pages,
    )


# PC_VALUATION_PREVIEW_V1
@flip_bp.route("/valuation-preview", methods=["GET"])
def pc_valuation_preview_page():
    import json
    from pathlib import Path
    from flask import render_template

    path = Path(__file__).resolve().parent / "pc_valuation_snapshot_v1.json"
    snapshot = json.loads(path.read_text(encoding="utf-8"))

    return render_template(
        "pc_valuation_preview_v1.html",
        rows=snapshot["rows"],
        generated=snapshot["generated_utc"],
    )


# CATALOG_COVERAGE_GUI_V1
@flip_bp.route("/catalog-coverage", methods=["GET"])
def catalog_coverage_page():
    from flask import render_template
    from app_v2.catalog_coverage_v1 import get_report

    return render_template(
        "catalog_coverage_v1.html",
        report=get_report(),
    )
