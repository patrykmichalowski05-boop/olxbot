import json
import sqlite3
from pathlib import Path

import pytest

from flipradar_legacy_bridge import LegacyBridge


def make_db(path, ddl, rows):
    with sqlite3.connect(path) as c:
        c.executescript(ddl)
        for sql, args in rows:
            c.execute(sql, args)


@pytest.fixture
def legacy(tmp_path):
    make_db(tmp_path / 'offer_snapshots.db', '''
        CREATE TABLE snapshots (id INTEGER PRIMARY KEY, offer_key TEXT, title TEXT, url TEXT,
            price REAL, created_at TEXT, details_json TEXT, valuation_json TEXT, action_json TEXT);
    ''', [
        ("INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?,?)", (1,'OLX:A','RTX 3070', 'https://www.olx.pl/oferta/1',1000,'2026-10-01','{}',json.dumps({'profit': 300, 'roi': 25}),json.dumps({'action':'WATCH'}))),
        ("INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?,?)", (2,'OLX:A','RTX 3070', 'https://www.olx.pl/oferta/1',900,'2026-10-02','{}',json.dumps({'profit': 500, 'roi': 50}),json.dumps({'action':'BUY'}))),
        ("INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?,?)", (3,'OLX:B','Laptop', 'https://www.olx.pl/oferta/2',1600,'2026-10-02','{}',json.dumps({'profit': 150, 'roi': 8}),json.dumps({'action':'SKIP'}))),
        ("INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?,?)", (4,'FB:C','BMW e90', 'https://www.facebook.com/marketplace/3',6000,'2026-10-02','{}',json.dumps({'profit': 900, 'roi': 12}),json.dumps({'action':'WATCH'}))),
    ])
    make_db(tmp_path / 'deal_crm.db', '''
        CREATE TABLE deals(id INTEGER PRIMARY KEY, offer_key TEXT, alert_id INT, title TEXT, url TEXT, status TEXT, created_at TEXT);
        CREATE TABLE sale_prep_costs(id INTEGER PRIMARY KEY, offer_key TEXT, cost REAL);
        CREATE TABLE sale_plans(id INTEGER PRIMARY KEY, offer_key TEXT, target_price REAL, minimum_price REAL);
        CREATE TABLE sale_listings(id INTEGER PRIMARY KEY, offer_key TEXT, listed_price REAL);
    ''', [
        ('INSERT INTO deals VALUES (?,?,?,?,?,?,?)', (1,'OLX:A',101,'RTX 3070', 'https://www.olx.pl/oferta/1','LISTED','2026-10-02')),
        ('INSERT INTO deals VALUES (?,?,?,?,?,?,?)', (2,'FB:C',103,'BMW e90', 'https://www.facebook.com/marketplace/3','BOUGHT','2026-10-02')),
        ('INSERT INTO sale_prep_costs VALUES (?,?,?)', (1,'OLX:A',75)),
        ('INSERT INTO sale_prep_costs VALUES (?,?,?)', (2,'OLX:A',25)),
        ('INSERT INTO sale_plans VALUES (?,?,?,?)', (1,'OLX:A',1650,1450)),
        ('INSERT INTO sale_listings VALUES (?,?,?)', (1,'OLX:A',1600)),
    ])
    make_db(tmp_path / 'flip_results.db', '''
        CREATE TABLE flips(id INTEGER PRIMARY KEY, alert_id INT, purchase_price REAL, extra_cost REAL, sale_price REAL);
    ''', [
        ('INSERT INTO flips VALUES (?,?,?,?,?)',(1,101,900,60,None)),
    ])
    return LegacyBridge(tmp_path)


def test_radar_enforces_filters_before_pagination(legacy):
    p = legacy.radar(limit=1, max_price_minor=100_000, min_profit_minor=40_000, min_roi_bps=3000)
    assert [i['snapshot_id'] for i in p['items']] == [2]
    assert p['items'][0]['price_minor'] == 90_000
    assert p['items'][0]['profit_minor'] == 50_000
    assert p['next_before_id'] == 2
    nxt = legacy.radar(limit=1, before_id=p['next_before_id'], min_profit_minor=40_000)
    assert nxt['items'] == []
    assert nxt['next_before_id'] is None


def test_radar_platform_category_and_latest_snapshot(legacy):
    page = legacy.radar(platform='FACEBOOK', category='CAR', min_price_minor=500_000)
    assert len(page['items']) == 1
    assert page['items'][0]['offer_key'] == 'FB:C'
    all_rows = legacy.radar()['items']
    assert [r['snapshot_id'] for r in all_rows] == [4,3,2]


def test_legacy_deals_use_real_records_and_real_costs(legacy):
    page = legacy.deals()
    assert [r['id'] for r in page['items']] == ['legacy-2','legacy-1']
    item = legacy.deal('legacy-1')
    assert item['purchase_minor'] == 90_000
    assert item['cost_minor'] == 16_000
    assert item['target_price_minor'] == 165_000
    assert item['listed_price_minor'] == 160_000
    assert item['status'] == 'LISTED'
    assert item['realized_profit_minor'] is None


def test_invalid_ids_and_missing_databases(tmp_path, legacy):
    with pytest.raises(ValueError):
        legacy.deal('../etc/passwd')
    with pytest.raises(ValueError):
        legacy.radar(min_profit_minor=-1)
    with pytest.raises(FileNotFoundError):
        LegacyBridge(tmp_path / 'missing').deals()
    assert legacy.deal('legacy-9999') is None


def test_missing_optional_financial_tables(tmp_path):
    make_db(tmp_path / 'deal_crm.db', 'CREATE TABLE deals(id INTEGER PRIMARY KEY, offer_key TEXT, alert_id INT, title TEXT, url TEXT, status TEXT, created_at TEXT);', [
        ('INSERT INTO deals VALUES (?,?,?,?,?,?,?)',(5,'OLX:X',11,'Test',None,'BOUGHT','2026-10-02')),
    ])
    x = LegacyBridge(tmp_path).deals()['items'][0]
    assert x['id'] == 'legacy-5'
    assert not x['financials_complete']
    assert x['realized_profit_minor'] is None


def test_sale_profit_keeps_real_costs_and_losses(legacy):
    with sqlite3.connect(legacy.root / 'deal_crm.db') as db:
        db.execute("UPDATE deals SET status='SOLD' WHERE id=1")
    with sqlite3.connect(legacy.root / 'flip_results.db') as db:
        db.execute('UPDATE flips SET sale_price=1000 WHERE id=1')
    item = legacy.deal('legacy-1')
    assert item['financials_complete'] is True
    assert item['sale_minor'] == 100000
    assert item['realized_profit_minor'] == -6000


def test_invalid_purchase_is_unknown_rather_than_zero_profit(legacy):
    with sqlite3.connect(legacy.root / 'flip_results.db') as db:
        db.execute('UPDATE flips SET purchase_price=? WHERE id=1', ('invalid',))
    assert legacy.deal('legacy-1')['financials_complete'] is False
