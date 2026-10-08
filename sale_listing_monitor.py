import html
import sqlite3

from sale_listing_tracker import (
    price_advice,
)

from telegram_notifier import (
    send_message,
)


CRM_DB = "/opt/olx-bot/deal_crm.db"
ALERT_DB = "/opt/olx-bot/alert_history.db"


def crm_connect():
    conn = sqlite3.connect(CRM_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = crm_connect()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS
        sale_price_notifications (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            offer_key TEXT NOT NULL,
            suggested_price REAL NOT NULL,

            created_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(
                offer_key,
                suggested_price
            )
        )
    """)

    conn.commit()
    conn.close()


def alert_data(
    alert_id,
):
    conn = sqlite3.connect(ALERT_DB)
    conn.row_factory = sqlite3.Row

    row = conn.execute("""
        SELECT
            title,
            url

        FROM alerts

        WHERE id = ?
    """, (
        alert_id,
    )).fetchone()

    conn.close()

    return row


def already_notified(
    conn,
    offer_key,
    suggested_price,
):
    row = conn.execute("""
        SELECT id

        FROM sale_price_notifications

        WHERE
            offer_key = ?
            AND suggested_price = ?

        LIMIT 1
    """, (
        offer_key,
        suggested_price,
    )).fetchone()

    return row is not None


def save_notification(
    conn,
    offer_key,
    suggested_price,
):
    conn.execute("""
        INSERT OR IGNORE INTO
        sale_price_notifications (
            offer_key,
            suggested_price
        )

        VALUES (?, ?)
    """, (
        offer_key,
        suggested_price,
    ))

    conn.commit()


def run():
    init_db()

    conn = crm_connect()

    listings = conn.execute("""
        SELECT
            sl.*,
            sp.minimum_price

        FROM sale_listings sl

        LEFT JOIN sale_plans sp
            ON sp.offer_key =
               sl.offer_key

        WHERE sl.status = 'ACTIVE'

        ORDER BY sl.listed_at ASC
    """).fetchall()

    print(
        "[SALE MONITOR] active:",
        len(listings),
    )

    sent = 0

    for listing in listings:

        advice = price_advice(
            listing,
            listing["minimum_price"],
        )

        if advice["status"] != "REDUCE":
            continue

        suggested = float(
            advice["suggested_price"]
        )

        if already_notified(
            conn,
            listing["offer_key"],
            suggested,
        ):
            continue

        alert = alert_data(
            listing["alert_id"]
        )

        title = (
            alert["title"]
            if alert
            else "Komputer"
        )

        safe_title = html.escape(
            str(title)
        )

        current = float(
            listing["listed_price"]
        )

        minimum = (
            float(listing["minimum_price"])
            if listing["minimum_price"]
            is not None
            else None
        )

        message = (
            "📉 <b>SUGEROWANA OBNIŻKA</b>\n\n"
            f"<b>{safe_title}</b>\n\n"
            f"📅 Wystawiony: "
            f"{advice['days']} dni\n"
            f"💰 Aktualna cena: "
            f"{current:.0f} zł\n"
            f"➡️ Sugerowana: "
            f"{suggested:.0f} zł\n"
        )

        if minimum is not None:
            message += (
                f"🛑 Minimum: "
                f"{minimum:.0f} zł\n"
            )

        message += (
            f"\n📉 Obniżka: "
            f"-{advice['discount']:.0f} zł"
        )

        ok = send_message(
            message
        )

        if ok:

            save_notification(
                conn,
                listing["offer_key"],
                suggested,
            )

            sent += 1

            print(
                "[SALE MONITOR] alert:",
                title,
                "->",
                suggested,
            )

    conn.close()

    print(
        "[SALE MONITOR] sent:",
        sent,
    )


if __name__ == "__main__":
    run()
