"""FlipRadar V12 compatibility routes for existing OLX bot databases.

Read-only. Does not create/alter/attach DBs, run migrations or modify scanners.
Install only behind the application's existing admin/session authorization.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
from contextlib import closing
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlparse

ACTIVE = frozenset({"BOUGHT", "PICKUP", "PREPARING", "READY_TO_SELL", "LISTED"})
IDENTIFIER = re.compile(r"^legacy-(\d+)$")


def _minor(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        num = Decimal(str(value))
        if not num.is_finite():
            return None
        return int((num * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _money_from_minor(value):
    if value is None:
        return None
    try:
        value = int(value)
        return value if value >= 0 else None
    except (TypeError, ValueError):
        return None


def _json(value):
    try:
        obj = json.loads(value or "{}")
        return obj if isinstance(obj, dict) else {}
    except (ValueError, TypeError):
        return {}


def _open_readonly(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path.name)
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    return db


def _has_table(conn, table):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _columns(conn, table):
    if not _has_table(conn, table):
        return set()
    # table comes from a fixed, trusted literal in this module
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}


def _platform(url, details):
    p = str(details.get("_source") or details.get("platform") or "").upper().strip()
    if p in {"FB", "FACEBOOK MARKETPLACE"}:
        return "FACEBOOK"
    if p in {"ALLEGRO LOKALNIE", "ALLEGRO_LOKALNIE"}:
        return "ALLEGRO_LOKALNIE"
    if p in {"OLX", "FACEBOOK", "OTOMOTO", "VINTED", "ALLEGRO_LOKALNIE"}:
        return p
    host = (urlparse(str(url or "")).hostname or "").lower()
    if host.endswith(".olx.pl") or host == "olx.pl":
        return "OLX"
    if host.endswith(".facebook.com") or host == "facebook.com":
        return "FACEBOOK"
    if host.endswith(".otomoto.pl") or host == "otomoto.pl":
        return "OTOMOTO"
    if host.endswith(".vinted.pl") or host == "vinted.pl":
        return "VINTED"
    if host.endswith(".allegrolokalnie.pl") or host == "allegrolokalnie.pl":
        return "ALLEGRO_LOKALNIE"
    return "UNKNOWN"


def _category(title, valuation):
    explicit = str(valuation.get("category") or valuation.get("product_category") or "").upper()
    if "CAR" in explicit or "AUTO" in explicit:
        return "CAR"
    if "FASHION" in explicit or "MODA" in explicit:
        return "FASHION"
    if "ELECTRON" in explicit or "PC" in explicit:
        return "ELECTRONICS"
    t = str(title or "").lower()
    if re.search(r"\b(bmw|audi|tesla|toyota|volkswagen|mercedes|skoda)\b", t):
        return "CAR"
    if re.search(r"\b(nike|adidas|buty|kurtka|bluza)\b", t):
        return "FASHION"
    if re.search(r"\b(rtx|radeon|laptop|komputer|pc|iphone|ryzen|intel|macbook)\b", t):
        return "ELECTRONICS"
    return "OTHER"


def _profit_and_roi(price_minor, valuation):
    # Legacy valuation amounts are in PLN, not grosze.
    profit = _minor(valuation.get("profit"))
    if profit is None:
        resale = _minor(valuation.get("quick_sale"))
        costs = _minor(valuation.get("total_cost"))
        if resale is not None and costs is not None:
            profit = resale - costs
        elif resale is not None and price_minor is not None:
            profit = resale - price_minor

    explicit_bps = valuation.get("roi_bps")
    if isinstance(explicit_bps, (int, float)) and not isinstance(explicit_bps, bool) and math.isfinite(explicit_bps):
        roi_bps = round(explicit_bps) if explicit_bps == explicit_bps else None
    else:
        roi_bps = None
    if roi_bps is None:
        explicit_pct = valuation.get("roi")
        if isinstance(explicit_pct, (int, float)) and not isinstance(explicit_pct, bool) and math.isfinite(explicit_pct):
            roi_bps = round(explicit_pct * 100)
    if roi_bps is None and profit is not None:
        investment = _minor(valuation.get("total_cost")) or price_minor
        if investment is not None and investment > 0:
            roi_bps = round(profit / investment * 10_000)
    return profit, roi_bps


class LegacyBridge:
    """Access existing sources with SQLite URI mode=ro; no writes or initialization."""

    def __init__(self, root):
        self.root = Path(root)

    def radar(self, *, limit=30, before_id=None, q="", min_price_minor=None,
              max_price_minor=None, min_profit_minor=None, min_roi_bps=None,
              category=None, platform=None):
        limit = int(limit)
        if not 1 <= limit <= 100:
            raise ValueError("limit must be 1..100")
        if before_id is not None:
            before_id = int(before_id)
            if before_id < 1:
                raise ValueError("invalid cursor")
        q = str(q or "").strip().lower()[:120]
        platform = str(platform or "").upper().strip()
        allowed_platforms = {"OLX", "FACEBOOK", "VINTED", "OTOMOTO", "ALLEGRO_LOKALNIE"}
        platform_set = {part.strip() for part in platform.split(",") if part.strip()}
        category = str(category or "").upper().strip()
        if not platform_set.issubset(allowed_platforms):
            raise ValueError("unsupported platform")
        if category not in {"", "ALL", "ELECTRONICS", "CAR", "FASHION", "OTHER"}:
            raise ValueError("unsupported category")
        for value in (min_price_minor, max_price_minor, min_profit_minor, min_roi_bps):
            if value is not None and (not isinstance(value, int) or value < 0):
                raise ValueError("negative or invalid filter")
        items = []
        cursor = before_id
        scanned = 0
        chunk = 200
        scan_cap = 4000  # defensive bound, paginates when highly selective
        with closing(_open_readonly(self.root / "offer_snapshots.db")) as db:
            if not _has_table(db, "snapshots"):
                raise sqlite3.DatabaseError("snapshots table missing")
            while scanned < scan_cap:
                terms = ["s.id = (SELECT MAX(v.id) FROM snapshots v WHERE v.offer_key=s.offer_key)"]
                args = []
                if cursor is not None:
                    terms.append("s.id < ?")
                    args.append(cursor)
                rows = db.execute(
                    "SELECT s.* FROM snapshots s WHERE " + " AND ".join(terms)
                    + " ORDER BY s.id DESC LIMIT ?", (*args, chunk),
                ).fetchall()
                if not rows:
                    return {"items": items, "next_before_id": None}
                for row in rows:
                    scanned += 1
                    r = dict(row)
                    cursor = int(r["id"])
                    val = _json(r.get("valuation_json"))
                    details = _json(r.get("details_json"))
                    price = _minor(r.get("price"))
                    profit, roi = _profit_and_roi(price, val)
                    title = str(r.get("title") or "")
                    item_platform = _platform(r.get("url"), details)
                    item_category = _category(title, val)
                    if q and q not in title.lower() and q not in str(r.get("offer_key") or "").lower():
                        continue
                    if platform_set and item_platform not in platform_set:
                        continue
                    if category not in {"", "ALL"} and item_category != category:
                        continue
                    if min_price_minor is not None and (price is None or price < min_price_minor):
                        continue
                    if max_price_minor is not None and (price is None or price > max_price_minor):
                        continue
                    if min_profit_minor is not None and (profit is None or profit < min_profit_minor):
                        continue
                    if min_roi_bps is not None and (roi is None or roi < min_roi_bps):
                        continue
                    action = _json(r.get("action_json"))
                    items.append({
                        "snapshot_id": cursor, "offer_key": r.get("offer_key"),
                        "title": r.get("title"), "url": r.get("url"),
                        "platform": item_platform, "category": item_category,
                        "price_minor": price, "profit_minor": profit, "roi_bps": roi,
                        "currency": "PLN", "decision": str(action.get("action") or action.get("decision") or "UNKNOWN").upper(),
                        "valuation": val, "observed_at": r.get("created_at"),
                        "source_status": "UNKNOWN",
                    })
                    if len(items) >= limit:
                        return {"items": items, "next_before_id": cursor}
                    if scanned >= scan_cap:
                        return {"items": items, "next_before_id": cursor}
                if len(rows) < chunk:
                    return {"items": items, "next_before_id": None}
        return {"items": items, "next_before_id": cursor}

    def deals(self, *, limit=100, before_id=None, status=None):
        limit = int(limit)
        if not 1 <= limit <= 200:
            raise ValueError("limit must be 1..200")
        raw_cursor = _deal_id(before_id) if before_id else None
        status = str(status or "").upper()
        items = []
        with closing(_open_readonly(self.root / "deal_crm.db")) as db:
            if not _has_table(db, "deals"):
                raise sqlite3.DatabaseError("deals table missing")
            terms, params = ["1=1"], []
            if raw_cursor:
                terms.append("id < ?")
                params.append(raw_cursor)
            if status:
                terms.append("status = ?")
                params.append(status)
            rows = db.execute("SELECT * FROM deals WHERE " + " AND ".join(terms)
                              + " ORDER BY id DESC LIMIT ?", (*params, limit + 1)).fetchall()
            has_next = len(rows) > limit
            for row in rows[:limit]:
                items.append(self._deal_details(db, dict(row)))
        return {"items": items,
                "next_before_id": items[-1]["id"] if has_next and items else None}

    def deal(self, deal_id):
        raw_id = _deal_id(deal_id)
        with closing(_open_readonly(self.root / "deal_crm.db")) as db:
            row = db.execute("SELECT * FROM deals WHERE id=?", (raw_id,)).fetchone()
            return self._deal_details(db, dict(row)) if row else None

    def _deal_details(self, crm, row):
        key = row.get("offer_key")
        alert_id = row.get("alert_id")
        prep_minor = 0
        extra_minor = 0
        purchase_minor = 0
        financials_complete = False
        if _has_table(crm, "sale_prep_costs"):
            costs = crm.execute(
                "SELECT cost FROM sale_prep_costs WHERE offer_key=?", (key,)
            ).fetchall()
            prep_minor = sum(_minor(c[0]) or 0 for c in costs)
        plan = None
        if _has_table(crm, "sale_plans"):
            plan = crm.execute("SELECT * FROM sale_plans WHERE offer_key=?", (key,)).fetchone()
        listed = None
        if _has_table(crm, "sale_listings"):
            listed = crm.execute("SELECT * FROM sale_listings WHERE offer_key=?", (key,)).fetchone()
        sale_minor = None
        try:
            with closing(_open_readonly(self.root / "flip_results.db")) as flip:
                columns = _columns(flip, "flips")
                if "alert_id" in columns and "purchase_price" in columns:
                    f = flip.execute(
                        "SELECT * FROM flips WHERE alert_id=? ORDER BY id DESC LIMIT 1", (alert_id,)
                    ).fetchone()
                    if f:
                        f = dict(f)
                        purchase_value = _minor(f.get("purchase_price"))
                        extra_value = _minor(f.get("extra_cost"))
                        financials_complete = (
                            purchase_value is not None and 0 <= purchase_value <= 9007199254740991
                            and (f.get("extra_cost") is None or extra_value is not None)
                        )
                        purchase_minor = purchase_value or 0
                        extra_minor = extra_value or 0
                        for name in ("sale_price", "sold_price", "final_sale_price"):
                            if name in f and f[name] is not None:
                                sale_minor = _minor(f[name])
                                break
        except (FileNotFoundError, sqlite3.Error):
            pass
        cost_minor = extra_minor + prep_minor
        status = str(row.get("status") or "NEW").upper()
        realized_profit = (
            sale_minor - purchase_minor - cost_minor
            if status == "SOLD" and sale_minor is not None and financials_complete else None
        )
        target = _minor(plan["target_price"]) if plan else None
        minimum = _minor(plan["minimum_price"]) if plan else None
        listing_price = _minor(listed["listed_price"]) if listed else None
        return {
            "id": f"legacy-{row['id']}", "listing_id": str(alert_id) if alert_id else None,
            "offer_key": key, "title": row.get("title"), "url": row.get("url"),
            "status": status, "currency": "PLN", "created_at": row.get("created_at"),
            "purchase_minor": purchase_minor, "cost_minor": cost_minor,
            "sale_minor": sale_minor, "realized_profit_minor": realized_profit,
            "target_price_minor": target, "minimum_price_minor": minimum,
            "listed_price_minor": listing_price,
            "financials_complete": financials_complete,
            "financials_note": None if financials_complete else "Brak zarejestrowanej ceny zakupu w flip_results.db",
        }


def _deal_id(value):
    m = IDENTIFIER.fullmatch(str(value or ""))
    if m is None:
        raise ValueError("invalid legacy deal ID")
    return int(m.group(1))


def register_flask(app, data_root, require_admin):
    """Attach routes to an existing Flask application. require_admin() MUST check current session and role."""
    if not callable(require_admin):
        raise TypeError("require_admin must be a callable enforcing an authenticated admin session")
    from flask import Blueprint, abort, jsonify, request
    service = LegacyBridge(data_root)
    bp = Blueprint("flipradar_v12_legacy_bridge", __name__)

    @bp.before_request
    def _guard():
        if require_admin() is not True:
            abort(403)

    def _num(name):
        raw = request.args.get(name)
        if raw is None or raw == "":
            return None
        n = int(raw)
        if n < 0:
            raise ValueError("negative parameter")
        return n

    @bp.get("/api/v12/legacy/radar")
    def radar_view():
        try:
            return jsonify(service.radar(
                limit=int(request.args.get("limit", 30)),
                before_id=_num("before_id"), q=request.args.get("q", ""),
                min_price_minor=_num("min_price_minor"),
                max_price_minor=_num("max_price_minor"),
                min_profit_minor=_num("min_profit_minor"),
                min_roi_bps=_num("min_roi_bps"),
                category=request.args.get("category"), platform=request.args.get("platform"),
            ))
        except (ValueError, TypeError):
            return jsonify({"detail": "Nieprawidłowe filtry"}), 422
        except (FileNotFoundError, sqlite3.Error):
            return jsonify({"detail": "Baza radaru jest niedostępna"}), 503

    @bp.get("/api/v2/workspaces/legacy/deals")
    def deals_view():
        try:
            return jsonify(service.deals(
                limit=int(request.args.get("limit", 100)),
                before_id=request.args.get("before_id"), status=request.args.get("status"),
            ))
        except (ValueError, TypeError):
            return jsonify({"detail": "Nieprawidłowe parametry"}), 422
        except (FileNotFoundError, sqlite3.Error):
            return jsonify({"detail": "Baza magazynu jest niedostępna"}), 503

    @bp.get("/api/v2/workspaces/legacy/deals/<deal_id>")
    def deal_view(deal_id):
        try:
            deal = service.deal(deal_id)
            return jsonify(deal) if deal else (jsonify({"detail": "Brak flipa"}), 404)
        except ValueError:
            return jsonify({"detail": "Nieprawidłowy identyfikator"}), 422
        except (FileNotFoundError, sqlite3.Error):
            return jsonify({"detail": "Baza magazynu jest niedostępna"}), 503

    app.register_blueprint(bp)
    return bp


def register_fastapi(app, data_root, require_admin):
    """Attach equivalent endpoints to an existing FastAPI application with admin dependency."""
    if not callable(require_admin):
        raise TypeError("require_admin must be an authenticated admin dependency")
    from fastapi import APIRouter, Depends, HTTPException, Query
    service = LegacyBridge(data_root)
    def _admin_guard(granted=Depends(require_admin)):
        if granted is not True:
            raise HTTPException(403, "Administrator access required")

    router = APIRouter(dependencies=[Depends(_admin_guard)])

    @router.get("/api/v12/legacy/radar")
    def radar_view(limit: int = Query(30, ge=1, le=100), before_id: int | None = Query(None, gt=0),
                   q: str = Query("", max_length=120), min_price_minor: int | None = Query(None, ge=0),
                   max_price_minor: int | None = Query(None, ge=0),
                   min_profit_minor: int | None = Query(None, ge=0),
                   min_roi_bps: int | None = Query(None, ge=0),
                   category: str | None = None, platform: str | None = None):
        try:
            return service.radar(limit=limit, before_id=before_id, q=q,
                                 min_price_minor=min_price_minor, max_price_minor=max_price_minor,
                                 min_profit_minor=min_profit_minor, min_roi_bps=min_roi_bps,
                                 category=category, platform=platform)
        except ValueError:
            raise HTTPException(422, "Invalid filters") from None
        except (FileNotFoundError, sqlite3.Error):
            raise HTTPException(503, "Radar database unavailable") from None

    @router.get("/api/v2/workspaces/legacy/deals")
    def deals_view(limit: int = Query(100, ge=1, le=200), before_id: str | None = None,
                   status: str | None = None):
        try:
            return service.deals(limit=limit, before_id=before_id, status=status)
        except ValueError:
            raise HTTPException(422, "Invalid pagination") from None
        except (FileNotFoundError, sqlite3.Error):
            raise HTTPException(503, "Legacy CRM unavailable") from None

    @router.get("/api/v2/workspaces/legacy/deals/{deal_id}")
    def deal_view(deal_id: str):
        try:
            result = service.deal(deal_id)
            if result is None:
                raise HTTPException(404, "Deal not found")
            return result
        except ValueError:
            raise HTTPException(422, "Invalid deal identifier") from None
        except (FileNotFoundError, sqlite3.Error):
            raise HTTPException(503, "Legacy CRM unavailable") from None

    app.include_router(router)
    return router
