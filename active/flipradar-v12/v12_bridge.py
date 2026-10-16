"""FlipRadar V12.2: original Expo/React frontend served over existing Flask sessions.

This is a compatibility bridge, not a second authentication system.
No database migrations and no updates to scanner databases.
Unsupported mutations return HTTP 501 rather than fabricating success.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from flask import abort, jsonify, redirect, request, send_from_directory, session
from werkzeug.security import check_password_hash
import multiuser_v2 as m
from app_v2 import config
from app_v2.security import verify_credentials

DIST = Path(os.getenv('FLIPRADAR_V12_DIST', '/opt/flipradar-v12/dist'))
FLAG = Path('/opt/olx-bot-budget-dev/.v12_live')
CLIENT = 'portal'

# Only these routes are taken over by the original frontend; existing specialist
# tools /centrum, /dev/flip-hunter and Flask's old mutation routes remain intact.
PUBLIC_UI = {'/', '/login', '/register', '/rejestracja', '/info'}
PRIVATE_UI = {'/bot', '/radar', '/searches', '/watched', '/analyze', '/flips',
              '/settings', '/offer', '/purchase', '/analytics', '/notifications',
              '/account', '/market', '/admin/uzytkownicy'}
FRONTEND_ROUTES = PUBLIC_UI | PRIVATE_UI
PUBLIC_API = {'/api/v1/portal/auth/login','/api/v1/portal/auth/register',
              '/api/v1/portal/auth/resume','/api/v1/public/config',
              '/api/v1/public/search'}
OTHER_API = {'/api/v1/me','/api/v1/portal/me','/api/v1/portal/auth/logout',
             '/api/v1/portal/admin','/api/v1/portal/admin/access',
             '/api/v1/portal/admin/delete','/api/v1/portal/plan-requests',
             '/api/v1/portal/notifications','/api/v1/universal/mobile-radar',
             '/api/v1/universal/searches','/api/v1/universal/source-health',
             '/api/v1/universal/watchlist','/api/v1/universal/watchlist/close',
             '/api/v1/universal/manual/analyze'}


def _identity():
    u = m.current_identity()
    return u if u and u.get('state') == 'active' else None


def _json_body():
    if not request.is_json:
        abort(415, description='Wymagany JSON')
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description='Nieprawidłowy JSON')
    return data


def _unsafe_method_guard():
    # A custom header requires CORS preflight from a cross-site page; the app
    # deliberately sends NO Access-Control-Allow-Origin response.
    if request.headers.get('X-FlipRadar-Client') != CLIENT:
        abort(403, description='Brak nagłówka klienta')
    origin = request.headers.get('Origin')
    referer = request.headers.get('Referer')
    if origin:
        p = urlsplit(origin)
    elif referer:
        p = urlsplit(referer)
    else:
        abort(403, description='Brak Origin/Referer')
    if p.netloc != request.host or p.scheme not in ('http','https'):
        abort(403, description='Niedozwolony origin')
    # Body-free session resume/logout are valid POST requests; endpoints that
    # actually accept a payload validate JSON separately via _json_body().


def _error(message, status=400):
    return jsonify({'detail':message}), status


def _safe_url(url, source):
    p = urlsplit(str(url or ''))
    host = (p.hostname or '').lower()
    providers = {'olx': ('olx.pl',), 'facebook':('facebook.com','fb.com')}
    domains = providers.get(str(source).lower(), ())
    if p.scheme != 'https' or p.username or p.password:
        return None
    if not any(host == d or host.endswith('.'+d) for d in domains):
        return None
    return str(url)[:2000]


def _plan(u):
    if u.get('root') or u.get('role') == 'admin':
        return 'LEGACY', 'Administrator', None
    role = str(u.get('role') or 'user').casefold()
    if role in ('fliper','flipper'):
        return 'PLUS','Fliper',None
    if role in ('minifliper','mini_fliper','mini-fliper'):
        return 'STANDARD','MiniFliper',7
    return 'START','User',3


def _plans():
    # Zero is intentional, not an advertised commercial price.
    return [
        {'code':'START','name':'User','price_minor':0,'searches':3,'days':None,
         'notifications':True,'prices_are_examples':True},
        {'code':'STANDARD','name':'MiniFliper','price_minor':0,'searches':7,
         'days':None,'notifications':True,'prices_are_examples':True},
        {'code':'PLUS','name':'Fliper','price_minor':0,'searches':None,
         'days':None,'notifications':True,'prices_are_examples':True},
        {'code':'LEGACY','name':'Administrator','price_minor':0,'searches':None,
         'days':None,'notifications':True,'prices_are_examples':True},
    ]


def _account(u):
    code,name,limit = _plan(u)
    with m._connect() as db:
        used = int(db.execute('SELECT COUNT(*) FROM workspace_searches_v4 WHERE owner_id=?',
                              (u.get('id',-999),)).fetchone()[0]) if not u.get('root') else 0
    remaining = None if limit is None else max(0,limit-used)
    return {'user_id':str(u.get('id') or 'root'),
            'username':str(u.get('username') or ('admin' if u.get('root') else 'Użytkownik')),
            'role':'OWNER' if u.get('root') or u.get('role')=='admin' else 'MEMBER',
            'plan':{'code':code,'name':name,'price_minor':0,'searches':limit,'days':None,
                    'notifications':True,'prices_are_examples':True},
            'access':{'can_open_bot':True,'can_search':remaining is None or remaining>0,
                      'can_receive_notifications':True,'reason':'ACTIVE',
                      'remaining':remaining,'limit':limit,'used':used,'expires_at':None},
            'plan_request':None}


def _make_session(u):
    session.clear()
    session['authenticated'] = True
    if u.get('root'):
        session['flip_root_v2'] = True
    else:
        session['flip_uid_v2'] = int(u['id'])
        session['flip_ver_v2'] = int(u['version'])
    session.permanent = True
    if hasattr(m,'ensure_csrf_token'):
        m.ensure_csrf_token()
    return jsonify({'access_token':'flask-session', 'refresh_token':''})


def _login():
    data = _json_body()
    credential = str(data.get('username') or '').strip()
    password = str(data.get('password') or '')
    if not credential or not password:
        return _error('Podaj e-mail i hasło',400)
    if not m.throttle('login', 15, 900):
        return _error('Zbyt wiele prób logowania',429)
    # Existing root admin credentials stay owned by original server config.
    if verify_credentials(credential,password):
        return _make_session({'root':True})
    import accounts_v10
    user = accounts_v10.authenticate(credential,password)
    if not user:
        return _error('Nieprawidłowy e-mail lub hasło',401)
    return _make_session(user)


def _register():
    if not m.throttle('register',5,3600):
        return _error('Zbyt wiele prób rejestracji',429)
    data = _json_body()
    import accounts_v10
    try:
        accounts_v10.register_user(data.get('username'),data.get('email'),data.get('password'))
        u = accounts_v10.authenticate(data.get('email'),data.get('password'))
        if not u:
            raise ValueError('Nie można rozpocząć sesji')
    except ValueError as ex:
        return _error(str(ex),400)
    return _make_session(u)


def _radar_items(u, single=None):
    uid = int(u.get('id') or -1)
    params=[uid]
    where='WHERE o.owner_id=? AND s.active=1'
    if single is not None:
        where+=' AND o.rowid=?'
        params.append(int(single))
    q = str(request.args.get('q') or '')[:120].strip()
    if q and single is None:
        where+=' AND lower(o.title) LIKE ?'
        params.append('%'+q.casefold()+'%')
    limit = max(1,min(int(request.args.get('limit','30')) if single is None else 1,100))
    sql = '''SELECT o.rowid AS snapshot_id,o.title,o.price_zl,o.source,o.url,
                    o.last_seen_utc,o.sid,s.query_text,st.status
             FROM user_search_offers_v9 o
             JOIN workspace_searches_v4 s ON s.id=o.sid AND s.owner_id=o.owner_id
             LEFT JOIN user_search_state_v9 st ON st.sid=o.sid AND st.owner_id=o.owner_id
          '''+where+' ORDER BY o.rowid DESC LIMIT ?'
    params.append(limit)
    with m._connect() as db:
        rows=[dict(r) for r in db.execute(sql,params)]
    return [{'snapshot_id':int(r['snapshot_id']),
             'offer_key':f"{r['source']}:{r['snapshot_id']}",
             'decision':'REVIEW','valuation':{},'observed_at':r['last_seen_utc'],
             'title':r['title'],'platform':r['source'].upper(),
             'price_minor':int(r['price_zl'])*100 if r['price_zl'] is not None else None,
             'url':_safe_url(r['url'],r['source']), 'currency':'PLN',
             'source_status':r.get('status') or 'UNKNOWN'} for r in rows]


def _searches(u):
    with m._connect() as db:
        rows=[dict(r) for r in db.execute('''
         SELECT s.id,s.query_text,s.source,s.active,
                COALESCE(g.category,'other') AS category,
                g.budget,g.since
         FROM workspace_searches_v4 s
         LEFT JOIN guide_settings_v7 g ON g.owner_id=s.owner_id AND g.sid=s.id
         WHERE s.owner_id=? ORDER BY s.id DESC LIMIT 150
        ''',(int(u.get('id') or -1),))]
    return [{'id':str(r['id']),'name':r['query_text'],'query':r['query_text'],
             'platforms':[str(r['source']).upper()],
             'category':str(r['category'] or 'other'),
             'purpose':'cheap','max_price_minor':int(r['budget'])*100 if r['budget'] else None,
             'min_profit_minor':0,'min_roi_bps':0,'enabled':bool(r['active']),
             'notify_initial':bool(r['since']),'excluded_terms':[],
             'costs':{'shipping_minor':0,'repairs_minor':0,'travel_minor':0,
                      'other_minor':0,'sale_fee_bps':0,'reserve_bps':0}} for r in rows]


def _searches_update(u, path):
    """Write one OLX radar into V4, with idempotency protection for retries."""
    if request.method != 'PUT': abort(405)
    body=_json_body()
    uid=int(u.get('id') or -1)
    if uid<=0:
        return _error('Administrator musi użyć zwykłego konta do prywatnych radarów',403)
    query=' '.join(str(body.get('query') or '').split())[:120]
    if len(query)<3:return _error('Fraza musi mieć co najmniej 3 znaki',400)
    sources=body.get('platforms')
    if sources!=['OLX']:
        return _error('Wyszukiwania na żywo V9 obsługują na razie wyłącznie OLX. '
                      'Pozostałe platformy wymagają integracji.',422)
    budget_minor=body.get('max_price_minor')
    if budget_minor is not None and (type(budget_minor) is not int or
                                    budget_minor<0 or budget_minor>100_000_000):
        return _error('Nieprawidłowy budżet',400)
    budget=budget_minor//100 if budget_minor else 0
    active=bool(body.get('enabled',True))
    candidate_id=path.rsplit('/',1)[-1]
    if not candidate_id or len(candidate_id)>100:abort(400)
    _,_,limit=_plan(u)
    now=m.utcnow()
    with m._connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS workspace_v12_requests (
           owner_id INTEGER NOT NULL, client_key TEXT NOT NULL,
           sid INTEGER NOT NULL, PRIMARY KEY(owner_id, client_key))''')
        record=None
        if candidate_id.isdigit():
            sid=int(candidate_id)
            record=db.execute('''SELECT id FROM workspace_searches_v4
                         WHERE id=? AND owner_id=?''',(sid,uid)).fetchone()
            if not record:abort(404)
        else:
            mapped=db.execute('''SELECT sid FROM workspace_v12_requests
                         WHERE owner_id=? AND client_key=?''',(uid,candidate_id)).fetchone()
            if mapped:
                sid=int(mapped['sid'])
                record=db.execute('''SELECT id FROM workspace_searches_v4
                         WHERE id=? AND owner_id=?''',(sid,uid)).fetchone()
                if not record:return _error('Radar już nie istnieje; odśwież stronę',409)
        cols={r['name']:r for r in db.execute('PRAGMA table_info("workspace_searches_v4")')}
        data={'query_text':query,'source':'olx','active':1 if active else 0}
        if 'title' in cols:data['title']=query
        if 'name' in cols:data['name']=query
        if 'updated_at' in cols:data['updated_at']=now
        if 'max_price' in cols:data['max_price']=budget
        if 'min_price' in cols:data['min_price']=0
        if record:
            keys=[k for k in data if k in cols]
            assignments=', '.join(f'"{k}"=?' for k in keys)
            db.execute(f'''UPDATE workspace_searches_v4 SET {assignments}
                WHERE id=? AND owner_id=?''',[data[k] for k in keys]+[sid,uid])
        else:
            total=db.execute('''SELECT COUNT(*) FROM workspace_searches_v4
                  WHERE owner_id=?''',(uid,)).fetchone()[0]
            if limit is not None and total>=limit:
                return _error('Osiągnięto limit radarów w pakiecie',403)
            data['owner_id']=uid
            if 'created_at' in cols:data['created_at']=now
            for name,col in cols.items():
                if name=='id' or name in data:continue
                if col['notnull'] and col['dflt_value'] is None:
                    return _error('Nieznana wymagana kolumna V4: '+name+
                                  '. Zapisz radar w /centrum i podeślij strukturę.',409)
            keys=[k for k in data if k in cols]
            assignments=','.join('"'+k+'"' for k in keys)
            placeholders=','.join('?' for _ in keys)
            cur=db.execute(f'''INSERT INTO workspace_searches_v4 ({assignments})
                         VALUES ({placeholders})''',[data[k] for k in keys])
            sid=int(cur.lastrowid)
            db.execute('''INSERT INTO workspace_v12_requests(owner_id,client_key,sid)
                          VALUES(?,?,?)''',(uid,candidate_id,sid))
        category=str(body.get('category') or 'other').lower()
        if category not in ('gpu','pc','phone','laptop','other'):category='other'
        db.execute('''INSERT INTO guide_settings_v7
            (owner_id,sid,category,budget,since) VALUES(?,?,?,?,?)
            ON CONFLICT(owner_id,sid) DO UPDATE SET
             category=excluded.category,budget=excluded.budget''',
            (uid,sid,category,budget,None))
    matching=next((x for x in _searches(u) if x['id']==str(sid)),None)
    if not matching:return _error('Nie można odczytać zapisanego radaru',500)
    return jsonify(matching)


def _source_health(u):
    with m._connect() as db:
        rows=[dict(r) for r in db.execute('''SELECT v.sid,v.status,
            COALESCE(v.matches_count,0) AS count,v.last_attempt_utc,
            COALESCE(v.last_error,'') AS error,s.source
            FROM user_search_state_v9 v
            JOIN workspace_searches_v4 s ON s.id=v.sid AND s.owner_id=v.owner_id
            WHERE v.owner_id=?''',(int(u.get('id') or -1),))]
    return {'items':[{'search_id':str(r['sid']),'platform':str(r['source']).upper(),
                      'status':r['status'],'message':r['error'],
                      'checked_at':r['last_attempt_utc'] or '', 'count':r['count']} for r in rows],
            'notifications':{}}


def _inbox(u):
    with m._connect() as db:
        rows=[dict(r) for r in db.execute('''SELECT id,title,source,url,price_zl,created_utc,
            read_utc,listing_id FROM monitor_v8_alerts WHERE owner_id=?
            ORDER BY id DESC LIMIT 30''',(int(u.get('id') or -1),))]
    items=[]
    for r in rows:
        items.append({'id':str(r['id']),'category':'Nowa oferta',
                      'title':r['title'],
                      'reason':f"{str(r['source']).upper()} · {r['price_zl']} zł",
                      'at':r['created_utc']})
    return {'items':items,'next_before_id':None}


def _admin_data(u):
    if not (u.get('root') or u.get('role')=='admin'):
        abort(403)
    with m._connect() as db:
        rows=[dict(r) for r in db.execute('''SELECT id,username,role,state
                        FROM users ORDER BY id DESC LIMIT 500''')]
    accounts=[]
    for r in rows:
        code,_,_= _plan(r)
        accounts.append({'user_id':str(r['id']),'username':r['username'],
                        'role':'OWNER' if r['role']=='admin' else 'MEMBER',
                        'enabled':1 if r['state']=='active' else 0,
                        'plan':code,'used':0,'expires_at':None})
    return {'accounts':accounts,'requests':[]}


def _admin_delete(u):
    if not u.get('root') and u.get('role')!='admin':
        abort(403)
    data=_json_body()
    try: uid=int(data.get('user_id') or 0)
    except (ValueError,TypeError): abort(400)
    target=m.get_user(uid)
    if not target or uid<=0: abort(404)
    if target.get('role')=='admin' and not u.get('root'): abort(403)
    if target.get('id') == u.get('id'): abort(403)
    if data.get('confirm') != target['username']:
        return _error('Wpisz dokładnie login użytkownika',400)
    import accounts_v10
    accounts_v10._remove_account(uid)
    return jsonify({'ok':True})


def _admin_access(u):
    if not u.get('root') and u.get('role')!='admin':abort(403)
    # Existing account administration remains the authoritative mutator.
    return _error('Zmianę roli i dostępu wykonaj w administracji V10: /admin/uzytkownicy?legacy=1.',501)


def _api(path, *, read_only=False):
    if request.method in ('POST','PUT','PATCH','DELETE'):
        _unsafe_method_guard()
        if read_only and path not in ('/api/v1/portal/auth/login',
                '/api/v1/portal/auth/logout','/api/v1/portal/auth/resume',
                '/api/v1/public/search'):
            return _error('Podgląd V12 jest tylko do odczytu. Nie zapisuje danych produkcyjnych.',403)
    elif request.method not in ('GET','HEAD'):
        abort(405)
    if path == '/api/v1/public/config':
        return jsonify({'demo_data':False,'registration_enabled':True,
           'public_search_available':False,'payment_mode':'MANUAL','plans':_plans()})
    if path == '/api/v1/public/search':
        d=_json_body(); q=str(d.get('query') or '')[:120]
        return jsonify({'query':q,'remaining':None,'items':[],'example':False})
    if path == '/api/v1/portal/auth/login' and request.method=='POST':return _login()
    if path == '/api/v1/portal/auth/register' and request.method=='POST':return _register()
    u=_identity()
    if not u:
        return _error('Unauthorized',401)
    if path == '/api/v1/portal/auth/resume' and request.method=='POST':
        return jsonify({'access_token':'flask-session','refresh_token':''})
    if path == '/api/v1/portal/auth/logout' and request.method=='POST':
        session.clear();return jsonify({'ok':True})
    if path == '/api/v1/me':return jsonify({'user_id':str(u.get('id') or 'root')})
    if path == '/api/v1/portal/me':return jsonify(_account(u))
    if path == '/api/v1/portal/admin':return jsonify(_admin_data(u))
    if path == '/api/v1/portal/admin/delete' and request.method=='POST':return _admin_delete(u)
    if path == '/api/v1/portal/admin/access' and request.method=='POST':return _admin_access(u)
    if path == '/api/v1/portal/plan-requests' and request.method=='POST':
        return _error('Pakiety zarządzane są w obecnym panelu administratora',501)
    if path == '/api/v1/universal/mobile-radar':
        return jsonify({'items':_radar_items(u),'next_before_id':None})
    if path.startswith('/api/v1/universal/mobile-radar/'):
        try: snapshot_id=int(path.rsplit('/',1)[-1])
        except ValueError:abort(404)
        rows=_radar_items(u,single=snapshot_id)
        if not rows:abort(404)
        return jsonify(rows[0])
    if path=='/api/v1/universal/searches':return jsonify({'items':_searches(u)})
    if path.startswith('/api/v1/universal/searches/'):
        return _searches_update(u,path)
    if path=='/api/v1/universal/source-health':return jsonify(_source_health(u))
    if path=='/api/v1/portal/notifications':return jsonify(_inbox(u))
    if path=='/api/v1/universal/watchlist' and request.method=='GET':
        return jsonify({'items':[]})
    return _error('Ta funkcja wymaga kolejnego adaptera danych V12. Nie są pokazywane fałszywe dane.',501)


def _asset(path):
    p=(DIST/path).resolve()
    if not p.is_relative_to(DIST.resolve()) or not p.is_file(): abort(404)
    result=send_from_directory(str(DIST),path,conditional=True)
    result.headers['X-Content-Type-Options']='nosniff'
    result.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    if p.suffix=='.html':
        result.headers['Cache-Control']='no-store, private'
        # V11's startup preflight expects CSP on the public landing. Expo's
        # static export also needs inline bootstrapping styles/scripts.
        result.headers['Content-Security-Policy'] = (
            "default-src 'self'; base-uri 'self'; object-src 'none'; "
            "frame-ancestors 'none'; form-action 'self'; connect-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self' data:; img-src 'self' data: blob: https:"
        )
    return result


def _html_route(path):
    if path in ('/admin/uzytkownicy','/admin/uzytkownicy/'):
        path='/account'
    if path == '/rejestracja':
        path='/register'
    if path in ('/bot','/account','/login','/register','/info'):
        return _asset(path[1:]+'.html')
    name=path.strip('/')
    item=DIST/name/'index.html'
    if item.is_file():return _asset(name+'/index.html')
    item=DIST/(name+'.html')
    if item.is_file():return _asset(name+'.html')
    abort(404)


def _is_frontend_path(path):
    return path in FRONTEND_ROUTES or any(path.startswith('/'+p+'/')
                for p in ('offer','purchase','flips','searches'))


def install(app, *, preview=False):
    """Call before first Flask request; in preview make V12 the root app UI."""
    if app.config.get('v12_bridge'):
        return
    def early():
        path=request.path
        enabled=preview or FLAG.is_file()
        if not enabled:return None
        if path.startswith(('/_expo/','/assets/')):
            return _asset(path.lstrip('/'))
        if path.startswith('/api/v1/'):
            if path in PUBLIC_API or path in OTHER_API or path.startswith(
                    ('/api/v1/universal/mobile-radar/','/api/v1/universal/searches/')):
                return _api(path,read_only=preview)
            return None
        if request.method not in ('GET','HEAD'):
            return None
        # Serve EXACTLY the original Expo landing on the actual domain, not
        # V11's reconstructed Jinja marketing page. V11 still owns its
        # specialized legacy routes and scanners.
        if path == '/':
            return _asset('index.html')
        if not preview and path=='/centrum' and not request.args.get('tab'):
            user=_identity()
            if user: return redirect('/bot', code=302)
        if path in ('/login','/register','/rejestracja','/info'):
            return _html_route(path)
        # All public and private primary React pages are now installed.
        # Legacy specialist routes remain available separately.
        if path in PRIVATE_UI or (_is_frontend_path(path) and path not in PUBLIC_UI):
            user=_identity()
            if not user:
                return redirect('/login?next=/bot',code=302)
            if path.startswith('/admin/uzytkownicy') and not (
                    user.get('root') or user.get('role')=='admin'):
                abort(403)
            if path.startswith('/admin/uzytkownicy') and request.args.get('legacy')=='1':
                return None
            return _html_route(path)
        return None
    app.before_request_funcs.setdefault(None,[]).insert(0,early)
    app.config['v12_bridge']=True
