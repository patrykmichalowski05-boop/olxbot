import sqlite3
import time
from datetime import datetime

from deal_crm import (
    ensure_deal,
    set_status,
    status_for_offer,
)

from crm_history import (
    add_entry,
)

from pickup_checklist import (
    ITEMS,
    set_check,
    get_checklist,
    readiness,
)

from sale_prep import (
    add_cost,
    save_plan,
    summary as sale_summary,
)

from sale_listing_tracker import (
    mark_listed,
    get_listing,
    change_price,
    price_history,
    close_listing,
)


ROOT = "/opt/olx-bot"

ALERT_DB = f"{ROOT}/alert_history.db"
FLIP_DB = f"{ROOT}/flip_results.db"
CRM_DB = f"{ROOT}/deal_crm.db"

stamp = int(time.time())

OFFER_KEY = f"V1_TEST_{stamp}"
TITLE = "V1 TEST Ryzen 5 5600 RTX 3070 16GB 1TB"
URL = f"https://example.invalid/v1-test-{stamp}"

alert_id = None
flip_id = None


def banner(text):
    print()
    print("=" * 55)
    print(text)
    print("=" * 55)


def table_exists(conn, table):
    return conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table,),
    ).fetchone() is not None


def columns(conn, table):
    conn.row_factory = sqlite3.Row

    return conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()


def generic_insert(
    db_path,
    table,
    values,
):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    info = columns(
        conn,
        table,
    )

    if not info:
        conn.close()

        raise RuntimeError(
            f"Brak tabeli {table}"
        )

    insert_cols = []
    insert_values = []

    for col in info:

        name = col["name"]
        col_type = str(
            col["type"] or ""
        ).upper()

        # INTEGER PRIMARY KEY zwykle jest
        # automatycznie generowany przez SQLite.
        if (
            col["pk"]
            and "INT" in col_type
            and name not in values
        ):
            continue

        if name in values:

            value = values[name]

        elif col["dflt_value"] is not None:

            # Pomijamy -> SQLite użyje DEFAULT.
            continue

        elif not col["notnull"]:

            value = None

        else:

            # Awaryjna wartość tylko dla pól
            # wymaganych bez DEFAULT.
            if any(
                x in col_type
                for x in (
                    "INT",
                    "REAL",
                    "NUM",
                    "DEC",
                    "FLOAT",
                    "DOUBLE",
                )
            ):
                value = 0
            else:
                value = "V1_TEST"

        insert_cols.append(
            name
        )

        insert_values.append(
            value
        )

    placeholders = ",".join(
        "?"
        for _ in insert_cols
    )

    sql = (
        f"INSERT INTO {table} "
        f"({','.join(insert_cols)}) "
        f"VALUES ({placeholders})"
    )

    cur = conn.execute(
        sql,
        insert_values,
    )

    row_id = cur.lastrowid

    conn.commit()
    conn.close()

    return row_id


