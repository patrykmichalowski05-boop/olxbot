import sqlite3
from datetime import datetime, timedelta


DB_FILE = "/opt/olx-bot/decision_log.db"


def connect():

    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = sqlite3.Row

    return conn


def separator():

    print()
    print("=" * 90)


def money(value):

    if value is None:
        return "-"

    try:
        return f"{round(float(value))} zł"
    except:
        return str(value)


def percentage(
    part,
    total
):

    if not total:
        return 0

    return round(
        part / total * 100,
        1
    )


# ============================================================
# PODSUMOWANIE
# ============================================================

def summary(days=30):

    cutoff = (
        datetime.now()
        -
        timedelta(days=days)
    ).isoformat(
        timespec="seconds"
    )

    with connect() as conn:

        total = conn.execute("""
            SELECT COUNT(*)
            FROM decisions
            WHERE created_at >= ?
        """, (
            cutoff,
        )).fetchone()[0]

        unique_offers = conn.execute("""
            SELECT COUNT(
                DISTINCT offer_id
            )
            FROM decisions
            WHERE created_at >= ?
        """, (
            cutoff,
        )).fetchone()[0]

        accepted = conn.execute("""
            SELECT COUNT(*)
            FROM decisions
            WHERE
                created_at >= ?
                AND decision = 'ACCEPT'
        """, (
            cutoff,
        )).fetchone()[0]

        rejected = conn.execute("""
            SELECT COUNT(*)
            FROM decisions
            WHERE
                created_at >= ?
                AND decision = 'REJECT'
        """, (
            cutoff,
        )).fetchone()[0]

        errors = conn.execute("""
            SELECT COUNT(*)
            FROM decisions
            WHERE
                created_at >= ?
                AND decision = 'ERROR'
        """, (
            cutoff,
        )).fetchone()[0]

        avg_profit = conn.execute("""
            SELECT AVG(profit)
            FROM decisions
            WHERE
                created_at >= ?
                AND profit IS NOT NULL
        """, (
            cutoff,
        )).fetchone()[0]

        avg_accept_profit = conn.execute("""
            SELECT AVG(profit)
            FROM decisions
            WHERE
                created_at >= ?
                AND decision = 'ACCEPT'
                AND profit IS NOT NULL
        """, (
            cutoff,
        )).fetchone()[0]

    separator()

    print(
        f"DECISION REPORT — OSTATNIE {days} DNI"
    )

    separator()

    print(
        f"Decyzji:               {total}"
    )

    print(
        f"Unikalnych ofert:       {unique_offers}"
    )

    print(
        f"Zaakceptowane:          "
        f"{accepted} "
        f"({percentage(accepted, total)}%)"
    )

    print(
        f"Odrzucone:              "
        f"{rejected} "
        f"({percentage(rejected, total)}%)"
    )

    print(
        f"Błędy:                  "
        f"{errors} "
        f"({percentage(errors, total)}%)"
    )

    print(
        f"Średni policzony zysk:  "
        f"{money(avg_profit)}"
    )

    print(
        f"Średni zysk ACCEPT:     "
        f"{money(avg_accept_profit)}"
    )

    return cutoff


# ============================================================
# POWODY ODRZUTÓW
# ============================================================

def rejection_reasons(
    cutoff
):

    separator()

    print(
        "POWODY ODRZUTÓW"
    )

    separator()

    with connect() as conn:

        rows = conn.execute("""
            SELECT
                reason,
                stage,
                COUNT(*) AS count

            FROM decisions

            WHERE
                created_at >= ?
                AND decision = 'REJECT'

            GROUP BY
                reason,
                stage

            ORDER BY
                count DESC
        """, (
            cutoff,
        )).fetchall()

    if not rows:

        print(
            "Brak odrzuconych ofert."
        )

        return

    total = sum(
        row["count"]
        for row in rows
    )

    for row in rows:

        print(
            f"{row['count']:>4} | "
            f"{percentage(row['count'], total):>5}% | "
            f"{row['stage']:<12} | "
            f"{row['reason']}"
        )


# ============================================================
# ETAPY
# ============================================================

def stages(
    cutoff
):

    separator()

    print(
        "DECYZJE WG ETAPU"
    )

    separator()

    with connect() as conn:

        rows = conn.execute("""
            SELECT
                stage,
                decision,
                COUNT(*) AS count

            FROM decisions

            WHERE created_at >= ?

            GROUP BY
                stage,
                decision

            ORDER BY
                count DESC
        """, (
            cutoff,
        )).fetchall()

    for row in rows:

        print(
            f"{row['count']:>4} | "
            f"{row['decision']:<7} | "
            f"{row['stage']}"
        )


