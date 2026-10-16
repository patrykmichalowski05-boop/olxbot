"""Facebook-only human review notifications, without automatic BUY."""

from html import escape
from math import isfinite
from urllib.parse import urlsplit
import re

MIN_REVIEW_PROFIT_PLN = 400


def _number(value):
    if isinstance(value, bool):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None

    return number if isfinite(number) else None


def _valid_facebook_url(url):
    try:
        parsed = urlsplit(str(url or ""))
    except ValueError:
        return False

    return (
        parsed.scheme == "https"
        and parsed.hostname in (
            "www.facebook.com",
            "facebook.com",
            "m.facebook.com",
        )
        and not parsed.username
        and not parsed.password
        and re.fullmatch(
            r"/marketplace/item/\d+/?",
            parsed.path,
        ) is not None
    )


def is_review_eligible(
    details,
    metadata,
    specs,
    valuation,
    url,
    action,
    min_profit=400,
):
    if action != "WATCH":
        return False

    if not _valid_facebook_url(url):
        return False

    if not all(
        isinstance(item, dict)
        for item in (
            details,
            metadata,
            specs,
            valuation,
        )
    ):
        return False

    if (
        metadata.get("is_live") is not True
        or metadata.get("is_sold") is not False
        or str(
            metadata.get("currency") or ""
        ).upper().strip() != "PLN"
    ):
        return False

    if not (
        specs.get("cpu")
        and specs.get("gpu")
    ):
        return False

    ram = _number(specs.get("ram"))

    if ram is None or ram < 16:
        return False

    price = _number(details.get("price"))
    verified_price = _number(metadata.get("price"))
    profit = _number(valuation.get("profit"))
    sale = _number(valuation.get("quick_sale"))
    total = _number(valuation.get("total_cost"))
    threshold = _number(min_profit)

    if None in (
        price,
        verified_price,
        profit,
        sale,
        total,
        threshold,
    ):
        return False

    if (
        price <= 0
        or abs(price - verified_price) > 1
        or total < price
        or sale <= total
        or threshold < 0
        or profit < max(
            MIN_REVIEW_PROFIT_PLN,
            threshold,
        )
        or abs(profit - (sale - total)) > 25
    ):
        return False

    condition = str(
        valuation.get("ai_condition") or ""
    ).lower()

    if condition in (
        "bad",
        "poor",
        "risky",
    ):
        return False

    issues = valuation.get("ai_issues") or []

    if (
        not isinstance(issues, (list, tuple))
        or len(issues) >= 4
    ):
        return False

    return True


def review_message(
    details,
    valuation,
    url,
    score,
):
    title = escape(
        str(
            details.get("title") or "Komputer"
        )[:200]
    )

    cpu = escape(
        str(details.get("cpu") or "Brak")[:90]
    )

    gpu = escape(
        str(details.get("gpu") or "Brak")[:90]
    )

    confidence = escape(
        str(
            valuation.get("confidence") or "BRAK"
        )[:30]
    )

    link = escape(str(url), quote=True)

    def zl(value):
        return f"{_number(value):.0f} zl"

    return (
        "🔎 <b>FACEBOOK - OKAZJA DO "
        "RĘCZNEJ WERYFIKACJI</b>\n\n"
        f"<b>{title}</b>\n"
        f"Cena: <b>{zl(details['price'])}</b>\n"
        "Szybka sprzedaż (szacunek): "
        f"{zl(valuation['quick_sale'])}\n"
        "Szacowany zysk: "
        f"<b>{zl(valuation['profit'])}</b>\n"
        f"CPU: {cpu}\n"
        f"GPU: {gpu}\n"
        f"RAM: {details.get('ram')} GB\n"
        f"Pewność: {confidence}; score: {int(score)}\n\n"
        "⚠️ Wycena może być niedokładna. "
        "Sprawdź dostępność, stan, kompletność "
        "i realną cenę sprzedaży. "
        "NIE jest to sygnał kup teraz.\n"
        f'<a href="{link}">'
        "Otwórz ofertę Facebook</a>"
    )


def send_watch_review_alert(
    details,
    metadata,
    specs,
    valuation,
    url,
    action,
    score,
    min_profit,
    *,
    send_fn,
    already_sent_fn,
    record_fn,
):
    if not is_review_eligible(
        details,
        metadata,
        specs,
        valuation,
        url,
        action,
        min_profit,
    ):
        return "NOT_ELIGIBLE"

    try:
        if already_sent_fn(details, url):
            return "SUPPRESSED"

        message = review_message(
            details,
            valuation,
            url,
            score,
        )

        if not send_fn(message):
            return "ERROR"

    except Exception as exc:
        print(
            "[FB REVIEW] Blad wysylki:",
            type(exc).__name__,
        )
        return "ERROR"

    # Telegram potwierdzil wysylke.
    # Facebook zapisze alert_sent osobno.
    try:
        record_fn(
            details=details,
            valuation=valuation,
            offer_url=url,
            score=score,
            mode="LOCAL",
        )

    except Exception as exc:
        print(
            "[FB REVIEW] Alert wyslany, "
            "ale zapis historii nieudany:",
            type(exc).__name__,
        )

    return "SENT"
