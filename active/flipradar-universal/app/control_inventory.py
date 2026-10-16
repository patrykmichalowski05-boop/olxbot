import sqlite3

from sale_prep import summary as sale_prep_summary
from sale_listing_tracker import (
    get_listing,
    price_advice,
)


CRM_DB = "/opt/olx-bot/deal_crm.db"


ACTIVE_STATUSES = {
    "BOUGHT",
    "PREPARING",
    "READY_TO_SELL",
    "LISTED",
}


def connect():
    conn = sqlite3.connect(CRM_DB)
    conn.row_factory = sqlite3.Row
    return conn


def collect_inventory():
    conn = connect()

    deals = conn.execute("""
        SELECT *
        FROM deals

        WHERE status IN (
            'BOUGHT',
            'PREPARING',
            'READY_TO_SELL',
            'LISTED'
        )

        ORDER BY updated_at DESC
    """).fetchall()

    conn.close()

    result = []

    for deal in deals:

        prep = sale_prep_summary(
            deal["offer_key"],
            deal["alert_id"],
            None,
        )

        listing = get_listing(
            deal["offer_key"]
        )

        advice = price_advice(
            listing,
            prep.get(
                "minimum_price"
            ),
        )

        total = float(
            prep.get(
                "total_investment"
            )
            or 0
        )

        target = prep.get(
            "target_price"
        )

        minimum = prep.get(
            "minimum_price"
        )

        listed_price = (
            float(
                listing["listed_price"]
            )
            if listing
            else None
        )

        projected_profit = (
            float(target) - total
            if target is not None
            else None
        )

        minimum_profit = (
            float(minimum) - total
            if minimum is not None
            else None
        )


        # ==========================================
        # PRIORYTET / UWAGA
        # ==========================================

        attention = "OK"
        attention_label = "Bez akcji"

        if (
            deal["status"] == "LISTED"
            and advice.get("status") == "REDUCE"
        ):
            attention = "PRICE"
            attention_label = (
                "Rozważ obniżkę ceny"
            )

        elif (
            deal["status"] == "LISTED"
            and advice.get("status") == "MINIMUM"
        ):
            attention = "MINIMUM"
            attention_label = (
                "Cena minimalna osiągnięta"
            )

        elif deal["status"] == "BOUGHT":
            attention = "PREP"
            attention_label = (
                "Rozpocznij przygotowanie"
            )

        elif deal["status"] == "PREPARING":
            attention = "PREP"
            attention_label = (
                "Dokończ przygotowanie"
            )

        elif deal["status"] == "READY_TO_SELL":
            attention = "LIST"
            attention_label = (
                "Wystaw komputer"
            )


        result.append({
            "offer_key":
                deal["offer_key"],

            "alert_id":
                deal["alert_id"],

            "title":
                deal["title"],

            "url":
                deal["url"],

            "status":
                deal["status"],

            "purchase_price":
                prep.get(
                    "purchase_price"
                ),

            "prep_cost":
                prep.get(
                    "prep_cost"
                ),

            "total_investment":
                total,

            "target_price":
                target,

            "minimum_price":
                minimum,

            "listed_price":
                listed_price,

            "projected_profit":
                projected_profit,

            "minimum_profit":
                minimum_profit,

            "days_listed":
                advice.get(
                    "days",
                    0,
                ),

            "suggested_price":
                advice.get(
                    "suggested_price"
                ),

            "price_advice_status":
                advice.get(
                    "status"
                ),

            "attention":
                attention,

            "attention_label":
                attention_label,
        })


    # Najpierw rzeczy wymagające działania.
    priority = {
        "PRICE": 1,
        "PREP": 2,
        "LIST": 3,
        "MINIMUM": 4,
        "OK": 5,
    }

    result.sort(
        key=lambda x: (
            priority.get(
                x["attention"],
                99,
            ),
            -x["days_listed"],
        )
    )

    return result


def inventory_stats(
    inventory,
):
    stats = {
        "count": len(inventory),
        "bought": 0,
        "preparing": 0,
        "ready": 0,
        "listed": 0,
        "attention": 0,
        "capital": 0,
        "potential_profit": 0,
    }

    for item in inventory:

        status = item[
            "status"
        ]

        if status == "BOUGHT":
            stats["bought"] += 1

        elif status == "PREPARING":
            stats["preparing"] += 1

        elif status == "READY_TO_SELL":
            stats["ready"] += 1

        elif status == "LISTED":
            stats["listed"] += 1

        if item["attention"] != "OK":
            stats["attention"] += 1

        stats["capital"] += float(
            item["total_investment"]
            or 0
        )

        stats["potential_profit"] += float(
            item["projected_profit"]
            or 0
        )

    return stats
