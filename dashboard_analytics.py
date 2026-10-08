import sqlite3
from datetime import datetime

from flask import (
    Blueprint,
    render_template_string,
)


analytics_bp = Blueprint(
    "analytics",
    __name__,
)


FLIP_DB = (
    "/opt/olx-bot/flip_results.db"
)


HTML = """
<!doctype html>
<html lang="pl">

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>
Analityka — OLX Flip Hunter
</title>

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
    color: #75baff;
    text-decoration: none;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 25px;
}

.grid {
    display: grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(190px, 1fr)
        );
    gap: 14px;
}

.card {
    background: #171b20;
    border: 1px solid #292f36;
    border-radius: 14px;
    padding: 18px;
}

.label {
    color: #8d97a2;
    font-size: 13px;
}

.value {
    font-size: 27px;
    font-weight: bold;
    margin-top: 7px;
}

.good {
    color: #66d98b;
}

.warn {
    color: #ffd166;
}

.section {
    margin-top: 30px;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th,
td {
    text-align: left;
    padding: 11px;
    border-bottom: 1px solid #292f36;
}

th {
    color: #8d97a2;
    font-size: 12px;
}

.chart {
    margin-top: 15px;
}

.chart-row {
    display: grid;
    grid-template-columns:
        90px 1fr 100px;
    gap: 12px;
    align-items: center;
    margin-bottom: 12px;
}

.bar-bg {
    height: 22px;
    background: #252b32;
    border-radius: 7px;
    overflow: hidden;
}

.bar {
    height: 100%;
    background: #4078df;
    border-radius: 7px;
}

.profit {
    color: #66d98b;
}

.loss {
    color: #ff7373;
}

.empty {
    color: #8d97a2;
    padding: 25px 0;
}

@media(max-width: 700px) {

    .container {
        padding: 12px;
    }

    .header {
        display: block;
    }

    .header div:last-child {
        margin-top: 10px;
    }

    .chart-row {
        grid-template-columns:
            70px 1fr 75px;
    }

}

</style>

</head>


<body>

<div class="container">

<div class="header">

<div>

<h1>
📊 Analityka Flipów
</h1>

<div class="label">
OLX Flip Hunter V3
</div>

</div>

<div>

<a href="/">
← Dashboard
</a>

</div>

</div>


<div class="grid">

<div class="card">

<div class="label">
Zysk łącznie
</div>

<div class="value good">
{{ money(total_profit) }}
</div>

</div>


<div class="card">

<div class="label">
Zysk w tym miesiącu
</div>

<div class="value good">
{{ money(month_profit) }}
</div>

</div>


<div class="card">

<div class="label">
Sprzedane PC
</div>

<div class="value">
{{ sold_count }}
</div>

</div>


<div class="card">

<div class="label">
Średni zysk / PC
</div>

<div class="value">
{{ money(avg_profit) }}
</div>

</div>


<div class="card">

<div class="label">
Najlepszy flip
</div>

<div class="value good">
{{ money(best_profit) }}
</div>

</div>


<div class="card">

<div class="label">
Trafność wycen
</div>

<div class="value">
{% if accuracy is not none %}
{{ "%.1f"|format(accuracy) }}%
{% else %}
-
{% endif %}
</div>

</div>


<div class="card">

<div class="label">
Kapitał w magazynie
</div>

<div class="value warn">
{{ money(inventory_cost) }}
</div>

</div>


<div class="card">

<div class="label">
PC na stanie
</div>

<div class="value">
{{ inventory_count }}
</div>

</div>


<div class="card">

<div class="label">
Potencjalny zysk magazynu
</div>

<div class="value good">
{{ money(inventory_profit) }}
</div>

</div>


<div class="card">

<div class="label">
Średni czas sprzedaży
</div>

<div class="value">
{% if avg_days is not none %}
{{ "%.1f"|format(avg_days) }} dni
{% else %}
-
{% endif %}
</div>

</div>

</div>


<div class="section">

<h2>
📅 Zysk miesięczny
</h2>

<div class="card">

{% if months %}

<div class="chart">

{% for month in months %}

<div class="chart-row">

<div>
{{ month.label }}
</div>

<div class="bar-bg">

<div
    class="bar"
    style="
        width:
        {{ month.width }}%;
    "
>
</div>

</div>

<div class="
{% if month.profit >= 0 %}
profit
{% else %}
loss
{% endif %}
">

{{ money(month.profit) }}

</div>

</div>

{% endfor %}

</div>

{% else %}

<div class="empty">
Brak danych sprzedażowych.
</div>

{% endif %}

</div>

</div>


<div class="section">

<h2>
🏆 Najlepsze zakończone flipy
</h2>

<div class="card">

{% if top_flips %}

<table>

<tr>
<th>Komputer</th>
<th>Kupiono</th>
<th>Sprzedano</th>
<th>Koszty</th>
<th>Zysk</th>
<th>Prognoza</th>
<th>Błąd wyceny</th>
</tr>

{% for row in top_flips %}

<tr>

<td>
{{ row.title }}
</td>

<td>
{{ money(row.purchase_price) }}
</td>

<td>
{{ money(row.sale_price) }}
</td>

<td>
{{ money(row.extra_cost) }}
</td>

<td class="profit">
<b>
{{ money(row.real_profit) }}
</b>
</td>

<td>
{{ money(row.predicted_quick_sale) }}
</td>

<td>

{% if row.price_error is not none %}

{% if row.price_error >= 0 %}
+
{% endif %}

{{ money(row.price_error) }}

{% else %}
-
{% endif %}

</td>

</tr>

{% endfor %}

</table>

{% else %}

<div class="empty">
Nie masz jeszcze prawdziwych zakończonych flipów.
</div>

{% endif %}

</div>

</div>


<div class="section">

<h2>
📦 Aktualny magazyn
</h2>

<div class="card">

{% if inventory %}

<table>

<tr>
<th>Komputer</th>
<th>Kupiono</th>
<th>Koszty</th>
<th>Prognoza sprzedaży</th>
<th>Potencjalny zysk</th>
<th>W magazynie</th>
</tr>

{% for row in inventory %}

<tr>

<td>
{{ row.title }}
</td>

<td>
{{ money(row.purchase_price) }}
</td>

<td>
{{ money(row.extra_cost) }}
</td>

<td>
{{ money(row.predicted_quick_sale) }}
</td>

<td class="profit">
{{ money(row.expected_profit) }}
</td>

<td>
{{ row.days_held }} dni
</td>

</tr>

{% endfor %}

</table>

{% else %}

<div class="empty">
Brak niesprzedanych komputerów.
</div>

{% endif %}

</div>

</div>


</div>

</body>
</html>
"""


