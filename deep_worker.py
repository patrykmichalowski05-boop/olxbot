import os
import re
import sqlite3
import time

from datetime import datetime

from playwright.sync_api import (
    sync_playwright,
)

from fast_db import (
    init_db,
    mark_done,
    mark_failed,
    recover_stale_processing,
    queue_stats,
)

from scanner import (
    analyze_candidate,
)

from priority_queue import (
    claim_next_priority,
)

from browser_utils import (
    block_heavy_resources,
)


DECISION_DB = (
    "/opt/olx-bot/decision_log.db"
)


MAX_JOBS = int(
    os.getenv(
        "DEEP_MAX_JOBS",
        "10",
    )
)


# ============================================================
# LIGHT PREFILTER
# ============================================================

def normalize_title(
    title,
):

    return re.sub(
        r"\s+",
        " ",
        str(
            title or ""
        ).lower(),
    ).strip()


def obvious_non_pc(
    job,
):
    """
    Bardzo konserwatywny filtr.

    Odrzucamy tylko jednoznaczne części / akcesoria.

    Tanie i słabo opisane pełne komputery przepuszczamy
    do właściwej analizy.
    """

    title = normalize_title(
        job["title"]
    )

    price = job["price"]

    # --------------------------------------------------------
    # HARDWARE
    # --------------------------------------------------------

    hardware_markers = [
        "rtx ",
        "gtx ",
        "rx 5",
        "rx 6",
        "rx 7",
        "rx 9",
        "radeon",
        "ryzen",
        "i3-",
        "i3 ",
        "i5-",
        "i5 ",
        "i7-",
        "i7 ",
        "i9-",
        "i9 ",
        "core ultra",
    ]

    has_computer_hardware = any(
        marker in title
        for marker in hardware_markers
    )

    # --------------------------------------------------------
    # WYGLĄDA JAK PEŁNY KOMPUTER
    # --------------------------------------------------------

    full_pc_markers = [
        "komputer",
        "gaming pc",
        "pc gaming",
        "gamingowy pc",
        "pecet",
        "mini pc",
    ]

    looks_like_pc = any(
        marker in title
        for marker in full_pc_markers
    )

    # --------------------------------------------------------
    # JEDNOZNACZNIE CZĘŚĆ
    # --------------------------------------------------------

    part_only_patterns = [
        r"^obudowa\b",
        r"^zasilacz\b",
        r"^płyta główna\b",
        r"^plyta glowna\b",
        r"^procesor\b",
        r"^karta graficzna\b",
        r"^pamięć ram\b",
        r"^pamiec ram\b",
        r"^ram \d",
        r"^dysk\b",
        r"^ssd\b",
        r"^nvme\b",
        r"^hdd\b",
        r"^chłodzenie\b",
        r"^chlodzenie\b",
        r"^cooler\b",
        r"^wentylator\b",
        r"^wentylatory\b",
    ]

    if any(
        re.search(
            pattern,
            title,
        )
        for pattern in part_only_patterns
    ):

        return (
            True,
            "OBVIOUS_PART_TITLE",
        )

    explicit_part_phrases = [
        "sama obudowa",
        "sam zasilacz",
        "sama płyta główna",
        "sama plyta glowna",
        "sam procesor",
        "sama karta graficzna",
        "same kości ram",
        "same kosci ram",
        "sam dysk",
        "zestaw części",
        "zestaw czesci",
    ]

    if any(
        phrase in title
        for phrase in explicit_part_phrases
    ):

        return (
            True,
            "EXPLICIT_PART_ONLY",
        )

    # --------------------------------------------------------
    # SAME AKCESORIA
    # --------------------------------------------------------

    accessory_patterns = [
        r"^monitor\b",
        r"^klawiatura\b",
        r"^mysz\b",
        r"^podkładka\b",
        r"^podkladka\b",
    ]

    if any(
        re.search(
            pattern,
            title,
        )
        for pattern in accessory_patterns
    ):

        return (
            True,
            "ACCESSORY_ONLY",
        )

    # --------------------------------------------------------
    # CENA
    # --------------------------------------------------------

    try:

        numeric_price = int(
            price
        )

    except Exception:

        numeric_price = None

    # Bardzo tania rzecz bez żadnego sygnału,
    # że to komputer.
    #
    # ALE:
    # "Komputer Lenovo 150 zł"
    # przepuszczamy.

    if (
        numeric_price is not None
        and
        numeric_price < 300
        and
        not has_computer_hardware
        and
        not looks_like_pc
    ):

        return (
            True,
            "LOW_PRICE_NO_PC_SIGNAL",
        )

    return (
        False,
        None,
    )


