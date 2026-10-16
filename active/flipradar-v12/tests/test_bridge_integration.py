"""HTTP/SQLite contracts for the GUI bridge; existing V10 services are explicit test doubles."""
from __future__ import annotations

import importlib.util
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from html.parser import HTMLParser
import sqlite3
import sys
from types import ModuleType
from urllib.parse import quote, urlsplit

import pytest
from flask import Flask, session
from test_legacy_data import legacy as legacy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
BRIDGE = Path(__file__).resolve().parents[1] / 'v12_bridge.py'
HEADERS = {'X-FlipRadar-Client': 'portal', 'Origin': 'http://localhost'}


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(BRIDGE.parent))
    database = tmp_path / 'accounts.sqlite3'
    def connect():
        db = sqlite3.connect(database, timeout=15)
        db.row_factory = sqlite3.Row
        return db
    with connect() as db:
        db.executescript('''
          CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT,email TEXT,role TEXT,state TEXT,version INTEGER);
          INSERT INTO users VALUES(1,'alice','alice@example.test','user','active',1);
          INSERT INTO users VALUES(2,'bob','bob@example.test','user','active',1);
          CREATE TABLE workspace_searches_v4(id INTEGER PRIMARY KEY,owner_id INTEGER,source TEXT,query_text TEXT,active INTEGER);
          INSERT INTO workspace_searches_v4 VALUES(101,1,'olx','Komputer',1);
          INSERT INTO workspace_searches_v4 VALUES(102,2,'olx','Komputer',1);
          CREATE TABLE guide_settings_v7(owner_id INTEGER,sid INTEGER,category TEXT,budget INTEGER,since TEXT,PRIMARY KEY(owner_id,sid));
          INSERT INTO guide_settings_v7 VALUES(1,101,'pc',3000,NULL);
          CREATE TABLE user_search_state_v9(owner_id INTEGER,sid INTEGER,status TEXT,last_attempt_utc TEXT,matches_count INTEGER,last_error TEXT);
          INSERT INTO user_search_state_v9 VALUES(1,101,'OK','2026-10-16T20:00:00Z',70,NULL);
          CREATE TABLE user_search_offers_v9(owner_id INTEGER,sid INTEGER,source TEXT,listing_id TEXT,title TEXT,url TEXT,price_zl NUMERIC,last_seen_utc TEXT);
          CREATE TABLE monitor_v8_alerts(id INTEGER PRIMARY KEY,owner_id INTEGER,title TEXT,source TEXT,url TEXT,price_zl NUMERIC,created_utc TEXT,read_utc TEXT,listing_id TEXT);
        ''')
        for i in range(1, 71):
            db.execute('INSERT INTO user_search_offers_v9 VALUES(?,?,?,?,?,?,?,?)', (1,101,'olx',str(i),f'Komputer {i}','https://www.olx.pl/d/oferta/test.html',1900.99,'2026-10-16T20:00:00Z'))
        db.execute('INSERT INTO user_search_offers_v9 VALUES(?,?,?,?,?,?,?,?)', (2,102,'olx','foreign','Komputer Boba','https://www.olx.pl/d/oferta/other.html',2000,'2026-10-16T20:00:00Z'))
        for i in range(1, 66):
            db.execute('INSERT INTO monitor_v8_alerts VALUES(?,?,?,?,?,?,?,?,?)', (i,1,f'Alert {i}','olx',None,1000,'2026-10-16T20:00:00Z',None,str(i)))
        db.execute('INSERT INTO monitor_v8_alerts VALUES(?,?,?,?,?,?,?,?,?)', (66,2,'Prywatny alert Boba','olx',None,1000,'2026-10-16T20:00:00Z',None,'bob'))
    users = ModuleType('multiuser_v2')
    users._connect = connect
    users.utcnow = lambda: '2026-10-16T20:00:00Z'
    users.throttle = lambda *args: True
    users.ensure_csrf_token = lambda: None
    def get_user(uid):
        with connect() as db:
            row = db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
            return dict(row) if row else None
    users.get_user = get_user
    def identity():
        if not session.get('authenticated'): return None
        if session.get('flip_root_v2'): return {'root': True, 'role': 'admin', 'state': 'active'}
        row = get_user(session.get('flip_uid_v2',-1))
        return row if row and row['state']=='active' and row['version']==session.get('flip_ver_v2') else None
    users.current_identity = identity
    accounts = ModuleType('accounts_v10')
    def authenticate(email,password):
        if password != 'temporary-test-password': return None
        with connect() as db:
            row = db.execute('SELECT * FROM users WHERE email=? AND state=?',(email,'active')).fetchone()
            return dict(row) if row else None
    accounts.authenticate = authenticate
    accounts.deleted = []
    accounts._remove_account = lambda uid: accounts.deleted.append(uid)
    monkeypatch.setitem(sys.modules,'multiuser_v2',users)
    monkeypatch.setitem(sys.modules,'accounts_v10',accounts)
    spec=importlib.util.spec_from_file_location('gui_bridge_contract',BRIDGE)
    bridge=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    dist=tmp_path/'dist'
    for name in ('index.html','login.html','register.html','account.html','bot.html','radar/index.html','market/index.html','searches/results.html','offer/[id].html','flips/[dealId].html','purchase/[listingId].html'):
        path=dist/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('<div id="root">FlipRadar</div>')
    font=dist/'assets/icons.ttf';font.parent.mkdir(parents=True);font.write_bytes(b'font-test')
    bridge.LEGACY_ROOT=tmp_path
    bridge.DIST=dist
    bridge.FLAG=tmp_path/'enabled';bridge.FLAG.touch()
    def app(preview=False):
        result=Flask(__name__);result.secret_key='temporary-contract-test';result.config['TESTING']=True
        result.add_url_rule('/centrum','legacy',lambda:'existing tools')
        bridge.install(result,preview=preview)
        return result
    return bridge, app, connect, users, accounts


