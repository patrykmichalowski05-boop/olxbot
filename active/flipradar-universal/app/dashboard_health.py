import re
import sqlite3
import subprocess
from datetime import datetime

from flask import Blueprint, jsonify, render_template_string


health_bp = Blueprint("health_dashboard", __name__)

FAST_DB = "/opt/olx-bot/fast.db"
MARKET_DB = "/opt/olx-bot/market.db"
WATCHLIST_DB = "/opt/olx-bot/watchlist.db"


MODULES = [
    ("FAST", "olx-fast.timer", "olx-fast.service"),
    ("DEEP", "olx-deep.timer", "olx-deep.service"),
    ("BUNDLE", "olx-bundle.timer", "olx-bundle.service"),
    ("NEAR MISS", "olx-near-miss.timer", "olx-near-miss.service"),
    ("MARKET", "olx-market.timer", "olx-market.service"),
    ("LIFECYCLE", "olx-lifecycle.timer", "olx-lifecycle.service"),
    (
        "WATCHLIST",
        "olx-watchlist-lifecycle.timer",
        "olx-watchlist-lifecycle.service",
    ),
    ("WATCHDOG", "olx-watchdog.timer", "olx-watchdog.service"),
    (
        "DAILY REPORT",
        "olx-daily-report.timer",
        "olx-daily-report.service",
    ),
]


def command(args):
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def active(unit):
    return command(
        ["systemctl", "is-active", unit]
    ) or "unknown"


def service_result(unit):
    return command(
        [
            "systemctl",
            "show",
            unit,
            "--property=Result",
            "--value",
        ]
    ) or "unknown"


def last_start(unit):
    return command(
        [
            "systemctl",
            "show",
            unit,
            "--property=ExecMainStartTimestamp",
            "--value",
        ]
    ) or "-"


def error_count(unit, since):
    logs = command(
        [
            "journalctl",
            "-u",
            unit,
            "--since",
            since,
            "--no-pager",
            "--output=cat",
        ]
    )

    if not logs:
        return 0

    count = 0

    for line in logs.splitlines():
        low = line.lower()

        if (
            "traceback" in low
            or "[deep exception]" in low
            or "[fast feed error]" in low
            or "[search error]" in low
            or "[detail error]" in low
        ):
            count += 1

    return count


def errors_24h(unit):
    return error_count(
        unit,
        "24 hours ago",
    )


def errors_1h(unit):
    return error_count(
        unit,
        "1 hour ago",
    )


def query(db, sql):
    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql).fetchall()
        conn.close()
        return rows
    except Exception:
        return []


def queue_stats():
    result = {
        "pending": 0,
        "processing": 0,
        "done": 0,
        "failed": 0,
    }

    rows = query(
        FAST_DB,
        """
        SELECT status, COUNT(*) count
        FROM queue
        GROUP BY status
        """,
    )

    for row in rows:
        key = str(row["status"]).lower()

        if key in result:
            result[key] = row["count"]

    return result


def watchlist_stats():
    result = {
        "watching": 0,
        "triggered": 0,
        "stale": 0,
        "closed": 0,
    }

    rows = query(
        WATCHLIST_DB,
        """
        SELECT status, COUNT(*) count
        FROM watchlist
        GROUP BY status
        """,
    )

    for row in rows:
        key = str(row["status"]).lower()

        if key in result:
            result[key] = row["count"]

    return result


