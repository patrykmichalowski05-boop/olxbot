"""Telegram delivery with bounded retries; credentials never enter the DB/logs."""

from __future__ import annotations

import html
import os

import requests

from .models import Offer
from .store import Store


class DeliveryError(Exception):
    def __init__(self, code: str, retryable: bool = True, retry_after: int = 0):
        super().__init__(code)
        self.code, self.retryable, self.retry_after = code, retryable, retry_after


def money(value: int) -> str:
    sign = "-" if value < 0 else ""
    units = f"{abs(value) // 100:,}".replace(",", " ")
    return f"{sign}{units},{abs(value) % 100:02d} zł"


def message(payload: dict) -> str:
    offer = Offer.from_mapping(payload["offer"])
    result = payload["result"]

    def esc(value):
        return html.escape(str(value), quote=True)

    lines = [
        f"<b>FlipRadar · {esc(payload['search_name'])}</b>",
        esc(offer.title[:240]),
        f"{esc(offer.platform)} · {money(offer.price_minor)}",
    ]
    value = result.get("valuation")
    if value:
        lines.extend(
            [
                f"Prognoza odsprzedaży: <b>{money(value['sell_minor'])}</b>",
                f"Potencjalny wynik po kosztach: <b>{money(value['profit_minor'])}</b>",
                f"ROI: {value['roi_bps'] / 100:.1f}% · Limit zakupu: {money(value['max_buy_minor'])}",
                f"Koszty i rezerwa: {money(value['cost_minor'])} · przed podatkiem",
            ]
        )
    else:
        lines.append("Cena w ustawionym limicie. Brak wiarygodnej prognozy zysku.")
    market = result.get("market") or {}
    if market.get("kind") == "ASKING":
        lines.append("Punkt odniesienia: ceny ofertowe, nie potwierdzone transakcje.")
    lines.extend(esc(warning[:180]) for warning in result.get("warnings", [])[:3])
    lines.append(f'<a href="{esc(offer.url)}">Zobacz ofertę</a>')
    return "\n".join(lines)


class Telegram:
    def __init__(
        self,
        token_env: str = "TELEGRAM_BOT_TOKEN",
        chat_env: str = "TELEGRAM_CHAT_ID",
        session=None,
    ):
        self.token_env, self.chat_env = token_env, chat_env
        self.session = session or requests.Session()

    @property
    def configured(self):
        return bool(os.getenv(self.token_env) and os.getenv(self.chat_env))

    def send(self, payload: dict):
        token, chat = os.getenv(self.token_env), os.getenv(self.chat_env)
        if not token or not chat:
            raise DeliveryError("NOTIFICATIONS_NOT_CONFIGURED", False)
        try:
            response = self.session.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat,
                    "text": message(payload),
                    "parse_mode": "HTML",
                    "link_preview_options": {"is_disabled": True},
                },
                timeout=(10, 25),
                allow_redirects=False,
            )
        except requests.RequestException:
            raise DeliveryError("TELEGRAM_NETWORK_ERROR") from None
        try:
            try:
                data = response.json()
            except ValueError:
                data = {}
            if not isinstance(data, dict):
                data = {}
            if response.status_code == 429 or data.get("error_code") == 429:
                parameters = data.get("parameters")
                delay = (
                    parameters.get("retry_after", 60)
                    if isinstance(parameters, dict)
                    else 60
                )
                delay = delay if type(delay) is int else 60
                raise DeliveryError(
                    "TELEGRAM_RATE_LIMITED", retry_after=min(max(delay, 1), 86400)
                )
            if response.status_code >= 500:
                raise DeliveryError("TELEGRAM_UNAVAILABLE")
            if response.status_code != 200 or data.get("ok") is not True:
                raise DeliveryError("TELEGRAM_REJECTED", False)
        finally:
            response.close()

    def close(self):
        self.session.close()


def dispatch(store: Store, owner: str, sender: Telegram, limit: int = 20) -> dict:
    if not sender.configured:
        return {"sent": 0, "retry": 0, "failed": 0, "status": "NOT_CONFIGURED"}
    stats = {"sent": 0, "retry": 0, "failed": 0, "status": "OK"}
    for _ in range(limit):
        alert = store.claim(owner)
        if alert is None:
            break
        try:
            sender.send(alert["body"])
        except DeliveryError as error:
            retry = error.retryable and alert["attempts"] < 8
            delay = max(error.retry_after, min(3600, 30 * 2 ** (alert["attempts"] - 1)))
            store.finish(alert, "RETRY" if retry else "FAILED", error.code, delay)
            stats["retry" if retry else "failed"] += 1
            # Respect Telegram's global rate limit; do not claim the rest now.
            if error.code == "TELEGRAM_RATE_LIMITED":
                store.defer_notifications(owner, delay)
                break
        else:
            if store.finish(alert):
                stats["sent"] += 1
    return stats