# ============================================================
# OFERTY BLISKO PROGU
# ============================================================

def near_misses(
    cutoff,
    limit=15
):

    separator()

    print(
        "NAJLEPSZE ODRZUCONE OFERTY "
        "BLISKO PROGU 400 ZŁ"
    )

    separator()

    with connect() as conn:

        rows = conn.execute("""
            SELECT
                created_at,
                offer_id,

                purchase_price,

                cpu,
                gpu,
                ram,

                quick_sale,
                profit,

                valuation_source,
                confidence,

                reason,

                url

            FROM decisions

            WHERE
                created_at >= ?

                AND decision = 'REJECT'

                AND profit IS NOT NULL

                AND profit < 400

            ORDER BY
                profit DESC

            LIMIT ?
        """, (
            cutoff,
            limit
        )).fetchall()

    if not rows:

        print(
            "Brak odrzuconych ofert "
            "z policzonym zyskiem."
        )

        return

    for row in rows:

        print()

        print(
            f"{row['profit']:>4} zł | "
            f"zakup {money(row['purchase_price'])} | "
            f"{row['cpu']} | "
            f"{row['gpu']} | "
            f"{row['ram']} GB"
        )

        print(
            f"        sprzedaż: "
            f"{money(row['quick_sale'])}"
        )

        print(
            f"        źródło: "
            f"{row['valuation_source']} | "
            f"{row['confidence']}"
        )

        print(
            f"        powód: "
            f"{row['reason']}"
        )

        print(
            f"        {row['url']}"
        )


# ============================================================
# ACCEPT
# ============================================================

def accepted_flips(
    cutoff,
    limit=15
):

    separator()

    print(
        "NAJLEPSZE ZAAKCEPTOWANE FLIPY"
    )

    separator()

    with connect() as conn:

        rows = conn.execute("""
            SELECT
                created_at,
                offer_id,

                purchase_price,

                cpu,
                gpu,
                ram,

                quick_sale,
                profit,

                valuation_source,
                confidence,

                ai_adjustment_percent,

                url

            FROM decisions

            WHERE
                created_at >= ?
                AND decision = 'ACCEPT'

            ORDER BY
                profit DESC

            LIMIT ?
        """, (
            cutoff,
            limit
        )).fetchall()

    if not rows:

        print(
            "Brak zaakceptowanych flipów."
        )

        return

    for row in rows:

        print()

        print(
            f"+{row['profit']} zł | "
            f"zakup {money(row['purchase_price'])} | "
            f"{row['cpu']} | "
            f"{row['gpu']} | "
            f"{row['ram']} GB"
        )

        print(
            f"        sprzedaż: "
            f"{money(row['quick_sale'])}"
        )

        print(
            f"        źródło: "
            f"{row['valuation_source']} | "
            f"{row['confidence']}"
        )

        print(
            f"        AI: "
            f"{row['ai_adjustment_percent']}%"
        )

        print(
            f"        {row['url']}"
        )


# ============================================================
# ŹRÓDŁA WYCENY
# ============================================================

def valuation_sources(
    cutoff
):

    separator()

    print(
        "ŹRÓDŁA WYCENY"
    )

    separator()

    with connect() as conn:

        rows = conn.execute("""
            SELECT
                valuation_source,
                confidence,

                COUNT(*) AS count,

                AVG(profit) AS avg_profit,

                AVG(exact_samples) AS avg_exact,

                AVG(similar_samples) AS avg_similar

            FROM decisions

            WHERE
                created_at >= ?
                AND valuation_source IS NOT NULL

            GROUP BY
                valuation_source,
                confidence

            ORDER BY
                count DESC
        """, (
            cutoff,
        )).fetchall()

    for row in rows:

        print(
            f"{row['count']:>4} | "
            f"{str(row['valuation_source']):<25} | "
            f"{str(row['confidence']):<14} | "
            f"avg profit "
            f"{money(row['avg_profit'])} | "
            f"exact "
            f"{round(row['avg_exact'] or 0, 1)} | "
            f"similar "
            f"{round(row['avg_similar'] or 0, 1)}"
        )


# ============================================================
# AI
# ============================================================

