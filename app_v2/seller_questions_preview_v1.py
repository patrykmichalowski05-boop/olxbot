import json
import re
import sqlite3
from urllib.parse import urlparse

FIELDS = ("cpu", "gpu", "ram_gb")
LABELS = {
    "cpu": "dokładny model procesora",
    "gpu": "dokładny model karty graficznej",
    "ram_gb": "ilość pamięci RAM",
}

SKIP = re.compile(
    r"\b(laptop|notebook|uszkodz\w*|niesprawn\w*|zamieni\w*)\b",
    re.I
)


def canon(value):
    return re.sub(r"\s+", "", str(value or "")).upper()


def valid(field, value):
    if value is None or str(value).strip() == "":
        return False

    if field == "ram_gb":
        try:
            return 1 <= int(value) <= 128
        except (ValueError, TypeError):
            return False

    return True


def different(field, left, right):
    if field == "ram_gb":
        try:
            return int(left) != int(right)
        except (ValueError, TypeError):
            return True

    return canon(left) != canon(right)


def safe_url(value):
    try:
        parsed = urlparse(str(value or ""))
        host = (parsed.hostname or "").lower()

        allowed = (
            "olx.pl",
            "facebook.com",
            "allegro.pl",
            "allegrolokalnie.pl",
        )

        if parsed.scheme == "https" and any(
            host == d or host.endswith("." + d)
            for d in allowed
        ):
            return parsed.geturl()

    except ValueError:
        pass

    return None


def analyze(offer, extractor):
    title = str(offer.get("title") or "")

    if SKIP.search(title):
        return None

    try:
        price = int(offer.get("price_zl") or 0)
    except (TypeError, ValueError):
        return None

    if not 250 <= price <= 3000:
        return None

    title_specs = extractor(title)

    try:
        payload = json.loads(
            offer.get("payload_json") or "{}"
        )
    except (ValueError, TypeError):
        payload = {}

    description = (
        payload.get("parts_from_description")
        if isinstance(payload, dict)
        else {}
    )

    if not isinstance(description, dict):
        description = {}

    missing = []
    conflicts = []
    hints = []
    effective = {}

    for field in FIELDS:
        db_value = offer.get(field)
        title_value = title_specs.get(field)
        desc_value = description.get(field)

        db_ok = valid(field, db_value)
        title_ok = valid(field, title_value)
        desc_ok = valid(field, desc_value)

        if db_ok and title_ok and different(
            field, db_value, title_value
        ):
            conflicts.append(
                LABELS[field] + " (baza a tytuł)"
            )

        if db_ok and desc_ok and different(
            field, db_value, desc_value
        ):
            conflicts.append(
                LABELS[field] + " (baza a opis)"
            )

        if title_ok and desc_ok and different(
            field, title_value, desc_value
        ):
            conflicts.append(
                LABELS[field] + " (tytuł a opis)"
            )

        if db_ok:
            effective[field] = db_value

        elif desc_ok:
            effective[field] = desc_value
            hints.append(
                LABELS[field] + ": opis (" +
                str(desc_value) + ")"
            )

        elif title_ok:
            effective[field] = title_value
            hints.append(
                LABELS[field] + ": tytuł (" +
                str(title_value) + ")"
            )

        else:
            effective[field] = None
            missing.append(field)

    if not missing and not conflicts:
        return None

    known = sum(
        valid(field, effective[field])
        for field in FIELDS
    )

    if known < 2:
        return None

    questions = [
        LABELS[field]
        for field in missing
    ]

    if conflicts:
        questions.append(
            "potwierdzenie rozbieżnych parametrów: " +
            "; ".join(sorted(set(conflicts)))
        )

    message = (
        "Dzień dobry, jestem zainteresowany komputerem. "
        + (
            "Czy można podać " +
            ", ".join(questions) + "? "
            if questions else ""
        )
        + "Czy komputer jest w pełni sprawny, "
          "czy można go przetestować oraz "
          "jaki jest model zasilacza?"
    )

    return {
        "source": str(offer.get("source") or ""),
        "listing_id": str(offer.get("listing_id") or ""),
        "title": title,
        "price_zl": price,
        "url": safe_url(offer.get("url")),
        "missing": ", ".join(
            LABELS[field] for field in missing
        ) or "brak",
        "conflicts": "; ".join(
            sorted(set(conflicts))
        ) or "brak",
        "hints": "; ".join(hints) or "brak",
        "message": message,
        "status": "DO_WERYFIKACJI",
        "automation_allowed": False,
    }


def list_candidates(limit=100):
    from app_v2.saved_searches_v1 import DB
    from app_v2.spec_enrichment_v1 import extract

    with sqlite3.connect(
        DB.resolve().as_uri() + "?mode=ro",
        uri=True
    ) as db:
        db.row_factory = sqlite3.Row

        offers = db.execute("""
            SELECT source, listing_id, title, url,
                   price_zl, cpu, gpu, ram_gb,
                   payload_json
            FROM offers
            WHERE status='REVIEW_SPECS'
              AND price_zl BETWEEN 250 AND 3000
            ORDER BY last_seen_utc DESC
        """).fetchall()

    results = []

    for row in offers:
        item = analyze(dict(row), extract)

        if item is not None:
            results.append(item)

    return (
        results[:max(0, min(int(limit), 5000))],
        len(results)
    )