def signed_client(app, uid=1, root=False):
    client=app.test_client()
    with client.session_transaction() as cookie:
        cookie['authenticated']=True
        if root: cookie['flip_root_v2']=True
        else: cookie.update(flip_uid_v2=uid,flip_ver_v2=1)
    return client


def test_existing_session_login_and_resume_contract(runtime):
    bridge, make_app, _, _, _=runtime
    client=make_app().test_client()
    assert client.get('/api/v1/portal/me').status_code==401
    assert client.get('/api/v1/portal/me',headers={'Authorization':'Bearer flask-session'}).status_code==401
    response=client.post('/api/v1/portal/auth/login',json={'username':'alice@example.test','password':'temporary-test-password'},headers=HEADERS)
    assert response.status_code==200
    assert client.post('/api/v1/portal/auth/resume',headers=HEADERS).status_code==200
    assert client.get('/api/v1/portal/me').json['username']=='alice'
    assert client.post('/api/v1/portal/auth/logout',headers=HEADERS).status_code==200
    assert client.get('/api/v1/me').status_code==401


@pytest.mark.parametrize('headers',[{}, {'X-FlipRadar-Client':'portal','Origin':'https://evil.test'}, {'Origin':'http://localhost'}])
def test_cross_origin_writes_rejected(runtime,headers):
    _,make_app,_,_,_=runtime
    client=make_app().test_client()
    assert client.post('/api/v1/portal/auth/login',json={'username':'alice@example.test','password':'temporary-test-password'},headers=headers).status_code==403


def test_radar_pagination_cents_and_owner_scope(runtime):
    _,make_app,_,_,_=runtime
    client=signed_client(make_app())
    seen=[];cursor=None
    while True:
        response=client.get('/api/v1/universal/mobile-radar',query_string={'limit':30,**({'before_id':cursor} if cursor else {})})
        assert response.status_code==200
        result=response.json
        assert all(row['price_minor']==190099 for row in result['items'])
        seen.extend(row['snapshot_id'] for row in result['items'])
        cursor=result['next_before_id']
        if cursor is None: break
    assert len(seen)==len(set(seen))==70
    assert 71 not in seen
    assert client.get('/api/v1/universal/mobile-radar/71').status_code==404
    assert client.get('/api/v1/universal/mobile-radar?q=Komputer%201').json['items']


