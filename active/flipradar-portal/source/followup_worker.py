import html
import sqlite3
from datetime import datetime

from telegram_notifier import (
    send_message,
)

from crm_followup import (
    init_db,
)


DB_FILE = "/opt/olx-bot/deal_crm.db"


def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def run():
    init_db()

    now = datetime.now().isoformat(
        timespec="seconds"
    )

    conn = connect()

    rows = conn.execute("""
        SELECT *
        FROM followups

        WHERE
            status = 'ACTIVE'
            AND notified_at IS NULL
            AND due_at <= ?

        ORDER BY due_at ASC
    """, (
        now,
    )).fetchall()


    print(
        "[FOLLOWUP] due:",
        len(rows)
    )


    for row in rows:

        title = html.escape(
            str(
                row["title"]
                or "Oferta OLX"
            )
        )

        note = html.escape(
            str(
                row["note"]
                or
                "Ponowny kontakt ze sprzedającym"
            )
        )

        message = (
            "⏰ <b>FOLLOW-UP CRM</b>\n\n"
            f"<b>{title}</b>\n\n"
            f"📝 {note}\n"
            f"⏱ Termin: {row['due_at']}\n"
        )

        if row["url"]:

            safe_url = html.escape(
                str(
                    row["url"]
                ),
                quote=True,
            )

            message += (
                "\n"
                f'<a href="{safe_url}">'
                "👉 OTWÓRZ OLX"
                "</a>"
            )


        sent = send_message(
            message
        )


        if sent:

            conn.execute("""
                UPDATE followups

                SET notified_at = ?

                WHERE id = ?
            """, (
                datetime.now().isoformat(
                    timespec="seconds"
                ),

                row["id"],
            ))

            conn.commit()

            print(
                "[FOLLOWUP] wysłano:",
                row["title"]
            )


    conn.close()


if __name__ == "__main__":
    run()
