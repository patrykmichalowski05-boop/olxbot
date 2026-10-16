import sqlite3
from datetime import datetime

from telegram_notifier import (
    send_message,
)


DB_FILE = (
    "/opt/olx-bot/alert_history.db"
)


def money(value):

    if value is None:
        return "brak"

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

        return str(
            value
        )


def get_today():

    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = sqlite3.Row

    today = (
        datetime.now()
        .strftime(
            "%Y-%m-%d"
        )
    )

    rows = conn.execute("""
        SELECT *
        FROM alerts

        WHERE
            created_at LIKE ?

        ORDER BY
            COALESCE(score, 0) DESC,
            COALESCE(profit, 0) DESC
    """, (
        today + "%",
    )).fetchall()

    conn.close()

    return rows


def main():

    rows = get_today()

    if not rows:

        print(
            "[DAILY REPORT] "
            "Brak dzisiejszych alertów."
        )

        return

    total = len(
        rows
    )

    profits = [
        row["profit"]
        for row in rows
        if row["profit"] is not None
    ]

    scores = [
        row["score"]
        for row in rows
        if row["score"] is not None
    ]

    avg_profit = (
        sum(profits)
        /
        len(profits)
        if profits
        else 0
    )

    avg_score = (
        sum(scores)
        /
        len(scores)
        if scores
        else 0
    )

    hot = sum(
        1
        for row in rows
        if (
            row["score"]
            is not None
            and
            row["score"] >= 80
        )
    )

    top = sum(
        1
        for row in rows
        if (
            row["score"]
            is not None
            and
            row["score"] >= 90
        )
    )

    bundles = sum(
        1
        for row in rows
        if row["bundle"]
    )

    price_drops = sum(
        1
        for row in rows
        if str(
            row["trigger"]
            or ""
        ).upper()
        in (
            "PRICE_DROP",
            "BUNDLE_PRICE_DROP",
        )
    )

    message = (
        "<b>📊 OLX FLIP HUNTER — RAPORT DNIA</b>\n\n"

        f"Data: "
        f"<b>{datetime.now().strftime('%d.%m.%Y')}</b>\n\n"

        "<b>PODSUMOWANIE</b>\n"

        f"Znalezione okazje: "
        f"<b>{total}</b>\n"

        f"Średni Deal Score: "
        f"<b>{avg_score:.0f}/100</b>\n"

        f"Średni potencjalny zysk: "
        f"<b>{money(avg_profit)}</b>\n"

        f"🔥 Score 80+: "
        f"{hot}\n"

        f"🚨 Score 90+: "
        f"{top}\n"

        f"🎮 Zestawy / bundle: "
        f"{bundles}\n"

        f"📉 Obniżki ceny: "
        f"{price_drops}\n"
    )

    message += (
        "\n<b>🏆 TOP 5 DZISIAJ</b>\n"
    )

    for index, row in enumerate(
        rows[:5],
        start=1,
    ):

        score = (
            row["score"]
            if row["score"]
            is not None
            else 0
        )

        message += (
            "\n"
            f"<b>{index}. "
            f"{score}/100</b>\n"

            f"{row['title']}\n"

            f"Cena: "
            f"{money(row['price'])}\n"

            f"Zysk: "
            f"<b>{money(row['profit'])}</b>\n"
        )

        if row["roi"] is not None:

            message += (
                f"ROI: "
                f"{row['roi']:.0f}%\n"
            )

        if row["url"]:

            message += (
                f'<a href="{row["url"]}">'
                "Otwórz OLX"
                "</a>\n"
            )

    sent = send_message(
        message
    )

    if sent:

        print(
            "[DAILY REPORT] "
            "Raport wysłany."
        )

    else:

        print(
            "[DAILY REPORT] "
            "Błąd wysyłki."
        )


if __name__ == "__main__":
    main()