@pytest.mark.parametrize('query',[{'limit':'bad'},{'limit':'0'},{'before_id':'-1'},{'before_id':'not-an-id'}])
def test_invalid_cursor_returns_json_error(runtime,query):
    _,make_app,_,_,_=runtime
    response=signed_client(make_app()).get('/api/v1/universal/mobile-radar',query_string=query)
    assert response.status_code==400
    assert response.is_json
    assert 'Traceback' not in response.text


def test_notification_cursor_is_private_and_complete(runtime):
    _,make_app,_,_,_=runtime
    client=signed_client(make_app());seen=[];cursor=None
    while True:
        page=client.get('/api/v1/portal/notifications',query_string={'before_id':cursor} if cursor else {}).json
        seen.extend(row['id'] for row in page['items'])
        cursor=page['next_before_id']
        if cursor is None:break
    assert len(seen)==len(set(seen))==65
    assert '66' not in seen


def test_exported_dynamic_pages_and_assets(runtime):
    bridge,make_app,_,_,_=runtime
    app=make_app();client=signed_client(app)
    for path in ('/offer/snap-1','/flips/123','/purchase/123','/searches/results?id=101','/market'):
        assert client.get(path).status_code==200,path
    anonymous=app.test_client()
    assert anonymous.get('/offer/snap-1').status_code==302
    assert 'next=' in anonymous.get('/offer/snap-1').location
    assert client.get('/assets/icons.ttf').data==b'font-test'
    assert client.get('/centrum?tab=dashboard').data==b'existing tools'


def test_actual_export_pages_and_all_local_assets_are_served(runtime):
    from build_ui import validate_export
    bridge, make_app, _, _, _ = runtime
    export = BRIDGE.parent / 'dist'
    validate_export(export)
    bridge.DIST = export
    client = signed_client(make_app())

    class LocalAssets(HTMLParser):
        paths = set()
        def handle_starttag(self, tag, attrs):
            for name, value in attrs:
                if name == 'src' or (tag == 'link' and name == 'href'):
                    if value and value.startswith(('/assets/', '/_expo/')):
                        self.paths.add(urlsplit(value).path)

    for route in ('/', '/login', '/account', '/radar', '/searches', '/searches/results', '/market', '/offer/snap-7', '/flips/legacy-1'):
        page = client.get(route)
        assert page.status_code == 200, route
        assert 'Content-Security-Policy' in page.headers
        LocalAssets().feed(page.get_data(as_text=True))
    assert any(path.endswith('.js') for path in LocalAssets.paths)
    assert any(path.endswith('.css') for path in LocalAssets.paths)
    files = [*export.glob('assets/**/*'), *export.glob('_expo/static/**/*')]
    assert any(path.name.startswith('Ionicons.') for path in files)
    for path in files:
        if path.is_file():
            relative = '/' + path.relative_to(export).as_posix()
            response = client.get(quote(relative, safe='/@'))
            assert response.status_code == 200, relative
            assert len(response.data) == path.stat().st_size, relative
    for path in LocalAssets.paths:
        assert client.get(path).status_code == 200, path


def test_preview_capabilities_and_write_protection(runtime):
    _,make_app,connect,_,accounts=runtime
    client=signed_client(make_app(preview=True),root=True)
    config=client.get('/api/v1/public/config').json
    assert config['capabilities']['read_only'] is True
    assert config['registration_enabled'] is False
    for key in ('watchlist','manual_analysis','deals','plan_requests','admin_access','account_delete'):
        assert config['capabilities'][key] is False
    assert client.put('/api/v1/universal/searches/new',json={'query':'Test'},headers=HEADERS).status_code==403
    assert client.post('/api/v1/portal/admin/delete',json={'user_id':1,'confirm':'alice'},headers=HEADERS).status_code==403
    assert accounts.deleted==[]
    assert client.post('/api/v1/portal/auth/resume',headers=HEADERS).status_code==200


