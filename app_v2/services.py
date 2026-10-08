import json
import sqlite3
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta

from . import config
from .db import columns, connect, execute, one, query, scalar, table_exists


def _dict(row):
    return dict(row) if row is not None else None


def _json(value, default=None):
    if default is None:
        default = {}
    if not value:
        return default
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, (dict, list)) else default
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _number(value, default=None):
    try:
        if value is None or value == "":
            return default
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _latest_snapshots(offer_keys):
    if not offer_keys or not table_exists(config.DATABASES["snapshots"], "snapshots"):
        return {}

    unique = list(dict.fromkeys(str(x) for x in offer_keys if x))
    placeholders = ",".join("?" for _ in unique)
    sql = f"""
        SELECT s.*
        FROM snapshots s
        JOIN (
            SELECT offer_key, MAX(id) AS max_id
            FROM snapshots
            WHERE offer_key IN ({placeholders})
            GROUP BY offer_key
        ) latest ON latest.max_id = s.id
    """
    rows = query(config.DATABASES["snapshots"], sql, tuple(unique))
    return {row["offer_key"]: dict(row) for row in rows}


def _source(alert, snapshot=None):
    snapshot = snapshot or {}
    details = _json(snapshot.get("details_json"))
    explicit = str(details.get("_source") or "").upper()
    title = str(alert.get("title") or "").upper()
    url = str(alert.get("url") or "").lower()

    if "FACEBOOK" in explicit or "[FB MARKETPLACE]" in title or "facebook.com" in url:
        return "FACEBOOK"
    return "OLX"


def _decision(alert, snapshot=None):
    snapshot = snapshot or {}
    action = _json(snapshot.get("action_json"))
    value = str(action.get("action") or "").upper()
    if value:
        return value

    score = _number(alert.get("score"), 0) or 0
    profit = _number(alert.get("profit"), 0) or 0
    if score >= 85 and profit >= 600:
        return "BUY_NOW"
    if score >= 75 and profit >= 500:
        return "BUY"
    if profit >= 300 or score >= 60:
        return "WATCH"
    return "SKIP"


def recent_alerts(limit=100, filters=None):
    filters = filters or {}
    limit = max(1, min(_int(limit, 100), 500))
    rows = query(
        config.DATABASES["alerts"],
        "SELECT * FROM alerts ORDER BY id DESC LIMIT ?",
        (max(limit * 4, 200),),
    )
    alerts = [dict(row) for row in rows]
    snapshots = _latest_snapshots([row.get("offer_key") for row in alerts])

    q = str(filters.get("q") or "").strip().lower()
    source_filter = str(filters.get("source") or "ALL").upper()
    decision_filter = str(filters.get("decision") or "ALL").upper()
    min_score = _number(filters.get("min_score"), None)

    result = []
    for alert in alerts:
        snapshot = snapshots.get(alert.get("offer_key"), {})
        source = _source(alert, snapshot)
        decision = _decision(alert, snapshot)
        action = _json(snapshot.get("action_json"))
        valuation = _json(snapshot.get("valuation_json"))
        details = _json(snapshot.get("details_json"))

        item = dict(alert)
        item.update(
            source=source,
            decision=decision,
            action=action,
            valuation=valuation,
            details=details,
            opening=action.get("opening"),
            max_buy=action.get("max_buy"),
            confidence=valuation.get("confidence"),
        )

        if q and q not in f"{item.get('title', '')} {item.get('offer_key', '')}".lower():
            continue
        if source_filter != "ALL" and source != source_filter:
            continue
        if decision_filter != "ALL" and decision != decision_filter:
            continue
        if min_score is not None and (_number(item.get("score"), 0) or 0) < min_score:
            continue

        result.append(item)
        if len(result) >= limit:
            break

    return result