def market_stats():
    result = {
        "total": 0,
        "active": 0,
        "inactive": 0,
        "price_changes": 0,
        "age_hours": None,
    }

    rows = query(
        MARKET_DB,
        """
        SELECT
            COUNT(*) total,

            COALESCE(
                SUM(
                    CASE WHEN active = 1
                    THEN 1 ELSE 0 END
                ),
                0
            ) active,

            COALESCE(
                SUM(
                    CASE WHEN active = 0
                    THEN 1 ELSE 0 END
                ),
                0
            ) inactive,

            COALESCE(
                SUM(price_changes),
                0
            ) price_changes,

            MAX(last_seen) last_seen

        FROM market_offers
        """,
    )

    if not rows:
        return result

    row = rows[0]

    result["total"] = row["total"] or 0
    result["active"] = row["active"] or 0
    result["inactive"] = row["inactive"] or 0
    result["price_changes"] = row["price_changes"] or 0

    if row["last_seen"]:
        try:
            last_seen = datetime.fromisoformat(
                str(row["last_seen"])
            )

            if last_seen.tzinfo:
                now = datetime.now(last_seen.tzinfo)
            else:
                now = datetime.now()

            result["age_hours"] = round(
                (
                    now - last_seen
                ).total_seconds()
                / 3600,
                1,
            )
        except Exception:
            pass

    return result


def collect_health():
    modules = []
    active_timers = 0
    total_errors = 0
    score = 100
    critical = False

    for name, timer, service in MODULES:
        timer_state = active(timer)
        result = service_result(service)
        errors = errors_24h(service)
        recent_errors = errors_1h(service)

        total_errors += errors

        if timer_state == "active":
            active_timers += 1
        else:
            score -= 12
            critical = True

        if result == "failed":
            score -= 15
            critical = True

        if timer_state != "active" or result == "failed":
            status = "ERROR"
        elif recent_errors > 0:
            status = "WARNING"
        else:
            status = "OK"

        modules.append(
            {
                "name": name,
                "timer": timer_state,
                "result": result,
                "errors": errors,
                "recent_errors": recent_errors,
                "last_start": last_start(service),
                "status": status,
            }
        )

    queue = queue_stats()
    market = market_stats()
    watchlist = watchlist_stats()

    if queue["pending"] >= 40:
        score -= 15
        critical = True
    elif queue["pending"] >= 15:
        score -= 5

    if queue["failed"] >= 10:
        score -= 20
        critical = True
    elif queue["failed"] >= 3:
        score -= 7

    age = market["age_hours"]

    if age is None:
        score -= 8
    elif age >= 36:
        score -= 20
        critical = True
    elif age >= 18:
        score -= 8

    if total_errors >= 20:
        score -= 10
    elif total_errors >= 5:
        score -= 5
    elif total_errors > 0:
        score -= 2

    score = max(
        0,
        min(
            100,
            score,
        ),
    )

    if critical:
        status = "ERROR"
    elif score >= 90:
        status = "OK"
    else:
        status = "WARNING"

    return {
        "score": score,
        "status": status,
        "modules": modules,
        "active_timers": active_timers,
        "total_timers": len(MODULES),
        "errors": total_errors,
        "queue": queue,
        "market": market,
        "watchlist": watchlist,
        "now": datetime.now().strftime(
            "%d.%m.%Y %H:%M:%S"
        ),
    }