# ============================================================
# DECISION LOG LOOKUP
# ============================================================

def latest_decision(
    offer_id,
    since,
):

    try:

        conn = sqlite3.connect(
            DECISION_DB
        )

        conn.row_factory = (
            sqlite3.Row
        )

        row = conn.execute("""
            SELECT
                decision,
                reason,
                stage,
                created_at

            FROM decisions

            WHERE
                offer_id = ?
                AND created_at >= ?

            ORDER BY id DESC

            LIMIT 1
        """, (
            offer_id,
            since,
        )).fetchone()

        conn.close()

        return row

    except Exception as e:

        print(
            "[DEEP DECISION DB ERROR] "
            f"{e}"
        )

        return None


# ============================================================
# PROCESS JOB
# ============================================================

def process_job(
    detail_page,
    job,
):

    job_id = (
        job["id"]
    )

    offer_id = (
        job["offer_id"]
    )

    started_at = (
        datetime.now()
        .isoformat(
            timespec="seconds"
        )
    )

    print()
    print(
        "=" * 80
    )

    print(
        f"[DEEP JOB #{job_id}]"
    )

    print(
        f"ID:      {offer_id}"
    )

    print(
        f"MODE:    {job['mode']}"
    )

    print(
        f"TRIGGER: {job['trigger']}"
    )

    print(
        f"CENA:    {job['price']}"
    )

    print(
        f"TYTUŁ:   {job['title']}"
    )

    print(
        f"URL:     {job['url']}"
    )

    print(
        f"PRÓBA:   {job['attempts']}"
    )

    print(
        "=" * 80
    )

    # ========================================================
    # CHEAP PREFILTER
    # ========================================================

    rejected, reason = (
        obvious_non_pc(
            job
        )
    )

    if rejected:

        print(
            "[DEEP PREFILTER SKIP] "
            f"{reason}"
        )

        mark_done(
            job_id
        )

        print(
            "[DEEP JOB] "
            "DONE / PREFILTER SKIP"
        )

        return True

    # ========================================================
    # FULL ANALYSIS
    # ========================================================

    try:

        accepted = analyze_candidate(
            detail_page=detail_page,

            offer_id=offer_id,

            offer_url=
                job["url"],

            card_title=
                job["title"],

            card_price=
                job["price"],

            mode=
                job["mode"],

            trigger=
                job["trigger"],
        )

    except Exception as e:

        print(
            "[DEEP EXCEPTION] "
            f"{type(e).__name__}: {e}"
        )

        status = mark_failed(
            job_id,
            (
                "UNHANDLED_EXCEPTION: "
                f"{type(e).__name__}: "
                f"{e}"
            ),
        )

        print(
            "[DEEP JOB] "
            f"{status}"
        )

        return False

    # ========================================================
    # ACCEPT
    # ========================================================

    if accepted:

        mark_done(
            job_id
        )

        print(
            "[DEEP JOB] "
            "DONE / ACCEPT"
        )

        return True

    # ========================================================
    # LOOKUP DECISION
    # ========================================================

    decision = latest_decision(
        offer_id,
        started_at,
    )

    if decision is None:

        status = mark_failed(
            job_id,
            "NO_DECISION_LOG",
        )

        print(
            "[DEEP JOB] "
            f"{status} / "
            "NO_DECISION_LOG"
        )

        return False

    decision_type = (
        decision[
            "decision"
        ]
    )

    reason = str(
        decision[
            "reason"
        ]
        or ""
    )

    stage = str(
        decision[
            "stage"
        ]
        or ""
    )

    print(
        "[DEEP DECISION] "
        f"{decision_type} | "
        f"{stage} | "
        f"{reason}"
    )

    # ========================================================
    # NORMAL REJECT / ACCEPT
    # ========================================================

    if decision_type in [
        "REJECT",
        "ACCEPT",
        "SUPPRESSED",
    ]:

        mark_done(
            job_id
        )

        print(
            "[DEEP JOB] DONE"
        )

        return True

    # ========================================================
    # ERROR
    # ========================================================

    if decision_type == "ERROR":

        error_text = f"{stage}: {reason}".upper()

        if "PRICE_NOT_FOUND" in error_text:
            mark_done(job_id)
            print("[DEEP JOB] DONE / SKIPPED_PRICE_NOT_FOUND")
            return True

        error_text = (
            f"{stage}: {reason}"
        ).upper()

        # ----------------------------------------------------
        # PRICE NOT FOUND
        # ----------------------------------------------------
        #
        # Brak ceny nie jest awarią bota.
        #
        # Mogą to być:
        # - zamiany
        # - ogłoszenia bez ceny
        # - dziwne / uszkodzone oferty OLX
        #
        # Jedna pełna analiza wystarczy.
        # Nie robimy 3 retry.

        if (
            "PRICE_NOT_FOUND"
            in error_text
        ):

            print(
                "[DEEP SKIP] "
                "PRICE_NOT_FOUND"
            )

            mark_done(
                job_id
            )

            print(
                "[DEEP JOB] "
                "DONE / SKIPPED_PRICE_NOT_FOUND"
            )

            return True

        # ----------------------------------------------------
        # INNY BŁĄD
        # ----------------------------------------------------

        status = mark_failed(
            job_id,
            f"{stage}: {reason}",
        )

        print(
            "[DEEP JOB] "
            f"{status} / ERROR"
        )

        return False

    # ========================================================
    # UNKNOWN DECISION
    # ========================================================

    status = mark_failed(
        job_id,
        (
            "UNKNOWN_DECISION: "
            f"{decision_type}"
        ),
    )

    print(
        "[DEEP JOB] "
        f"{status}"
    )

    return False