def alert_detail(alert_id):
    alert_row = one(
        config.DATABASES["alerts"],
        "SELECT * FROM alerts WHERE id = ?",
        (alert_id,),
    )
    if alert_row is None:
        return None

    alert = dict(alert_row)
    snapshot_row = one(
        config.DATABASES["snapshots"],
        "SELECT * FROM snapshots WHERE offer_key = ? ORDER BY id DESC LIMIT 1",
        (alert.get("offer_key"),),
    )
    snapshot = dict(snapshot_row) if snapshot_row else {}

    alert["source"] = _source(alert, snapshot)
    alert["decision"] = _decision(alert, snapshot)
    alert["details"] = _json(snapshot.get("details_json"))
    alert["valuation"] = _json(snapshot.get("valuation_json"))
    alert["action"] = _json(snapshot.get("action_json"))

    deal = one(
        config.DATABASES["crm"],
        "SELECT * FROM deals WHERE offer_key = ?",
        (alert.get("offer_key"),),
    )
    alert["deal"] = _dict(deal)

    flip = one(
        config.DATABASES["flips"],
        "SELECT * FROM flips WHERE alert_id = ? ORDER BY id DESC LIMIT 1",
        (alert_id,),
    )
    alert["flip"] = _dict(flip)

    alert["followups"] = [
        dict(row)
        for row in query(
            config.DATABASES["crm"],
            "SELECT * FROM followups WHERE offer_key = ? ORDER BY id DESC LIMIT 20",
            (alert.get("offer_key"),),
        )
    ]

    alert["history"] = [
        dict(row)
        for row in query(
            config.DATABASES["crm"],
            "SELECT * FROM deal_history WHERE offer_key = ? ORDER BY id DESC LIMIT 30",
            (alert.get("offer_key"),),
        )
    ] if table_exists(config.DATABASES["crm"], "deal_history") else []

    alert["purchase_checks"] = [
        dict(row)
        for row in query(
            config.DATABASES["checks"],
            "SELECT * FROM checks WHERE offer_key = ? ORDER BY item_key",
            (alert.get("offer_key"),),
        )
    ]

    # Narzędzia istniejące już w repo. Błędy pojedynczego modułu nie mogą
    # wywrócić całej strony oferty.
    alert["seller_questions"] = []
    alert["seller_message"] = None
    alert["negotiation"] = {}
    alert["negotiation_message"] = None
    alert["negotiation_variants"] = []
    alert["sale_prep"] = {}
    alert["sale_prices"] = {}
    alert["listing"] = {}

    try:
        from purchase_checklist import get_checklist
        from seller_questions import build_message, build_questions
        checklist = get_checklist(alert.get("offer_key"))
        alert["purchase_checks"] = checklist
        alert["seller_questions"] = build_questions(checklist)
        alert["seller_message"] = build_message(checklist)
    except Exception:
        pass

    try:
        from negotiation_helper import calculate_negotiation
        from negotiation_message import build_negotiation_message
        from negotiation_variants import build_variants
        negotiation = calculate_negotiation(
            alert.get("history") or [],
            alert.get("action", {}).get("max_buy"),
            alert.get("action", {}).get("opening"),
        )
        alert["negotiation"] = negotiation
        alert["negotiation_message"] = build_negotiation_message(negotiation)
        alert["negotiation_variants"] = build_variants(
            negotiation,
            alert.get("action", {}).get("opening"),
        )
    except Exception:
        pass

    alert["pickup_checks"] = []
    alert["pickup_readiness"] = {}
    try:
        from pickup_checklist import get_checklist as get_pickup_checklist, readiness
        pickup = get_pickup_checklist(alert.get("offer_key"))
        alert["pickup_checks"] = pickup
        alert["pickup_readiness"] = readiness(pickup)
    except Exception:
        pass

    alert["sale_listing"] = None
    alert["sale_price_history"] = []

    if alert.get("flip"):
        try:
            from sale_prep import summary as sale_prep_summary
            from sale_pricing import calculate_sale_prices
            from listing_generator import build_listing
            prep = sale_prep_summary(
                alert.get("offer_key"),
                alert_id,
                alert.get("quick_sale"),
            )
            prices = calculate_sale_prices(
                prep.get("total_investment"),
                alert.get("quick_sale"),
            )
            merged_prep = dict(prep)
            if not merged_prep.get("target_price"):
                merged_prep["target_price"] = prices.get("target_price")
            if not merged_prep.get("minimum_price"):
                merged_prep["minimum_price"] = prices.get("minimum_price")
            alert["sale_prep"] = merged_prep
            alert["sale_prices"] = prices
            alert["listing"] = build_listing(alert.get("details") or {}, merged_prep)
            try:
                from sale_listing_tracker import get_listing, price_history
                listing_row = get_listing(alert.get("offer_key"))
                alert["sale_listing"] = dict(listing_row) if listing_row else None
                alert["sale_price_history"] = [dict(row) for row in price_history(alert.get("offer_key"))]
            except Exception:
                pass
        except Exception:
            pass

    return alert