def ai_stats(
    cutoff
):

    separator()

    print(
        "AI — STATYSTYKI"
    )

    separator()

    with connect() as conn:

        analyzed = conn.execute("""
            SELECT COUNT(*)
            FROM decisions
            WHERE
                created_at >= ?
                AND ai_condition IS NOT NULL
        """, (
            cutoff,
        )).fetchone()[0]

        avg_adjustment = conn.execute("""
            SELECT AVG(
                ai_adjustment_percent
            )
            FROM decisions
            WHERE
                created_at >= ?
                AND ai_adjustment_percent
                    IS NOT NULL
        """, (
            cutoff,
        )).fetchone()[0]

        negative = conn.execute("""
            SELECT COUNT(*)
            FROM decisions
            WHERE
                created_at >= ?
                AND ai_adjustment_percent < 0
        """, (
            cutoff,
        )).fetchone()[0]

        spec_ai = conn.execute("""
            SELECT COUNT(*)
            FROM decisions
            WHERE
                created_at >= ?
                AND spec_ai_used = 1
        """, (
            cutoff,
        )).fetchone()[0]

    print(
        f"Analiz stanu AI:        {analyzed}"
    )

    print(
        f"Średnia korekta AI:     "
        f"{round(avg_adjustment, 2) if avg_adjustment is not None else '-'}%"
    )

    print(
        f"Ujemnych korekt:        {negative}"
    )

    print(
        f"Spec recovery użyte:    {spec_ai}"
    )


# ============================================================
# CPU / GPU
# ============================================================

def hardware_stats(
    cutoff
):

    separator()

    print(
        "NAJCZĘŚCIEJ ANALIZOWANE GPU"
    )

    separator()

    with connect() as conn:

        rows = conn.execute("""
            SELECT
                gpu,
                COUNT(*) AS count,

                AVG(profit) AS avg_profit

            FROM decisions

            WHERE
                created_at >= ?
                AND gpu IS NOT NULL

            GROUP BY gpu

            ORDER BY
                count DESC

            LIMIT 15
        """, (
            cutoff,
        )).fetchall()

    for row in rows:

        print(
            f"{row['count']:>4} | "
            f"{str(row['gpu']):<20} | "
            f"avg profit "
            f"{money(row['avg_profit'])}"
        )


# ============================================================
# SANITY CAP
# ============================================================

def sanity_stats(
    cutoff
):

    separator()

    print(
        "SANITY CAP"
    )

    separator()

    with connect() as conn:

        total = conn.execute("""
            SELECT COUNT(*)
            FROM decisions
            WHERE
                created_at >= ?
                AND quick_sale IS NOT NULL
        """, (
            cutoff,
        )).fetchone()[0]

        capped = conn.execute("""
            SELECT COUNT(*)
            FROM decisions
            WHERE
                created_at >= ?
                AND sanity_cap_applied = 1
        """, (
            cutoff,
        )).fetchone()[0]

        rows = conn.execute("""
            SELECT
                offer_id,
                cpu,
                gpu,

                quick_sale_before_cap,
                sanity_cap,
                quick_sale

            FROM decisions

            WHERE
                created_at >= ?
                AND sanity_cap_applied = 1

            ORDER BY id DESC

            LIMIT 10
        """, (
            cutoff,
        )).fetchall()

    print(
        f"Wyceny z finalną ceną: {total}"
    )

    print(
        f"Cap użyty:             "
        f"{capped} "
        f"({percentage(capped, total)}%)"
    )

    for row in rows:

        print()

        print(
            f"{row['cpu']} | "
            f"{row['gpu']}"
        )

        print(
            f"    przed: "
            f"{money(row['quick_sale_before_cap'])}"
        )

        print(
            f"    cap:   "
            f"{money(row['sanity_cap'])}"
        )

        print(
            f"    final: "
            f"{money(row['quick_sale'])}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    cutoff = summary(
        days=30
    )

    rejection_reasons(
        cutoff
    )

    stages(
        cutoff
    )

    near_misses(
        cutoff
    )

    accepted_flips(
        cutoff
    )

    valuation_sources(
        cutoff
    )

    ai_stats(
        cutoff
    )

    hardware_stats(
        cutoff
    )

    sanity_stats(
        cutoff
    )

    separator()

    print(
        "KONIEC RAPORTU"
    )

    separator()


if __name__ == "__main__":
    main()