# ============================================================
# MAIN
# ============================================================

def main():

    init_db()

    recovered = (
        recover_stale_processing(
            minutes=30
        )
    )

    if recovered:

        print(
            "[DEEP RECOVERY] "
            f"Przywrócono: "
            f"{recovered}"
        )

    print()
    print(
        "=" * 80
    )

    print(
        "DEEP WORKER START"
    )

    print(
        "MAX JOBS:",
        MAX_JOBS
    )

    print(
        "QUEUE:",
        queue_stats()
    )

    print(
        "=" * 80
    )

    jobs_processed = 0
    finished = 0
    errors = 0

    start = time.time()

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            viewport={
                "width": 1280,
                "height": 720,
            },

            locale="pl-PL",

            service_workers="block",
        )

        block_heavy_resources(
            context
        )

        detail_page = (
            context.new_page()
        )

        while (
            jobs_processed
            <
            MAX_JOBS
        ):

            job = (
                claim_next_priority()
            )

            if job is None:

                print()

                print(
                    "[DEEP] "
                    "Brak PENDING."
                )

                break

            result = process_job(
                detail_page,
                job,
            )

            jobs_processed += 1

            if result:

                finished += 1

            else:

                errors += 1

            time.sleep(
                0.3
            )

        browser.close()

    elapsed = round(
        time.time()
        -
        start,
        2
    )

    print()
    print(
        "=" * 80
    )

    print(
        "DEEP WORKER GOTOWY"
    )

    print(
        f"Czas:        "
        f"{elapsed}s"
    )

    print(
        f"Jobs:        "
        f"{jobs_processed}"
    )

    print(
        f"Zakończone:  "
        f"{finished}"
    )

    print(
        f"Retry/error: "
        f"{errors}"
    )

    print(
        "Queue:",
        queue_stats()
    )

    print(
        "=" * 80
    )


if __name__ == "__main__":
    main()
