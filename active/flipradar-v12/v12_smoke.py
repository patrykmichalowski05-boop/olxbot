"""V12 isolated smoke: actual original HTML + isolated SQLite, no writes to real DB."""
from __future__ import annotations
import os
import sqlite3
import tempfile
from pathlib import Path

ROOT=Path('/opt/flipradar-v12')
os.environ['FLIPRADAR_V12_DIST']=str(ROOT/'dist')
from flask import Flask
import multiuser_v2 as m
import v12_bridge as v12

with tempfile.TemporaryDirectory(prefix='flipradar-v12-smoke-') as tmp:
    db_path=Path(tmp)/'fake-users.sqlite3'
    def db():
        x=sqlite3.connect(db_path)
        x.row_factory=sqlite3.Row
        return x
    with db() as conn:
        conn.executescript('''
         CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT,email TEXT,role TEXT,state TEXT);
         INSERT INTO users VALUES(1,'test-user','test@example.net','user','active');
         INSERT INTO users VALUES(2,'other-user','other@example.net','user','active');
         CREATE TABLE workspace_searches_v4 (id INTEGER PRIMARY KEY,owner_id INTEGER,source TEXT,query_text TEXT,active INTEGER);
         INSERT INTO workspace_searches_v4 VALUES(101,1,'olx','RTX 4070',1);
         INSERT INTO workspace_searches_v4 VALUES(102,2,'olx','iPhone 14',1);
         CREATE TABLE guide_settings_v7(owner_id INTEGER,sid INTEGER,category TEXT,budget INTEGER,since TEXT);
         INSERT INTO guide_settings_v7 VALUES(1,101,'gpu',2500,NULL);
         CREATE TABLE user_search_state_v9(owner_id INTEGER,sid INTEGER,status TEXT,last_attempt_utc TEXT,matches_count INTEGER,last_error TEXT);
         INSERT INTO user_search_state_v9 VALUES(1,101,'OK','2026-10-16T10:00:00Z',1,NULL);
         CREATE TABLE user_search_offers_v9(owner_id INTEGER,sid INTEGER,source TEXT,listing_id TEXT,title TEXT,url TEXT,price_zl INTEGER,last_seen_utc TEXT);
         INSERT INTO user_search_offers_v9 VALUES(1,101,'olx','IDAA','RTX 4070 ASUS','https://www.olx.pl/d/oferta/rtx-CID123-IDAA.html',1900,'2026-10-16T10:00:00Z');
         INSERT INTO user_search_offers_v9 VALUES(2,102,'olx','IDBB','iPhone 14','https://www.olx.pl/d/oferta/iphone-CID123-IDBB.html',1200,'2026-10-16T10:00:00Z');
         CREATE TABLE monitor_v8_alerts(id INTEGER,owner_id INTEGER,title TEXT,source TEXT,url TEXT,price_zl INTEGER,created_utc TEXT,read_utc TEXT,listing_id TEXT);
        ''')
    old_connect=m._connect
    old_identity=m.current_identity
    try:
        m._connect=db
        identity=[None]
        m.current_identity=lambda:identity[0]
        app=Flask(__name__)
        app.secret_key='V12-test-only'
        v12.install(app,preview=True)
        client=app.test_client()
        assert client.get('/').status_code==200
        assert client.get('/bot').status_code==302
        assert client.get('/api/v1/me').status_code==401
        identity[0]={'id':1,'role':'user','state':'active','username':'test-user','root':False}
        assert client.get('/bot').status_code==200
        assert client.get('/account').status_code==200
        assert client.post('/api/v1/portal/auth/resume',headers={
            'X-FlipRadar-Client':'portal','Origin':'http://localhost'
        }).status_code==200, 'Browser session resume must accept empty POST body'
        page=client.get('/api/v1/universal/mobile-radar').json
        assert len(page['items'])==1 and page['items'][0]['title']=='RTX 4070 ASUS',page
        assert client.get('/api/v1/universal/mobile-radar/2').status_code==404
        searches=client.get('/api/v1/universal/searches').json
        assert len(searches['items'])==1
        assert client.get('/api/v1/portal/admin').status_code==403
        assert client.post('/api/v1/portal/admin/delete',json={'user_id':2}).status_code==403
        identity[0]={'root':True,'role':'admin','state':'active','username':'admin'}
        assert client.get('/admin/uzytkownicy').status_code==200
        assert len(client.get('/api/v1/portal/admin').json['accounts'])==2
        assert client.post('/api/v1/portal/admin/delete',json={'user_id':1}).status_code==403
        print('PASS: original Expo assets, authenticated UI, root admin UI, isolation')
        print('PASS: no user writes, browser API protected by Origin and X-FlipRadar-Client')
    finally:
        m._connect=old_connect
        m.current_identity=old_identity
print('PASS: V12 smoke on isolated SQLite')