def _queue_stats():
    stats = {"pending": 0, "processing": 0, "done": 0, "failed": 0}
    for row in query(
        config.DATABASES["fast"],
        "SELECT LOWER(status) AS status, COUNT(*) AS cnt FROM queue GROUP BY status",
    ):
        if row["status"] in stats:
            stats[row["status"]] = row["cnt"]
    return stats


def _fallback_health():
    return {
        "score": 0,
        "status": "UNKNOWN",
        "modules": [],
        "queue": _queue_stats(),
        "market": {},
        "watchlist": {},
        "errors": 0,
    }


def health_data():
    try:
        from dashboard_health import collect_health
        return collect_health()
    except Exception as exc:
        result = _fallback_health()
        result["error"] = str(exc)
        return result


def inventory_data():
    try:
        from control_inventory import collect_inventory, inventory_stats
        items = collect_inventory()
        for item in items:
            flip = one(
                config.DATABASES["flips"],
                "SELECT id, status FROM flips WHERE alert_id = ? ORDER BY id DESC LIMIT 1",
                (item.get("alert_id"),),
            ) if item.get("alert_id") else None
            item["flip_id"] = flip["id"] if flip else None
            item["flip_status"] = flip["status"] if flip else None
        return {"items": items, "stats": inventory_stats(items)}
    except Exception as exc:
        return {
            "items": [],
            "stats": {
                "count": 0,
                "bought": 0,
                "preparing": 0,
                "ready": 0,
                "listed": 0,
                "attention": 0,
                "capital": 0,
                "potential_profit": 0,
            },
            "error": str(exc),
        }


def dashboard_data():
    since = (datetime.now() - timedelta(hours=24)).isoformat(timespec="seconds")
    alerts_24h = scalar(
        config.DATABASES["alerts"],
        "SELECT COUNT(*) FROM alerts WHERE created_at >= ?",
        (since,),
        0,
    )
    hot_24h = scalar(
        config.DATABASES["alerts"],
        "SELECT COUNT(*) FROM alerts WHERE created_at >= ? AND COALESCE(score, 0) >= 75",
        (since,),
        0,
    )
    watch_count = scalar(
        config.DATABASES["watchlist"],
        "SELECT COUNT(*) FROM watchlist WHERE status = 'WATCHING'",
        default=0,
    )
    active_deals = scalar(
        config.DATABASES["crm"],
        "SELECT COUNT(*) FROM deals WHERE status NOT IN ('SOLD', 'SKIPPED')",
        default=0,
    )
    realized = scalar(
        config.DATABASES["flips"],
        """
        SELECT COALESCE(SUM(COALESCE(sale_price,0) - COALESCE(purchase_price,0) - COALESCE(extra_cost,0)),0)
        FROM flips WHERE status = 'SOLD'
        """,
        default=0,
    )

    inventory = inventory_data()
    return {
        "alerts_24h": alerts_24h,
        "hot_24h": hot_24h,
        "watch_count": watch_count,
        "active_deals": active_deals,
        "realized_profit": realized,
        "queue": _queue_stats(),
        "health": health_data(),
        "inventory": inventory,
        "offers": recent_alerts(12),
    }


