import os
import sqlite3
from contextlib import closing
from html import escape
from alert_dedupe import make_offer_key


def send_watch_review(details, valuation, action, offer_url, sender):
    if action.get('action') != 'WATCH':
        return False
    try:
        price = int(float(details.get('price')))
        profit = float(valuation.get('profit'))
    except (TypeError, ValueError):
        return False
    condition = str(valuation.get('ai_condition') or '').lower()
    if price <= 0 or profit < 400 or condition in ('bad', 'poor', 'risky'):
        return False
    if not details.get('cpu') or not details.get('gpu') or not offer_url:
        return False
    key = make_offer_key(details, offer_url)
    db_path = os.getenv('WATCH_REVIEW_DB', '/opt/olx-bot/watch_review_alerts.db')
    with closing(sqlite3.connect(db_path, timeout=30)) as db:
        db.execute(
            'CREATE TABLE IF NOT EXISTS alerts '
            '(offer_key TEXT PRIMARY KEY, price INTEGER NOT NULL)'
        )
        with db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute(
                'SELECT price FROM alerts WHERE offer_key=?', (key,)
            ).fetchone()
            if old and old[0] - price < 150:
                return False
            msg = (
                '👀 <b>WARTO SPRAWDZIĆ — WATCH</b>\n'
                '<b>To nie jest rekomendacja zakupu.</b>\n'
                f'{escape(str(details.get("title") or "Komputer"))}\n'
                f'Cena: {price} zł | Potencjalny zysk: {profit:.0f} zł\n'
                f'Pewność: {escape(str(valuation.get("confidence") or "brak"))}\n'
                f'CPU: {escape(str(details.get("cpu")))}\n'
                f'GPU: {escape(str(details.get("gpu")))}\n'
                f'<a href="{escape(str(offer_url), quote=True)}">Otwórz OLX</a>'
            )
            if not sender(msg):
                return False
            db.execute(
                'INSERT INTO alerts VALUES (?,?) ON CONFLICT(offer_key) '
                'DO UPDATE SET price=excluded.price', (key, price)
            )
            return True
