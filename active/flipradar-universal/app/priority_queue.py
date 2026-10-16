import sqlite3
from datetime import datetime


DB_FILE = "/opt/olx-bot/fast.db"


def now():
    return datetime.now().isoformat(
        timespec="seconds"
    )


def calculate_priority(
    mode,
    trigger,
    price,
    title,
):
    """
    Im wyższa liczba, tym wcześniej DEEP analizuje ofertę.
    """

    score = 0

    trigger = str(
        trigger or ""
    ).upper()

    mode = str(
        mode or ""
    ).upper()

    title = str(
        title or ""
    ).lower()

    # ========================================================
    # TRIGGER
    # ========================================================

    if trigger == "BUNDLE_PRICE_DROP":
        score += 100

    elif trigger == "PRICE_DROP":
        score += 90

    elif trigger == "BUNDLE_DISCOVERY":
        score += 70

    elif trigger == "NEW":
        score += 50

    else:
        score += 40

    # ========================================================
    # LOCAL
    # ========================================================

    if mode == "LOCAL":
        score += 20

    # ========================================================
    # INTERESUJĄCE GPU
    # ========================================================

    gpu_markers = [
        "rtx 3070",
        "rtx 3080",
        "rtx 4060",
        "rtx 4060 ti",
        "rtx 4070",
        "rtx 4070 super",
        "rtx 4070 ti",
        "rtx 5060",
        "rtx 5060 ti",
        "rx 6700 xt",
        "rx 6750 xt",
        "rx 6800",
        "rx 7700 xt",
        "rx 7800 xt",
    ]

    if any(
        marker in title
        for marker in gpu_markers
    ):
        score += 10

    # ========================================================
    # DOBRE CPU
    # ========================================================

    cpu_markers = [
        "ryzen 5 5600",
        "ryzen 5 5600x",
        "ryzen 7 5700",
        "ryzen 7 5800",
        "i5 12400",
        "i5 13400",
        "i5 13600",
        "i5 14400",
    ]

    if any(
        marker in title
        for marker in cpu_markers
    ):
        score += 5

    # ========================================================
    # NISKA CENA
    # ========================================================

    try:
        price = int(price)

        if price <= 1500:
            score += 10

        elif price <= 2200:
            score += 5

    except Exception:
        pass

    return score


def claim_next_priority():
    """
    Pobiera najlepszy PENDING według priority score,
    a nie najstarszy rekord.
    """

    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = sqlite3.Row

    try:

        conn.execute(
            "BEGIN IMMEDIATE"
        )

        rows = conn.execute("""
            SELECT *
            FROM queue
            WHERE status = 'PENDING'
        """).fetchall()

        if not rows:

            conn.commit()
            return None

        ranked = []

        for row in rows:

            score = calculate_priority(
                mode=row["mode"],
                trigger=row["trigger"],
                price=row["price"],
                title=row["title"],
            )

            ranked.append(
                (
                    score,
                    -row["id"],
                    row,
                )
            )

        ranked.sort(
            reverse=True,
            key=lambda x: (
                x[0],
                x[1],
            )
        )

        score, _, best = ranked[0]

        timestamp = now()

        conn.execute("""
            UPDATE queue

            SET
                status = 'PROCESSING',
                attempts = attempts + 1,
                updated_at = ?,
                last_error = NULL

            WHERE id = ?
        """, (
            timestamp,
            best["id"],
        ))

        conn.commit()

        result = conn.execute("""
            SELECT *
            FROM queue
            WHERE id = ?
        """, (
            best["id"],
        )).fetchone()

        print(
            "[QUEUE PRIORITY] "
            f"job={result['id']} | "
            f"score={score} | "
            f"trigger={result['trigger']} | "
            f"mode={result['mode']} | "
            f"{result['title']}"
        )

        return result

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()


if __name__ == "__main__":

    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT *
        FROM queue
        WHERE status = 'PENDING'
    """).fetchall()

    conn.close()

    results = []

    for row in rows:

        score = calculate_priority(
            row["mode"],
            row["trigger"],
            row["price"],
            row["title"],
        )

        results.append(
            (
                score,
                row["id"],
                row["trigger"],
                row["mode"],
                row["price"],
                row["title"],
            )
        )

    results.sort(
        reverse=True
    )

    print()
    print(
        "PRIORYTET KOLEJKI"
    )
    print(
        "=" * 100
    )

    for item in results[:30]:

        print(
            f"{item[0]:3} | "
            f"job {item[1]:4} | "
            f"{item[2]:20} | "
            f"{item[3]:6} | "
            f"{item[4]} zł | "
            f"{item[5]}"
        )