def watchlist_data():
    rows = query(
        config.DATABASES["watchlist"],
        "SELECT * FROM watchlist ORDER BY CASE WHEN status='WATCHING' THEN 0 ELSE 1 END, id DESC LIMIT 300",
    )
    return [dict(row) for row in rows]


def crm_board():
    rows = query(
        config.DATABASES["crm"],
        "SELECT * FROM deals ORDER BY updated_at DESC LIMIT 500",
    )
    board = {status: [] for status in config.CRM_STATUSES}
    for row in rows:
        item = dict(row)
        board.setdefault(item.get("status") or "NEW", []).append(item)
    return board


def analytics_data():
    sold = [
        dict(row)
        for row in query(
            config.DATABASES["flips"],
            "SELECT * FROM flips WHERE status='SOLD' ORDER BY sold_at DESC LIMIT 200",
        )
    ]
    open_flips = [
        dict(row)
        for row in query(
            config.DATABASES["flips"],
            "SELECT * FROM flips WHERE status!='SOLD' ORDER BY bought_at DESC LIMIT 200",
        )
    ]

    realized = 0.0
    purchase_capital = 0.0
    predicted = 0.0
    for item in sold:
        item["real_profit"] = (
            (_number(item.get("sale_price"), 0) or 0)
            - (_number(item.get("purchase_price"), 0) or 0)
            - (_number(item.get("extra_cost"), 0) or 0)
        )
        realized += item["real_profit"]
    for item in open_flips:
        purchase_capital += (_number(item.get("purchase_price"), 0) or 0) + (_number(item.get("extra_cost"), 0) or 0)
        predicted += _number(item.get("predicted_profit"), 0) or 0

    avg_profit = realized / len(sold) if sold else 0
    return {
        "sold": sold,
        "open": open_flips,
        "sold_count": len(sold),
        "open_count": len(open_flips),
        "realized_profit": realized,
        "avg_profit": avg_profit,
        "capital_open": purchase_capital,
        "predicted_open_profit": predicted,
    }


def market_data():
    try:
        from market_db import stats as market_stats
        stats = market_stats()
    except Exception:
        stats = {
            "total": scalar(config.DATABASES["market"], "SELECT COUNT(*) FROM market_offers", default=0),
            "active": scalar(config.DATABASES["market"], "SELECT COUNT(*) FROM market_offers WHERE active=1", default=0),
            "inactive": scalar(config.DATABASES["market"], "SELECT COUNT(*) FROM market_offers WHERE active=0", default=0),
            "price_changes": 0,
        }

    recent = [
        dict(row)
        for row in query(
            config.DATABASES["market"],
            "SELECT * FROM market_offers ORDER BY last_seen DESC LIMIT 100",
        )
    ]
    return {"stats": stats, "recent": recent}


def system_data():
    return {
        "health": health_data(),
        "jobs": config.JOBS,
        "bot_root": str(config.BOT_ROOT),
        "dbs": {
            name: {
                "path": str(path),
                "exists": path.exists(),
                "size": path.stat().st_size if path.exists() else 0,
            }
            for name, path in config.DATABASES.items()
        },
    }