HTML = """
<!doctype html>
<html lang="pl">

<head>
<meta charset="utf-8">
<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>Bot Health</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #0d1014;
    color: #edf0f3;
    font-family: Arial, sans-serif;
}

.container {
    max-width: 1400px;
    margin: auto;
    padding: 24px;
}

a {
    color: #74b9ff;
    text-decoration: none;
}

.top {
    display: flex;
    justify-content: space-between;
}

.health {
    margin-top: 25px;
    padding: 25px;
    border-radius: 16px;
    background: #171b20;
    border: 1px solid #293038;
}

.big {
    font-size: 48px;
    font-weight: bold;
}

.ok {
    color: #66d98b;
}

.warning {
    color: #ffd166;
}

.error {
    color: #ff6b6b;
}

.grid {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
    margin-top: 25px;
}

.card {
    background: #171b20;
    border: 1px solid #293038;
    border-radius: 13px;
    padding: 17px;
}

.label {
    color: #8d97a2;
    font-size: 12px;
}

.value {
    font-size: 27px;
    font-weight: bold;
    margin-top: 7px;
}

.section {
    margin-top: 30px;
}

.modules {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(250px, 1fr));
    gap: 12px;
}

.module {
    background: #171b20;
    border: 1px solid #293038;
    border-radius: 13px;
    padding: 15px;
}

.small {
    margin-top: 8px;
    color: #8d97a2;
    font-size: 12px;
    line-height: 1.6;
}

.dot {
    display: inline-block;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    margin-right: 8px;
}

.dot-ok {
    background: #66d98b;
}

.dot-warning {
    background: #ffd166;
}

.dot-error {
    background: #ff6b6b;
}

@media(max-width: 700px) {

    .container {
        padding: 12px;
    }

    .top {
        display: block;
    }

}

</style>
</head>


<body>

<div class="container">

<div class="top">

<div>

<h1>
BOT HEALTH
</h1>

<div class="label">
OLX Flip Hunter
</div>

</div>

<div>

<a href="/">
Dashboard
</a>

&nbsp; | &nbsp;

<a href="/watchlist">
Watchlista
</a>

&nbsp; | &nbsp;

<a href="/analytics">
Analityka
</a>

</div>

</div>


<div class="health">

<div class="
big
{% if status == 'OK' %}
ok
{% elif status == 'WARNING' %}
warning
{% else %}
error
{% endif %}
">

{{ score }}%

</div>

<h2>

{% if status == "OK" %}
SYSTEM OK
{% elif status == "WARNING" %}
SYSTEM WARNING
{% else %}
SYSTEM ERROR
{% endif %}

</h2>

<div class="label">
Ostatnia kontrola: {{ now }}
</div>

</div>


<div class="grid">

<div class="card">

<div class="label">
Timery
</div>

<div class="value">
{{ active_timers }}/{{ total_timers }}
</div>

</div>


<div class="card">

<div class="label">
Bledy 24h
</div>

<div class="value">
{{ errors }}
</div>

</div>


<div class="card">

<div class="label">
Queue pending
</div>

<div class="value">
{{ queue.pending }}
</div>

</div>


<div class="card">

<div class="label">
Queue failed
</div>

<div class="value">
{{ queue.failed }}
</div>

</div>


<div class="card">

<div class="label">
Market
</div>

<div class="value">
{{ market.total }}
</div>

</div>


<div class="card">

<div class="label">
Market age
</div>

<div class="value">

{% if market.age_hours is not none %}
{{ market.age_hours }} h
{% else %}
-
{% endif %}

</div>

</div>


<div class="card">

<div class="label">
Watchlista
</div>

<div class="value">
{{ watchlist.watching }}
</div>

</div>


<div class="card">

<div class="label">
KUP TERAZ
</div>

<div class="value">
{{ watchlist.triggered }}
</div>

</div>

</div>


<div class="section">

<h2>
Moduly
</h2>

<div class="modules">

{% for module in modules %}

<div class="module">

<div>

{% if module.status == "OK" %}

<span class="dot dot-ok"></span>

{% elif module.status == "WARNING" %}

<span class="dot dot-warning"></span>

{% else %}

<span class="dot dot-error"></span>

{% endif %}

<b>
{{ module.name }}
</b>

</div>


<div class="small">

Timer:
{{ module.timer }}

<br>

Result:
{{ module.result }}

<br>

Errors 24h:
{{ module.errors }}

<br>

Last start:
<br>
{{ module.last_start }}

</div>

</div>

{% endfor %}

</div>

</div>

</div>


<script>

setTimeout(
    function () {
        location.reload();
    },
    30000
);

</script>

</body>

</html>
"""


@health_bp.route("/health")
def health_page():
    data = collect_health()

    return render_template_string(
        HTML,
        **data,
    )


@health_bp.route("/api/health")
def health_api():
    return jsonify(
        collect_health()
    )
