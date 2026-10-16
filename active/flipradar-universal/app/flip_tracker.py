import argparse
import sqlite3
from datetime import datetime


ALERT_DB = "/opt/olx-bot/alert_history.db"
RESULT_DB = "/opt/olx-bot/flip_results.db"


# ============================================================
# DB
# ============================================================

def connect():

    conn = sqlite3.connect(
        RESULT_DB
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = connect()

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
    conn.close()


# ============================================================
# HELPERS
# ============================================================

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

        return str(value)


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


# ============================================================
# ALERTS
# ============================================================

def show_alerts(
    limit=20,
):

    conn = sqlite3.connect(
        ALERT_DB
    )

    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT
            id,
            score,
            price,
            profit,
            quick_sale,
            title,
            created_at

        FROM alerts

        ORDER BY id DESC

        LIMIT ?
    """, (
        limit,
    )).fetchall()

    conn.close()

    print()
    print(
        "=" * 100
    )

    print(
        "OSTATNIE ALERTY"
    )

    print(
        "=" * 100
    )

    for row in rows:

        print(
            f"ID {row['id']:4} | "
            f"Score {str(row['score'] or '-'):>3} | "
            f"Cena {money(row['price']):>11} | "
            f"Zysk {money(row['profit']):>11}"
        )

        print(
            f"       {row['title']}"
        )

        print()


# ============================================================
# BUY
# ============================================================

def buy(
    alert_id,
    purchase_price,
    extra_cost=0,
):

    alert = get_alert(
        alert_id
    )

    if alert is None:

        print(
            "Nie znaleziono alertu:",
            alert_id
        )

        return

    conn = connect()

    existing = conn.execute("""
        SELECT id
        FROM flips

        WHERE
            alert_id = ?
            AND status = 'BOUGHT'
    """, (
        alert_id,
    )).fetchone()

    if existing:

        print(
            "Ten alert jest już oznaczony jako kupiony."
        )

        conn.close()

        return

    cursor = conn.execute("""
        INSERT INTO flips (
            alert_id,

            title,
            url,

            predicted_score,
            predicted_quick_sale,
            predicted_profit,

            asking_price,
            purchase_price,
            extra_cost,

            bought_at,
            status
        )

        VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, 'BOUGHT'
        )
    """, (
        alert_id,

        alert["title"],
        alert["url"],

        alert["score"],
        alert["quick_sale"],
        alert["profit"],

        alert["price"],
        purchase_price,
        extra_cost,

        datetime.now().isoformat(
            timespec="seconds"
        ),
    ))

    conn.commit()

    flip_id = (
        cursor.lastrowid
    )

    conn.close()

    print()
    print(
        "✅ ZAPISANO ZAKUP"
    )

    print(
        "Flip ID:",
        flip_id
    )

    print(
        "Komputer:",
        alert["title"]
    )

    print(
        "Cena OLX:",
        money(
            alert["price"]
        )
    )

    print(
        "Kupiono:",
        money(
            purchase_price
        )
    )

    print(
        "Prognoza sprzedaży:",
        money(
            alert["quick_sale"]
        )
    )


# ============================================================
# SELL
# ============================================================

def sell(
    flip_id,
    sale_price,
    extra_cost=None,
):

    conn = connect()

    row = conn.execute("""
        SELECT *
        FROM flips
        WHERE id = ?
    """, (
        flip_id,
    )).fetchone()

    if row is None:

        print(
            "Nie znaleziono flipu:",
            flip_id
        )

        conn.close()

        return

    if row["status"] == "SOLD":

        print(
            "Ten komputer jest już oznaczony jako sprzedany."
        )

        conn.close()

        return

    current_extra = (
        row["extra_cost"]
        or 0
    )

    if extra_cost is not None:

        current_extra = (
            extra_cost
        )

    conn.execute("""
        UPDATE flips

        SET
            sale_price = ?,
            extra_cost = ?,
            sold_at = ?,
            status = 'SOLD'

        WHERE id = ?
    """, (
        sale_price,
        current_extra,
        datetime.now().isoformat(
            timespec="seconds"
        ),
        flip_id,
    ))

    conn.commit()
    conn.close()

    actual_profit = (
        float(sale_price)
        -
        float(row["purchase_price"])
        -
        float(current_extra)
    )

    prediction_error = None

    if row[
        "predicted_quick_sale"
    ] is not None:

        prediction_error = (
            float(sale_price)
            -
            float(
                row[
                    "predicted_quick_sale"
                ]
            )
        )

    print()
    print(
        "✅ ZAPISANO SPRZEDAŻ"
    )

    print(
        row["title"]
    )

    print(
        "Kupiono:",
        money(
            row["purchase_price"]
        )
    )

    print(
        "Dodatkowe koszty:",
        money(
            current_extra
        )
    )

    print(
        "Sprzedano:",
        money(
            sale_price
        )
    )

    print(
        "REALNY ZYSK:",
        money(
            actual_profit
        )
    )

    if prediction_error is not None:

        print(
            "Błąd prognozy ceny:",
            money(
                prediction_error
            )
        )


# ============================================================
# OPEN FLIPS
# ============================================================

def show_open():

    conn = connect()

    rows = conn.execute("""
        SELECT *
        FROM flips

        WHERE status = 'BOUGHT'

        ORDER BY id DESC
    """).fetchall()

    conn.close()

    print()
    print(
        "=" * 100
    )

    print(
        "AKTUALNIE KUPIONE / NIESPRZEDANE"
    )

    print(
        "=" * 100
    )

    if not rows:

        print(
            "Brak otwartych flipów."
        )

        return

    for row in rows:

        print(
            f"Flip ID {row['id']} | "
            f"Kupiono: "
            f"{money(row['purchase_price'])} | "
            f"Prognoza: "
            f"{money(row['predicted_quick_sale'])}"
        )

        print(
            row["title"]
        )

        print()


# ============================================================
# REPORT
# ============================================================

def report():

    conn = connect()

    rows = conn.execute("""
        SELECT *
        FROM flips

        WHERE status = 'SOLD'

        ORDER BY sold_at DESC
    """).fetchall()

    conn.close()

    print()
    print(
        "=" * 100
    )

    print(
        "RAPORT REALNYCH FLIPÓW"
    )

    print(
        "=" * 100
    )

    if not rows:

        print(
            "Brak zakończonych flipów."
        )

        return

    real_profits = []
    prediction_errors = []
    percentage_errors = []

    for row in rows:

        actual_profit = (
            float(
                row["sale_price"]
            )
            -
            float(
                row["purchase_price"]
            )
            -
            float(
                row["extra_cost"]
                or 0
            )
        )

        real_profits.append(
            actual_profit
        )

        predicted = (
            row[
                "predicted_quick_sale"
            ]
        )

        error = None

        if predicted:

            error = (
                float(
                    row["sale_price"]
                )
                -
                float(
                    predicted
                )
            )

            prediction_errors.append(
                abs(error)
            )

            percentage_errors.append(
                abs(error)
                /
                float(predicted)
                *
                100
            )

        print()

        print(
            f"#{row['id']} "
            f"{row['title']}"
        )

        print(
            "Kupiono:",
            money(
                row["purchase_price"]
            )
        )

        print(
            "Sprzedano:",
            money(
                row["sale_price"]
            )
        )

        print(
            "Realny zysk:",
            money(
                actual_profit
            )
        )

        print(
            "Bot przewidywał:",
            money(
                predicted
            )
        )

        if error is not None:

            print(
                "Błąd ceny:",
                money(
                    error
                )
            )

    total_profit = sum(
        real_profits
    )

    avg_profit = (
        total_profit
        /
        len(
            real_profits
        )
    )

    print()
    print(
        "-" * 100
    )

    print(
        "SPRZEDANE:",
        len(rows)
    )

    print(
        "ŁĄCZNY REALNY ZYSK:",
        money(
            total_profit
        )
    )

    print(
        "ŚREDNI ZYSK / PC:",
        money(
            avg_profit
        )
    )

    if prediction_errors:

        mae = (
            sum(
                prediction_errors
            )
            /
            len(
                prediction_errors
            )
        )

        print(
            "ŚREDNI BŁĄD WYCENY:",
            money(
                mae
            )
        )

    if percentage_errors:

        mape = (
            sum(
                percentage_errors
            )
            /
            len(
                percentage_errors
            )
        )

        accuracy = max(
            0,
            100 - mape
        )

        print(
            "TRAFNOŚĆ WYCEN:",
            f"{accuracy:.1f}%"
        )


# ============================================================
# CLI
# ============================================================

def main():

    init_db()

    parser = argparse.ArgumentParser(
        description=(
            "OLX Flip Hunter "
            "- tracker realnych zakupów"
        )
    )

    sub = (
        parser.add_subparsers(
            dest="command"
        )
    )

    alerts_parser = (
        sub.add_parser(
            "alerts"
        )
    )

    alerts_parser.add_argument(
        "--limit",
        type=int,
        default=20,
    )

    buy_parser = (
        sub.add_parser(
            "buy"
        )
    )

    buy_parser.add_argument(
        "alert_id",
        type=int,
    )

    buy_parser.add_argument(
        "price",
        type=float,
    )

    buy_parser.add_argument(
        "--extra",
        type=float,
        default=0,
    )

    sell_parser = (
        sub.add_parser(
            "sell"
        )
    )

    sell_parser.add_argument(
        "flip_id",
        type=int,
    )

    sell_parser.add_argument(
        "price",
        type=float,
    )

    sell_parser.add_argument(
        "--extra",
        type=float,
        default=None,
    )

    sub.add_parser(
        "open"
    )

    sub.add_parser(
        "report"
    )

    args = (
        parser.parse_args()
    )

    if args.command == "alerts":

        show_alerts(
            args.limit
        )

    elif args.command == "buy":

        buy(
            args.alert_id,
            args.price,
            args.extra,
        )

    elif args.command == "sell":

        sell(
            args.flip_id,
            args.price,
            args.extra,
        )

    elif args.command == "open":

        show_open()

    elif args.command == "report":

        report()

    else:

        parser.print_help()


if __name__ == "__main__":
    main()
