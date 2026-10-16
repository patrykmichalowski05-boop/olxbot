#!/bin/bash

SINCE="2026-10-03 22:00:00"

echo
echo "============================================================"
echo "OLX FLIP HUNTER — RAPORT NOCNY"
echo "Od: $SINCE"
echo "============================================================"


echo
echo "1. SKANY"
echo "------------------------------------------------------------"

echo -n "Zakończone skany: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -c "SKAN GOTOWY" || true

echo
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep "SKAN GOTOWY" \
    | tail -20 || true


echo
echo "2. FLIPY / ALERTY"
echo "------------------------------------------------------------"

echo -n "Flipy wykryte: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -cE "DOBRY FLIP|GORĄCA OKAZJA" || true

echo -n "Telegram OK: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -c "\[ALERT\] Telegram OK" || true

echo -n "Telegram ERROR: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -c "ALERT ERROR" || true


echo
echo "3. PRICE DROP"
echo "------------------------------------------------------------"

echo -n "Wykryte obniżki: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -c "PRICE DROP" || true


echo
echo "4. AI SPEC RECOVERY"
echo "------------------------------------------------------------"

echo -n "Uruchomienia SPEC AI: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -c "\[SPEC AI\] Brakujące" || true

echo -n "Udane odzyskania: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -c "\[SPEC AI OK\]" || true

echo -n "Błędy SPEC AI: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -c "\[SPEC AI ERROR\]" || true


echo
echo "5. ODRZUTY"
echo "------------------------------------------------------------"

echo -n "Hardware: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -c "\[ODRZUT SPRZĘTOWY\]" || true

echo -n "Brak wysyłki: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -c "\[ODRZUT POLSKA\]" || true

echo -n "Wycena: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -c "\[ODRZUT WYCENA\]" || true

echo -n "Przed AI: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -c "\[ODRZUT PRZED AI\]" || true

echo -n "Finalne: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -c "\[ODRZUT FINALNY\]" || true


echo
echo "6. PROBLEMY"
echo "------------------------------------------------------------"

echo -n "Traceback: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -ci "Traceback" || true

echo -n "Timeout: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -ci "timeout" || true

echo -n "ERROR: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -ci "ERROR" || true

echo -n "FAILED: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -ci "failed" || true


echo
echo "7. BRAKUJĄCE CENY"
echo "------------------------------------------------------------"

echo -n "CENA None: "
journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep -c "CENA: None" || true


echo
echo "8. RESOURCE USAGE — OSTATNIE 10"
echo "------------------------------------------------------------"

journalctl -u olx-bot.service \
    --since "$SINCE" \
    --no-pager \
    | grep "Consumed" \
    | tail -10 || true


echo
echo "9. DECISION DB"
echo "------------------------------------------------------------"

cd /opt/olx-bot

sqlite3 decision_log.db "
SELECT
    decision,
    stage,
    reason,
    COUNT(*)
FROM decisions
WHERE created_at >= '2026-10-03T22:00:00'
GROUP BY decision, stage, reason
ORDER BY COUNT(*) DESC;
"


echo
echo "10. NAJLEPSZE ODRZUCONE"
echo "------------------------------------------------------------"

sqlite3 decision_log.db "
SELECT
    profit,
    purchase_price,
    cpu,
    gpu,
    valuation_source,
    reason
FROM decisions
WHERE
    created_at >= '2026-10-03T22:00:00'
    AND decision='REJECT'
    AND profit IS NOT NULL
ORDER BY profit DESC
LIMIT 15;
"


echo
echo "11. MARKET DB"
echo "------------------------------------------------------------"

sqlite3 market.db "
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN active=1 THEN 1 ELSE 0 END) AS active,
    SUM(CASE WHEN active=0 THEN 1 ELSE 0 END) AS inactive,
    COALESCE(SUM(price_changes),0) AS price_changes
FROM market_offers;
"


echo
echo "12. TIMER"
echo "------------------------------------------------------------"

systemctl list-timers olx-bot.timer --no-pager

echo
echo "============================================================"
echo "KONIEC RAPORTU"
echo "============================================================"