def run_job(job_key):
    job = config.JOBS.get(job_key)
    if not job:
        raise ValueError("Nieznane zadanie")

    result = subprocess.run(
        ["systemctl", "start", job["service"]],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    return {
        "ok": result.returncode == 0,
        "code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "service": job["service"],
    }


def job_logs(job_key, lines=120):
    job = config.JOBS.get(job_key)
    if not job:
        raise ValueError("Nieznane zadanie")
    lines = max(20, min(_int(lines, 120), 500))
    result = subprocess.run(
        ["journalctl", "-u", job["service"], "-n", str(lines), "--no-pager", "-o", "short-iso"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    return {
        "ok": result.returncode == 0,
        "service": job["service"],
        "text": result.stdout.strip() or result.stderr.strip(),
    }


def _ensure_crm_table():
    conn = connect(config.DATABASES["crm"], readonly=False)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_key TEXT NOT NULL UNIQUE,
                alert_id INTEGER,
                title TEXT,
                url TEXT,
                status TEXT NOT NULL DEFAULT 'NEW',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def set_crm_status(alert_id, status):
    status = str(status or "").upper()
    if status not in config.CRM_STATUSES:
        raise ValueError("Nieprawidłowy status CRM")

    alert_row = one(config.DATABASES["alerts"], "SELECT * FROM alerts WHERE id=?", (alert_id,))
    if not alert_row:
        raise ValueError("Nie znaleziono oferty")
    alert = dict(alert_row)
    _ensure_crm_table()
    now = datetime.now().isoformat(timespec="seconds")

    conn = connect(config.DATABASES["crm"], readonly=False)
    try:
        conn.execute("""
            INSERT INTO deals (offer_key, alert_id, title, url, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(offer_key) DO UPDATE SET
                alert_id=excluded.alert_id,
                title=excluded.title,
                url=excluded.url,
                status=excluded.status,
                updated_at=excluded.updated_at
        """, (
            alert.get("offer_key"), alert.get("id"), alert.get("title"), alert.get("url"),
            status, now, now,
        ))
        conn.commit()
    finally:
        conn.close()
    return True


def _ensure_flips_table():
    conn = connect(config.DATABASES["flips"], readonly=False)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS flips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER,
                title TEXT,
                url TEXT,
                predicted_score INTEGER,
                predicted_quick_sale REAL,
                predicted_profit REAL,
                asking_price REAL,
                purchase_price REAL,
                sale_price REAL,
                extra_cost REAL DEFAULT 0,
                bought_at TEXT,
                sold_at TEXT,
                status TEXT NOT NULL DEFAULT 'BOUGHT'
            )
        """)
        conn.commit()
    finally:
        conn.close()


def buy_offer(alert_id, purchase_price, extra_cost=0):
    purchase_price = _number(purchase_price)
    extra_cost = _number(extra_cost, 0) or 0
    if purchase_price is None or purchase_price <= 0:
        raise ValueError("Cena zakupu musi być większa od zera")

    alert_row = one(config.DATABASES["alerts"], "SELECT * FROM alerts WHERE id=?", (alert_id,))
    if not alert_row:
        raise ValueError("Nie znaleziono oferty")
    alert = dict(alert_row)

    _ensure_flips_table()
    existing = one(config.DATABASES["flips"], "SELECT id FROM flips WHERE alert_id=?", (alert_id,))
    if existing:
        raise ValueError("Ta oferta jest już oznaczona jako kupiona")

    conn = connect(config.DATABASES["flips"], readonly=False)
    try:
        conn.execute("""
            INSERT INTO flips (
                alert_id, title, url, predicted_score, predicted_quick_sale, predicted_profit,
                asking_price, purchase_price, extra_cost, bought_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'BOUGHT')
        """, (
            alert_id, alert.get("title"), alert.get("url"), alert.get("score"),
            alert.get("quick_sale"), alert.get("profit"), alert.get("price"),
            purchase_price, extra_cost, datetime.now().isoformat(timespec="seconds"),
        ))
        conn.commit()
    finally:
        conn.close()

    set_crm_status(alert_id, "BOUGHT")
    return True


def sell_flip(flip_id, sale_price, extra_cost=0):
    sale_price = _number(sale_price)
    extra_cost = _number(extra_cost, 0) or 0
    if sale_price is None or sale_price <= 0:
        raise ValueError("Cena sprzedaży musi być większa od zera")

    flip_row = one(config.DATABASES["flips"], "SELECT * FROM flips WHERE id=?", (flip_id,))
    if not flip_row:
        raise ValueError("Nie znaleziono zakupu")
    flip = dict(flip_row)
    if str(flip.get("status") or "").upper() == "SOLD":
        raise ValueError("Ten komputer jest już oznaczony jako sprzedany")

    conn = connect(config.DATABASES["flips"], readonly=False)
    try:
        conn.execute("""
            UPDATE flips SET sale_price=?, extra_cost=?, sold_at=?, status='SOLD' WHERE id=?
        """, (
            sale_price, extra_cost, datetime.now().isoformat(timespec="seconds"), flip_id,
        ))
        conn.commit()
    finally:
        conn.close()

    alert_id = flip.get("alert_id")
    if alert_id:
        set_crm_status(alert_id, "SOLD")
        alert = one(config.DATABASES["alerts"], "SELECT offer_key FROM alerts WHERE id=?", (alert_id,))
        if alert and table_exists(config.DATABASES["crm"], "sale_listings"):
            execute(
                config.DATABASES["crm"],
                "UPDATE sale_listings SET status='CLOSED', updated_at=? WHERE offer_key=?",
                (datetime.now().isoformat(timespec="seconds"), alert["offer_key"]),
            )
    return True


def close_watch(item_id):
    if not table_exists(config.DATABASES["watchlist"], "watchlist"):
        raise ValueError("Watchlista nie istnieje")
    cols = columns(config.DATABASES["watchlist"], "watchlist")
    now = datetime.now().isoformat(timespec="seconds")
    if "close_reason" in cols:
        execute(
            config.DATABASES["watchlist"],
            "UPDATE watchlist SET status='CLOSED', close_reason='USER_SKIP', last_seen=? WHERE id=?",
            (now, item_id),
        )
    else:
        execute(
            config.DATABASES["watchlist"],
            "UPDATE watchlist SET status='CLOSED', last_seen=? WHERE id=?",
            (now, item_id),
        )
    return True


def _alert_for_action(alert_id):
    row = one(config.DATABASES["alerts"], "SELECT * FROM alerts WHERE id=?", (alert_id,))
    if not row:
        raise ValueError("Nie znaleziono oferty")
    return dict(row)


def add_history_entry(alert_id, kind, amount=None, note=None):
    alert = _alert_for_action(alert_id)
    from crm_history import add_entry
    add_entry(alert["offer_key"], alert_id, kind, amount, note)
    return True


def schedule_followup(alert_id, mode=None, due_at=None, note=None):
    alert = _alert_for_action(alert_id)
    from crm_followup import create_followup, schedule_from_mode

    if due_at:
        due = datetime.fromisoformat(str(due_at))
    else:
        due = schedule_from_mode(mode or "1h")

    create_followup(
        alert["offer_key"],
        alert_id,
        alert.get("title"),
        alert.get("url"),
        due.isoformat(timespec="seconds"),
        note,
    )
    return True


def update_followup(followup_id, action):
    from crm_followup import complete, cancel
    if action == "done":
        complete(followup_id)
    elif action == "cancel":
        cancel(followup_id)
    else:
        raise ValueError("Nieznana akcja follow-up")
    return True


def update_purchase_check(alert_id, item_key, status):
    alert = _alert_for_action(alert_id)
    from purchase_checklist import set_status
    set_status(alert["offer_key"], item_key, status)
    return True


def update_pickup_check(alert_id, item_key, status, note=None):
    alert = _alert_for_action(alert_id)
    from pickup_checklist import set_check
    set_check(alert["offer_key"], item_key, status, note)
    return True


def add_sale_cost(alert_id, kind, cost, note=None):
    alert = _alert_for_action(alert_id)
    from sale_prep import add_cost
    add_cost(alert["offer_key"], alert_id, kind, cost, note)
    return True


def save_sale_plan_action(alert_id, target_price, minimum_price):
    alert = _alert_for_action(alert_id)
    from sale_prep import save_plan
    save_plan(alert["offer_key"], alert_id, target_price, minimum_price)
    set_crm_status(alert_id, "PREPARING")
    return True


def mark_listing_action(alert_id, listed_price, platform="OLX"):
    alert = _alert_for_action(alert_id)
    from sale_listing_tracker import mark_listed
    mark_listed(alert["offer_key"], alert_id, listed_price, platform)
    set_crm_status(alert_id, "LISTED")
    return True


def change_listing_price_action(alert_id, new_price, reason="MANUAL"):
    alert = _alert_for_action(alert_id)
    from sale_listing_tracker import change_price
    change_price(alert["offer_key"], new_price, reason)
    return True
