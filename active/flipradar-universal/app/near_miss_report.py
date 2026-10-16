import html
import os
import sqlite3

from datetime import datetime, timedelta

from telegram_notifier import (
    send_message,
)


DECISION_DB = (
    "/opt/olx-bot/decision_log.db"
)

STATE_DB = (
    "/opt/olx-bot/near_miss.db"
)


MIN_PROFIT = int(
    os.getenv(
        "NEAR_MISS_MIN_PROFIT",
        "250",
    )
)

MAX_PROFIT = int(
    os.getenv(
        "NEAR_MISS_MAX_PROFIT",
        "399",
    )
)

LOOKBACK_HOURS = int(
    os.getenv(
        "NEAR_MISS_LOOKBACK_HOURS",
        "3",
    )
)

MAX_RESULTS = int(
    os.getenv(
        "NEAR_MISS_MAX_RESULTS",
        "10",
    )
)


# ============================================================
# HELPERS
# ============================================================

def esc(value):

    if value is None:
        return "brak"

    return html.escape(
        str(value)
    )


def money(value):

    if value is None:
        return "brak"

    try:

        return (
            f"{int(round(float(value))):,}"
            .replace(",", " ")
            + " zł"
        )

    except Exception:

        return esc(value)


# ============================================================
# STATE DB
# ============================================================

def init_state_db():

    conn = sqlite3.connect(
        STATE_DB
    )

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sent (

            decision_id INTEGER PRIMARY KEY,

            offer_id TEXT,

            sent_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def was_sent(
    decision_id,
):

    conn = sqlite3.connect(
        STATE_DB
    )

    row = conn.execute("""
        SELECT 1
        FROM sent
        WHERE decision_id = ?
    """, (
        decision_id,
    )).fetchone()

    conn.close()

    return (
        row is not None
    )


def mark_sent(
    decision_id,
    offer_id,
):

    conn = sqlite3.connect(
        STATE_DB
    )

    conn.execute("""
        INSERT OR IGNORE INTO sent (
            decision_id,
            offer_id,
            sent_at
        )
        VALUES (
            ?,
            ?,
            ?
        )
    """, (
        decision_id,
        offer_id,
        datetime.now().isoformat(
            timespec="seconds"
        ),
    ))

    conn.commit()
    conn.close()


# ============================================================
# LOAD OFFERS
# ============================================================

def get_candidates():

    since = (
        datetime.now()
        -
        timedelta(
            hours=LOOKBACK_HOURS
        )
    ).isoformat(
        timespec="seconds"
    )

    conn = sqlite3.connect(
        DECISION_DB
    )

    conn.row_factory = (
        sqlite3.Row
    )

    rows = conn.execute("""
        SELECT
            id,
            created_at,
            offer_id,
            decision,
            reason,
            stage,

            purchase_price,
            quick_sale,
            profit,

            cpu,
            gpu,

            valuation_source,
            confidence,

              url AS offer_url

        FROM decisions

        WHERE
            created_at >= ?

            AND decision = 'REJECT'

            AND profit
                BETWEEN ? AND ?

        ORDER BY
            profit DESC,
            id DESC

        LIMIT ?
    """, (
        since,
        MIN_PROFIT,
        MAX_PROFIT,
        MAX_RESULTS * 3,
    )).fetchall()

    conn.close()

    result = []

    seen_offers = set()

    for row in rows:

        if row[
            "offer_id"
        ] in seen_offers:

            continue

        if was_sent(
            row["id"]
        ):

            continue

        seen_offers.add(
            row["offer_id"]
        )

        result.append(
            row
        )

        if (
            len(result)
            >= MAX_RESULTS
        ):

            break

    return result


# ============================================================
# NEGOTIATION TARGET
# ============================================================

def negotiation_target(
    row,
):

    purchase_price = (
        row["purchase_price"]
    )

    profit = (
        row["profit"]
    )

    if (
        purchase_price is None
        or
        profit is None
    ):

        return None

    # Chcemy dojść do minimum 450 zł,
    # czyli zostawić trochę marginesu
    # ponad próg 400.

    missing_profit = (
        450
        -
        int(profit)
    )

    if missing_profit <= 0:

        return int(
            purchase_price
        )

    target = (
        int(purchase_price)
        -
        missing_profit
    )

    if target <= 0:

        return None

    return target


# ============================================================
# BUILD MESSAGE
# ============================================================

def build_message(
    rows,
):

    message = (
        "<b>OLX FLIP HUNTER — PRAWIE OKAZJE</b>\n\n"

        "Oferty odrzucone przez główny filtr, "
        "ale blisko progu opłacalności.\n\n"
    )

    for index, row in enumerate(
        rows,
        start=1,
    ):

        target = (
            negotiation_target(
                row
            )
        )

        message += (
            f"<b>{index}. "
            f"{esc(row['cpu'])} + "
            f"{esc(row['gpu'])}</b>\n"
        )

        message += (
            f"Cena zakupu: "
            f"{money(row['purchase_price'])}\n"

            f"Szybka sprzedaż: "
            f"{money(row['quick_sale'])}\n"

            f"Obecny zysk: "
            f"<b>{money(row['profit'])}</b>\n"
        )

        if target is not None:

            reduction = (
                int(row["purchase_price"])
                -
                target
            )

            message += (
                f"Cena docelowa po negocjacji: "
                f"<b>{money(target)}</b>\n"

                f"Potrzebna obniżka: "
                f"{money(reduction)}\n"
            )

        message += (
            f"Źródło wyceny: "
            f"{esc(row['valuation_source'])}\n"

            f"Pewność: "
            f"{esc(row['confidence'])}\n"
        )

        if row[
            "offer_url"
        ]:

            message += (
                f'<a href="{esc(row["offer_url"])}">'
                "Otwórz ogłoszenie OLX"
                "</a>\n"
            )

        message += "\n"

    message += (
        "<i>To nie są automatycznie zaakceptowane okazje. "
        "Warto je sprawdzić pod kątem negocjacji ceny.</i>"
    )

    return message


# ============================================================
# MAIN
# ============================================================

def main():

    init_state_db()

    rows = get_candidates()

    if not rows:

        print(
            "Brak nowych ofert blisko progu."
        )

        return

    message = build_message(
        rows
    )

    print(
        message
    )

    ok = send_message(
        message
    )

    if not ok:

        raise SystemExit(
            "Nie udało się wysłać Telegrama."
        )

    for row in rows:

        mark_sent(
            row["id"],
            row["offer_id"],
        )

    print(
        "Wysłano:",
        len(rows)
    )


if __name__ == "__main__":

    main()