def create_test_alert():
    conn = sqlite3.connect(
        ALERT_DB
    )

    conn.row_factory = sqlite3.Row

    if not table_exists(
        conn,
        "alerts",
    ):
        conn.close()

        raise RuntimeError(
            "Brak tabeli alerts"
        )

    source = conn.execute(
        """
        SELECT *
        FROM alerts
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    info = columns(
        conn,
        "alerts",
    )

    conn.close()

    values = {}

    if source:

        for col in info:

            name = col["name"]

            if name in source.keys():
                values[name] = source[name]

    # Nie kopiujemy ID.
    values.pop(
        "id",
        None,
    )

    overrides = {
        "offer_key": OFFER_KEY,
        "title": TITLE,
        "url": URL,

        "price": 1650,
        "quick_sale": 2450,
        "profit": 800,
        "score": 88,
        "roi": 48,

        "total_cost": 1650,

        "mode": "V1_TEST",
        "trigger": "INTEGRATION_TEST",

        "bundle": 0,

        "created_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),
    }

    values.update(
        overrides
    )

    return generic_insert(
        ALERT_DB,
        "alerts",
        values,
    )


def create_test_flip():
    now = datetime.now().isoformat(
        timespec="seconds"
    )

    values = {
        "alert_id": alert_id,
        "offer_key": OFFER_KEY,
        "title": TITLE,
        "url": URL,

        "purchase_price": 1600,
        "buy_price": 1600,

        "extra_cost": 50,
        "purchase_extra": 50,

        "predicted_price": 2450,
        "predicted_sale_price": 2450,
        "predicted_profit": 800,

        "status": "BOUGHT",

        "created_at": now,
        "bought_at": now,
        "purchase_date": now,
    }

    return generic_insert(
        FLIP_DB,
        "flips",
        values,
    )


def sell_test_flip():
    conn = sqlite3.connect(
        FLIP_DB
    )

    conn.row_factory = sqlite3.Row

    names = {
        row["name"]
        for row in columns(
            conn,
            "flips",
        )
    }

    updates = {}

    for candidate in (
        "sale_price",
        "sold_price",
        "selling_price",
    ):
        if candidate in names:
            updates[
                candidate
            ] = 2450

    for candidate in (
        "sale_extra_cost",
        "sell_extra_cost",
    ):
        if candidate in names:
            updates[
                candidate
            ] = 0

    if "status" in names:
        updates[
            "status"
        ] = "SOLD"

    now = datetime.now().isoformat(
        timespec="seconds"
    )

    for candidate in (
        "sold_at",
        "sale_date",
    ):
        if candidate in names:
            updates[
                candidate
            ] = now

    if not updates:
        conn.close()

        raise RuntimeError(
            "Nie znalazłem pól sprzedaży w flips"
        )

    sql = (
        "UPDATE flips SET "
        +
        ", ".join(
            f"{name}=?"
            for name in updates
        )
        +
        " WHERE id=?"
    )

    conn.execute(
        sql,
        list(updates.values())
        +
        [flip_id],
    )

    conn.commit()
    conn.close()


def cleanup_db(
    db_path,
    tables,
):
    conn = sqlite3.connect(
        db_path
    )

    conn.row_factory = sqlite3.Row

    for table in tables:

        if not table_exists(
            conn,
            table,
        ):
            continue

        names = {
            row["name"]
            for row in columns(
                conn,
                table,
            )
        }

        conditions = []
        params = []

        if "offer_key" in names:

            conditions.append(
                "offer_key=?"
            )

            params.append(
                OFFER_KEY
            )

        if (
            "alert_id" in names
            and alert_id is not None
        ):

            conditions.append(
                "alert_id=?"
            )

            params.append(
                alert_id
            )

        if (
            table == "alerts"
            and "id" in names
            and alert_id is not None
        ):

            conditions.append(
                "id=?"
            )

            params.append(
                alert_id
            )

        if (
            table == "flips"
            and "id" in names
            and flip_id is not None
        ):

            conditions.append(
                "id=?"
            )

            params.append(
                flip_id
            )

        if conditions:

            conn.execute(
                f"""
                DELETE FROM {table}
                WHERE
                {' OR '.join(conditions)}
                """,
                params,
            )

    conn.commit()
    conn.close()


def cleanup():
    print()
    print("[CLEANUP] Usuwam dane testowe...")

    cleanup_db(
        CRM_DB,
        [
            "deal_history",
            "followups",
            "pickup_checks",
            "sale_prep_costs",
            "sale_plans",
            "sale_listings",
            "sale_price_history",
            "sale_price_notifications",
            "deals",
        ],
    )

    cleanup_db(
        FLIP_DB,
        [
            "flips",
        ],
    )

    cleanup_db(
        ALERT_DB,
        [
            "alerts",
        ],
    )

    cleanup_db(
        f"{ROOT}/watchlist.db",
        [
            "watchlist",
        ],
    )

    cleanup_db(
        f"{ROOT}/offer_snapshots.db",
        [
            "snapshots",
        ],
    )

    cleanup_db(
        f"{ROOT}/purchase_checklist.db",
        [
            "checks",
        ],
    )

    print(
        "[CLEANUP] OK"
    )


try:
    banner(
        "V1.0 END-TO-END TEST"
    )

    # =========================================
    # ALERT / NEW
    # =========================================

    alert_id = (
        create_test_alert()
    )

    print(
        "[1] TEST ALERT ID:",
        alert_id,
    )

    ensure_deal(
        offer_key=OFFER_KEY,
        alert_id=alert_id,
        title=TITLE,
        url=URL,
    )

    assert (
        status_for_offer(
            OFFER_KEY
        )
        == "NEW"
    )

    print(
        "[2] NEW ✅"
    )


    # =========================================
    # CONTACTED
    # =========================================

    add_entry(
        offer_key=OFFER_KEY,
        alert_id=alert_id,
        kind="MESSAGE",
        note="Testowy kontakt ze sprzedającym",
    )

    set_status(
        OFFER_KEY,
        "CONTACTED",
    )

    assert (
        status_for_offer(
            OFFER_KEY
        )
        == "CONTACTED"
    )

    print(
        "[3] CONTACTED ✅"
    )


    # =========================================
    # NEGOTIATING
    # =========================================

    add_entry(
        offer_key=OFFER_KEY,
        alert_id=alert_id,
        kind="MY_OFFER",
        amount=1500,
        note="Moja oferta testowa",
    )

    add_entry(
        offer_key=OFFER_KEY,
        alert_id=alert_id,
        kind="SELLER_OFFER",
        amount=1600,
        note="Sprzedający zaakceptował 1600",
    )

    set_status(
        OFFER_KEY,
        "NEGOTIATING",
    )

    assert (
        status_for_offer(
            OFFER_KEY
        )
        == "NEGOTIATING"
    )

    print(
        "[4] NEGOTIATING ✅"
    )


    # =========================================
    # PICKUP
    # =========================================

    set_status(
        OFFER_KEY,
        "PICKUP",
    )

    assert (
        status_for_offer(
            OFFER_KEY
        )
        == "PICKUP"
    )

    print(
        "[5] PICKUP ✅"
    )


    # =========================================
    # PICKUP CHECKLIST
    # =========================================

    for item in ITEMS:

        set_check(
            OFFER_KEY,
            item["key"],
            "OK",
        )

    pickup = get_checklist(
        OFFER_KEY
    )

    pickup_result = readiness(
        pickup
    )

    assert (
        pickup_result[
            "ready"
        ]
        is True
    )

    print(
        "[6] PICKUP CHECKLIST "
        f"{pickup_result['ok']}/"
        f"{pickup_result['total']} ✅"
    )


    # =========================================
    # BOUGHT
    # =========================================

    flip_id = (
        create_test_flip()
    )

    set_status(
        OFFER_KEY,
        "BOUGHT",
    )

    assert (
        status_for_offer(
            OFFER_KEY
        )
        == "BOUGHT"
    )

    print(
        "[7] BOUGHT ✅ | flip:",
        flip_id,
    )


    # =========================================
    # PREPARING
    # =========================================

    add_cost(
        OFFER_KEY,
        alert_id,
        "SSD",
        120,
        "SSD testowy",
    )

    add_cost(
        OFFER_KEY,
        alert_id,
        "CASE",
        150,
        "Obudowa testowa",
    )

    save_plan(
        OFFER_KEY,
        alert_id,
        2699,
        2450,
    )

    set_status(
        OFFER_KEY,
        "PREPARING",
    )

    prep = sale_summary(
        OFFER_KEY,
        alert_id,
        2450,
    )

    print(
        "[8] PREPARING ✅"
    )

    print(
        "    zakup:",
        prep["purchase_price"],
    )

    print(
        "    dodatkowe:",
        prep["purchase_extra"],
    )

    print(
        "    przygotowanie:",
        prep["prep_cost"],
    )

    print(
        "    łącznie:",
        prep["total_investment"],
    )


    # =========================================
    # READY TO SELL
    # =========================================

    set_status(
        OFFER_KEY,
        "READY_TO_SELL",
    )

    assert (
        status_for_offer(
            OFFER_KEY
        )
        == "READY_TO_SELL"
    )

    print(
        "[9] READY_TO_SELL ✅"
    )


    # =========================================
    # LISTED
    # =========================================

    mark_listed(
        OFFER_KEY,
        alert_id,
        2699,
        "OLX+FACEBOOK",
    )

    set_status(
        OFFER_KEY,
        "LISTED",
    )

    listing = get_listing(
        OFFER_KEY
    )

    assert int(
        listing["listed_price"]
    ) == 2699

    print(
        "[10] LISTED 2699 zł ✅"
    )


    # =========================================
    # PRICE CHANGE
    # =========================================

    change_price(
        OFFER_KEY,
        2599,
        "V1_TEST_REDUCTION",
    )

    history = price_history(
        OFFER_KEY
    )

    assert history
    assert int(
        history[0]["new_price"]
    ) == 2599

    print(
        "[11] PRICE 2699 → 2599 ✅"
    )


    # =========================================
    # SOLD
    # =========================================

    sell_test_flip()

    close_listing(
        OFFER_KEY
    )

    set_status(
        OFFER_KEY,
        "SOLD",
    )

    assert (
        status_for_offer(
            OFFER_KEY
        )
        == "SOLD"
    )

    print(
        "[12] SOLD 2450 zł ✅"
    )


    # =========================================
    # REALNY ZYSK TESTOWY
    # =========================================

    investment = float(
        prep["total_investment"]
    )

    real_profit = (
        2450
        - investment
    )

    print()
    print(
        "Cena sprzedaży:",
        "2450 zł",
    )

    print(
        "Łączny koszt:",
        f"{investment:.0f} zł",
    )

    print(
        "Realny zysk:",
        f"{real_profit:.0f} zł",
    )


    # =========================================
    # FLASK
    # =========================================

    from dashboard import app

    client = app.test_client()

    offer_response = client.get(
        f"/offer/{alert_id}"
    )

    control_response = client.get(
        "/control"
    )

    print()
    print(
        "OFFER HTTP:",
        offer_response.status_code,
    )

    print(
        "CONTROL HTTP:",
        control_response.status_code,
    )

    assert (
        offer_response.status_code
        == 200
    )

    assert (
        control_response.status_code
        == 200
    )


    banner(
        "V1.0 END-TO-END TEST PASSED ✅"
    )

    print(
        "NEW → CONTACTED → NEGOTIATING "
        "→ PICKUP → BOUGHT → PREPARING "
        "→ READY_TO_SELL → LISTED "
        "→ PRICE CHANGE → SOLD"
    )


finally:
    cleanup()