def test_search_retry_and_limits_are_atomic(runtime):
    _,make_app,connect,_,_=runtime
    app=make_app();client=signed_client(app)
    body={'query':'RTX 4070','name':'RTX 4070','platforms':['OLX'],'category':'gpu','max_price_minor':200000,'enabled':True}
    for _ in range(2):
        response=client.put('/api/v1/universal/searches/client-attempt',json=body,headers=HEADERS)
        assert response.status_code==200,response.text
    assert len(client.get('/api/v1/universal/searches').json['items'])==2
    assert client.get('/api/v1/portal/me').json['access']['remaining']==1
    def save(i):
        return signed_client(app).put(f'/api/v1/universal/searches/parallel-{i}',json=body,headers=HEADERS).status_code
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(save,range(4)))
    assert results.count(200)==1
    assert results.count(403)==3
    with connect() as db:
        assert db.execute('SELECT COUNT(*) FROM workspace_searches_v4 WHERE owner_id=1').fetchone()[0]==3


def test_foreign_profile_and_disabled_session_are_rejected(runtime):
    _,make_app,connect,_,_=runtime
    client=signed_client(make_app())
    response=client.put('/api/v1/universal/searches/102',json={'query':'Komputer','platforms':['OLX']},headers=HEADERS)
    assert response.status_code==404
    with connect() as db: db.execute('UPDATE users SET version=2 WHERE id=1')
    assert client.get('/api/v1/portal/me').status_code==401


def test_unavailable_operations_are_explicit(runtime):
    _,make_app,_,_,_=runtime
    client=signed_client(make_app())
    assert client.get('/api/v1/universal/watchlist').status_code==501
    assert client.post('/api/v1/public/search',json={'query':'RTX'},headers=HEADERS).status_code==501
    assert client.get('/api/v1/public/config').json['capabilities']['search_platforms']==['OLX']


def test_root_legacy_radar_and_inventory_use_existing_admin_session(runtime, legacy):
    bridge, make_app, _, _, _ = runtime
    bridge.LEGACY_ROOT = legacy.root
    app = make_app()
    anonymous = app.test_client()
    member = signed_client(app)
    admin = signed_client(app, root=True)
    assert anonymous.get('/api/v2/workspaces/legacy/deals').status_code == 403
    assert member.get('/api/v2/workspaces/legacy/deals').status_code == 403
    result = admin.get('/api/v2/workspaces/legacy/deals')
    assert result.status_code == 200
    assert result.json['items'][0]['id'] == 'legacy-2'
    assert admin.get('/api/v2/workspaces/legacy/deals/legacy-1').json['purchase_minor'] == 90000
    filtered = admin.get('/api/v1/universal/mobile-radar?limit=1&max_price_minor=100000&min_profit_minor=40000')
    assert filtered.status_code == 200
    assert [item['snapshot_id'] for item in filtered.json['items']] == [2]
    assert admin.get('/api/v1/universal/mobile-radar/2').json['title'] == 'RTX 3070'
    assert admin.get('/api/v1/portal/me').json['capabilities']['radar_scope'] == 'global'
    assert admin.get('/api/v1/portal/me').json['capabilities']['deals_read'] is True
    assert member.get('/api/v1/portal/me').json['capabilities']['deals_read'] is False
    assert all(item['title'].startswith('Komputer') for item in member.get('/api/v1/universal/mobile-radar').json['items'])


def test_stage_reinstall_never_reuses_writable_live_mode(runtime):
    bridge, make_app, _, _, _ = runtime
    app = make_app()
    bridge.install(app, preview=True)
    client = signed_client(app)
    assert client.get('/api/v1/public/config').json['capabilities']['read_only'] is True
    assert client.put('/api/v1/universal/searches/new', json={'query': 'RTX 4070', 'platforms': ['OLX']}, headers=HEADERS).status_code == 403