def connect():

    conn = sqlite3.connect(
        FLIP_DB
    )

    conn.row_factory = sqlite3.Row

    return conn


def money(value):

    if value is None:
        return "-"

    try:

        value = int(
            round(
                float(value)
            )
        )

        return (
            f"{value:,}"
            .replace(",", " ")
            + " zł"
        )

    except Exception:

        return "-"


@analytics_bp.route(
    "/analytics"
)
def analytics():

    conn = connect()

    sold = conn.execute("""
        SELECT
            *,

            (
                sale_price
                -
                purchase_price
                -
                COALESCE(
                    extra_cost,
                    0
                )
            ) AS real_profit,

            (
                sale_price
                -
                predicted_quick_sale
            ) AS price_error

        FROM flips

        WHERE status = 'SOLD'
    """).fetchall()


    inventory_raw = conn.execute("""
        SELECT
            *,

            (
                predicted_quick_sale
                -
                purchase_price
                -
                COALESCE(
                    extra_cost,
                    0
                )
            ) AS expected_profit

        FROM flips

        WHERE status = 'BOUGHT'

        ORDER BY bought_at DESC
    """).fetchall()


    conn.close()


    total_profit = 0
    month_profit = 0
    sold_count = len(
        sold
    )

    profits = []
    errors = []
    hold_days = []

    month_key = (
        datetime.now()
        .strftime(
            "%Y-%m"
        )
    )


    month_map = {}


    for row in sold:

        profit = float(
            row["real_profit"]
            or 0
        )

        total_profit += (
            profit
        )

        profits.append(
            profit
        )


        sold_at = row[
            "sold_at"
        ]

        if sold_at:

            sold_month = str(
                sold_at
            )[:7]

            month_map[
                sold_month
            ] = (
                month_map.get(
                    sold_month,
                    0
                )
                +
                profit
            )

            if (
                sold_month
                ==
                month_key
            ):

                month_profit += (
                    profit
                )


        predicted = row[
            "predicted_quick_sale"
        ]

        actual = row[
            "sale_price"
        ]

        if (
            predicted
            and
            actual
        ):

            predicted = float(
                predicted
            )

            errors.append(
                abs(
                    float(actual)
                    -
                    predicted
                )
                /
                predicted
                *
                100
            )


        try:

            bought = (
                datetime.fromisoformat(
                    row[
                        "bought_at"
                    ]
                )
            )

            sold_date = (
                datetime.fromisoformat(
                    row[
                        "sold_at"
                    ]
                )
            )

            days = (
                sold_date
                -
                bought
            ).total_seconds() / 86400

            hold_days.append(
                max(
                    0,
                    days
                )
            )

        except Exception:

            pass


    avg_profit = (
        total_profit
        /
        sold_count

        if sold_count
        else 0
    )


    best_profit = (
        max(profits)

        if profits
        else 0
    )


    accuracy = None

    if errors:

        accuracy = max(
            0,
            100
            -
            (
                sum(errors)
                /
                len(errors)
            )
        )


    avg_days = None

    if hold_days:

        avg_days = (
            sum(hold_days)
            /
            len(hold_days)
        )


    inventory = []

    inventory_cost = 0
    inventory_profit = 0


    for row in inventory_raw:

        purchase = float(
            row[
                "purchase_price"
            ]
            or 0
        )

        extra = float(
            row[
                "extra_cost"
            ]
            or 0
        )

        expected = float(
            row[
                "expected_profit"
            ]
            or 0
        )

        inventory_cost += (
            purchase
            +
            extra
        )

        inventory_profit += (
            expected
        )


        try:

            bought_at = (
                datetime.fromisoformat(
                    row[
                        "bought_at"
                    ]
                )
            )

            days_held = (
                datetime.now()
                -
                bought_at
            ).days

        except Exception:

            days_held = 0


        item = dict(
            row
        )

        item[
            "days_held"
        ] = (
            days_held
        )

        inventory.append(
            item
        )


    max_month_profit = max(
        [
            abs(value)
            for value
            in month_map.values()
        ]
        or [1]
    )


    months = []

    for key in sorted(
        month_map.keys()
    )[-12:]:

        profit = (
            month_map[
                key
            ]
        )

        width = (
            abs(profit)
            /
            max_month_profit
            *
            100
        )

        months.append({
            "label":
                key,

            "profit":
                profit,

            "width":
                max(
                    2,
                    round(
                        width,
                        1
                    )
                ),
        })


    top_flips = sorted(
        sold,
        key=lambda row:
            float(
                row[
                    "real_profit"
                ]
                or 0
            ),
        reverse=True,
    )[:10]


    return render_template_string(
        HTML,

        money=money,

        total_profit=
            total_profit,

        month_profit=
            month_profit,

        sold_count=
            sold_count,

        avg_profit=
            avg_profit,

        best_profit=
            best_profit,

        accuracy=
            accuracy,

        inventory=
            inventory,

        inventory_count=
            len(
                inventory
            ),

        inventory_cost=
            inventory_cost,

        inventory_profit=
            inventory_profit,

        avg_days=
            avg_days,

        months=
            months,

        top_flips=
            top_flips,
    )
