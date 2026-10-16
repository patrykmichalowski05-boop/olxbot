#!/bin/bash

set -e

cd /opt/olx-bot
source venv/bin/activate


echo
echo "========================================"
echo "1. PYTHON COMPILE"
echo "========================================"
python -m py_compile \
    scanner.py \
    database.py \
    fast_db.py \
    fast_scanner.py \
bundle_fast_scanner.py \
deep_worker.py \
priority_queue.py \
candidate_prefilter.py \
bundle_detector.py \
bundle_valuation.py \
    offer_parser.py \
    price_resolver.py \
    filters.py \
    browser_utils.py \
    valuation.py \
    valuation_v2.py \
    valuation_v3.py \
    market_db.py \
    market_stats.py \
    market_lifecycle.py \
    market_collector.py \
    market_collector_v2.py \
    similarity_engine.py \
    similarity_engine_v2.py \
    spec_recovery.py \
    ai_analyzer.py \
    telegram_notifier.py \
    decision_log.py \
    decision_report.py \
    decision_inspect.py \
    watchdog.py
echo
echo "Kompilacja: OK"


echo
echo "========================================"
echo "2. REGRESSION TESTS"
echo "========================================"

python -m unittest discover \
    -v \
    -s tests \
    -p "test_*.py"

echo
echo "========================================"
echo "3. TIMER"
echo "========================================"

echo -n "enabled: "
systemctl is-enabled olx-bot.timer 2>/dev/null || true

echo -n "active: "
systemctl is-active olx-bot.timer 2>/dev/null || true


echo
echo "========================================"
echo "OLX FLIP HUNTER — CHECK OK"
echo "========================================"
