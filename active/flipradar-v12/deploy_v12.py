#!/usr/bin/env python3
"""Deploy the actual uploaded Expo frontend in a staged, reversible fashion."""
from __future__ import annotations
import argparse
import hashlib
import os
import sqlite3
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=Path('/opt/flipradar-v12')
MOBILE=ROOT/'mobile'
DIST=ROOT/'dist'
OVERLAY=Path('/opt/olx-bot-budget-dev')
FLAG=OVERLAY/'.v12_live'
ENTRY=OVERLAY/'flip_v2_overlay_dev.py'
BACKUPS=OVERLAY/'v12_backups'
SERVICE='olx-dashboard-v2.service'
PREVIEW='flipradar-v12-preview.service'
VERSION='V12.2-EXPO-ORIGINAL-PUBLISHED-20261016'
EXPECTED_SHA='6ff73ecbd418dbf0f38ae8c0a40a5c2e57e84fb2bdb779b2ce20a90c89d17591'


def out(*values): print(*values,flush=True)

def require(v,msg):
    if not v: raise RuntimeError('STOP: '+msg)

def run(cmd,**kwargs):
    out('+',' '.join(map(str,cmd)))
    subprocess.run(list(map(str,cmd)),check=True,**kwargs)

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for piece in iter(lambda:f.read(1048576),b''):h.update(piece)
    return h.hexdigest()

def files_from_zip(path,dest):
    require(path.is_file(),f'Brak oryginalnej paczki: {path}')
    require(sha(path)==EXPECTED_SHA,
            'Archiwum jest inne niz zaakceptowana paczka. Nie instaluję innej wersji.')
    with zipfile.ZipFile(path) as z:
        names=[n for n in z.namelist() if n.startswith('source/mobile/')
               and not n.endswith('/')]
        require(len(names)>90,'Niekompletny katalog source/mobile')
        for name in names:
            rel=Path(name).relative_to('source/mobile')
            require('..' not in rel.parts and not rel.is_absolute(),'Niedozwolona ścieżka ZIP')
            if rel.parts[0] in ('node_modules','dist','.expo'):continue
            if rel.suffix in ('.env','.local'):continue
            target=dest/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(name) as src, target.open('wb') as dst:
                shutil.copyfileobj(src,dst)
    out(f'PASS: skopiowano oryginalne pliki React/Expo ({len(names)})')

def check_node():
    require(shutil.which('node') and shutil.which('npm'),
            'Na VPS wymagany Node.js 22 i npm. Brak — produkcja nietknięta.')
    result=subprocess.check_output(['node','-p','process.versions.node'],text=True).strip()
    require(int(result.split('.')[0])>=22, f'Wymagany Node 22+, jest {result}')
    out('PASS: Node',result)

def prepare(source):
    require(ENTRY.is_file(),'Brak istniejacego Flask overlay')
    require(not FLAG.exists(),'V12 już opublikowany. Nie uruchamiaj prepare ponownie.')
    check_node()
    ROOT.mkdir(parents=True,exist_ok=True)
    if MOBILE.exists():
        old=ROOT/('mobile.previous.'+time.strftime('%Y%m%d-%H%M%S'))
        MOBILE.rename(old)
    files_from_zip(source,MOBILE)
    run([sys.executable,HERE/'patch_frontend_v12.py',MOBILE])
    env=os.environ.copy()
    env.update(EXPO_PUBLIC_FLIP_APP_MODE='live',EXPO_PUBLIC_FLIP_WEB_LIVE='1',
               EXPO_PUBLIC_FLIP_PORTAL_ENABLED='1',
               EXPO_PUBLIC_FLIP_RADAR_SOURCE='universal',
               EXPO_PUBLIC_FLIP_WORKSPACE_ID='legacy',
               EXPO_PUBLIC_FLIP_API_URL='same-origin',
               EXPO_NO_TELEMETRY='1',CI='1')
    run(['npm','ci','--no-audit','--no-fund'],cwd=str(MOBILE),env=env)
    run(['npx','expo','export','--platform','web','--output-dir','dist'],
        cwd=str(MOBILE),env=env)
    _finish_prepare()


def _copy_unless_same(source, destination):
    """Files shipped in /opt/flipradar-v12 already have their final location."""
    source, destination = Path(source), Path(destination)
    require(source.is_file(), f'Brak pliku wymaganej integracji: {source}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)


def _finish_prepare():
    """Complete a successful Expo export without rebuilding or touching production."""
    output = MOBILE / 'dist'
    for name in ('index.html', 'account.html', 'bot.html', 'login.html'):
        require((output / name).is_file(), f'Brak eksportu React: {output / name}')
    require(any(output.rglob('*.js')), 'Brak JavaScript w eksporcie React')
    require(any(output.rglob('*.css')), 'Brak CSS w eksporcie React')
    portal = MOBILE / 'src/features/portal/PortalPage.web.tsx'
    require(portal.is_file() and 'deleteMemberAccount' in portal.read_text(encoding='utf-8'),
            'Brak aktualizacji V12 w oryginalnym projekcie. Wykonaj pełne prepare.')
    ROOT.mkdir(parents=True, exist_ok=True)
    staging = ROOT / ('.dist-pending-' + str(os.getpid()))
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(output, staging)
    if DIST.exists():
        backup = ROOT / ('dist.previous.' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid()))
        DIST.rename(backup)
    staging.rename(DIST)
    for name in ('v12_bridge.py', 'v12_preview.py', 'v12_smoke.py'):
        _copy_unless_same(HERE / name, ROOT / name)
    (ROOT / 'VERSION').write_text(VERSION + '\noriginal_zip_sha256=' + EXPECTED_SHA + '\n', encoding='utf-8')
    out('PASS: oryginalny frontend React/Expo gotowy; produkcyjny dashboard nietknięty.')
    out('NEXT: /opt/olx-bot/venv/bin/python /opt/flipradar-v12/deploy_v12.py smoke')


def resume(source):
    """Recover when npm/Expo succeeded but the old installer crashed on copy2."""
    require(not FLAG.exists(), 'V12 juz opublikowane; nie uruchamiaj resume')
    require(source.is_file() and sha(source) == EXPECTED_SHA,
            'Niepoprawna lub brakujaca oryginalna paczka FlipRadar')
    require(MOBILE.is_dir() and (MOBILE / 'src').is_dir(),
            'Brak skopiowanego projektu. Wykonaj prepare.')
    _finish_prepare()


def _preview_unit():
    # Reuse dashboard's EnvironmentFile paths (not their contents).
    # Do not print credentials or copy them into this installer.
    envfiles=[]
    try:
        published=subprocess.check_output(['systemctl','cat',SERVICE], text=True,
                                          stderr=subprocess.DEVNULL)
        for line in published.splitlines():
            if line.strip().startswith('EnvironmentFile='):
                envfiles.append(line.strip())
    except (subprocess.CalledProcessError,FileNotFoundError):
        pass
    unit='''[Unit]
Description=FlipRadar V12 original React UI preview (live Flask data)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/olx-bot
Environment="PYTHONPATH=/opt/flipradar-v12:/opt/olx-bot:/opt/olx-bot-budget-dev"
Environment="FLIPRADAR_V12_DIST=/opt/flipradar-v12/dist"
EnvironmentFile=-/opt/olx-bot/.env
ExecStart=/opt/olx-bot/venv/bin/gunicorn --bind 127.0.0.1:8094 --workers 1 --timeout 45 --access-logfile - --error-logfile - v12_preview:app
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
'''
    if envfiles:
        unit=unit.replace('EnvironmentFile=-/opt/olx-bot/.env', '\n'.join(envfiles))
    return unit


def smoke():
    require((DIST/'bot.html').is_file(),
            'Najpierw wykonaj resume (po udanym Expo export) lub prepare')
    env = os.environ.copy()
    # Running a script by absolute path changes sys.path[0] to its own dir.
    # The user/account modules are in the existing Flask overlay, not there.
    required = [str(ROOT), '/opt/olx-bot', str(OVERLAY)]
    previous = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = os.pathsep.join(required + ([previous] if previous else []))
    run([sys.executable, ROOT / 'v12_smoke.py'], cwd=str(ROOT), env=env)
    _prepublish_check()
    out('PASS: V12.2 SMOKE — original React on public landing + admin protected')


def stage():
    smoke()
    unitpath=Path('/etc/systemd/system')/PREVIEW
    unitpath.write_text(_preview_unit())
    run(['systemctl','daemon-reload'])
    run(['systemctl','enable','--now',PREVIEW])
    run(['systemctl','restart',PREVIEW])
    require(_wait('/'), 'Podgląd V12 nie odpowiada; sprawdź journalctl -u '+PREVIEW)
    out('PASS: Oryginalny panel React dziala na 127.0.0.1:8094 (LIVE, nie DEMO).')
    out('Dostęp przez SSH tunnel: ssh -N -L 8094:127.0.0.1:8094 root@SERWER')


def _wait(path,port=8094,deadline=50,expected=(200,)):
    import http.client
    end=time.monotonic()+deadline
    while time.monotonic()<end:
        try:
            conn=http.client.HTTPConnection('127.0.0.1',port,timeout=4)
            try:
                conn.request('GET',path)
                response=conn.getresponse()
                code=response.status
                response.read(1024)
            finally:
                conn.close()
        except (OSError,TimeoutError,http.client.HTTPException):code=0
        if code in expected:return True
        out(f'WAIT: {port}{path} HTTP {code}')
        time.sleep(2)
    return False


def _new_backup():
    BACKUPS.mkdir(parents=True,exist_ok=True,mode=0o700)
    BACKUPS.chmod(0o700)
    target=BACKUPS/(time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid()))
    target.mkdir(mode=0o700)
    shutil.copy2(ENTRY,target/'flip_v2_overlay_dev.py')
    user_db=OVERLAY/'data'/'flipradar_users.sqlite3'
    if user_db.is_file():
        with sqlite3.connect(f'file:{user_db.as_posix()}?mode=ro',uri=True) as src:
            with sqlite3.connect(target/'flipradar_users.sqlite3') as dst:
                src.backup(dst)
        (target/'flipradar_users.sqlite3').chmod(0o600)
    (target/'version').write_text(VERSION+'\n')
    (ROOT/'last_backup').write_text(str(target))
    return target


def _prepublish_check():
    """Use fake credentials and SQLite; verify actual production-mode root/auth."""
    require((ROOT/'v12_publish_preflight.py').is_file(),
            'Brak testu produkcyjnego V12.2. Wgraj cala poprawke ZIP.')
    env=os.environ.copy()
    env['PYTHONPATH']=os.pathsep.join((str(ROOT),'/opt/olx-bot',str(OVERLAY)))
    env['FLIPRADAR_V12_DIST']=str(DIST)
    run([sys.executable,ROOT/'v12_publish_preflight.py'],
        cwd='/opt/olx-bot',env=env)


def publish():
    require(os.geteuid()==0,'Publikacja wymaga uprawnien root')
    require((DIST/'index.html').is_file() and (DIST/'account.html').is_file(),
            'Najpierw prepare i stage')
    require(not FLAG.exists(),'V12 juz opublikowane; nie nadpisuj ponownie')
    require(_wait('/',deadline=8),'Podglad LIVE na 8094 nie odpowiada')
    require(ENTRY.is_file(),'Nie znaleziono istniejacego Flaska')
    require((ROOT/'v12_bridge.py').is_file(),'Brak mostu V12.2')
    # Include a startup check for / as well as login/admin before touching production.
    _prepublish_check()
    src=ENTRY.read_text(encoding='utf-8')
    require('install_v12_original' not in src,
            'V12 bridge jest juz zainstalowany w overlay')
    target=_new_backup()
    copy_path=OVERLAY/'v12_bridge.py'
    previous_bridge=target/'v12_bridge.py'
    if copy_path.exists():shutil.copy2(copy_path,previous_bridge)
    try:
        shutil.copy2(ROOT/'v12_bridge.py',copy_path)
        entry=src.rstrip()+"""

# FLIPRADAR_V12_ORIGINAL_EXPO
from v12_bridge import install as install_v12_original
install_v12_original(app)
"""
        # Ensure source compiles before writing, so preflight will not break.
        compile(entry,str(ENTRY),'exec')
        ENTRY.write_text(entry,encoding='utf-8')
        FLAG.write_text('LIVE\n',encoding='ascii')
        run(['systemctl','restart',SERVICE])
        require(_wait('/',port=8089,expected=(200,),deadline=60),
                'Brak publicznej strony React /')
        require(_wait('/login',port=8089,expected=(200,),deadline=15),
                'Brak React login /login')
        require(_wait('/rejestracja',port=8089,expected=(200,),deadline=15),
                'Brak formularza React rejestracja')
        require(_wait('/bot',port=8089,expected=(302,),deadline=15),
                'Niechroniony albo niedostepny panel /bot')
        require(_wait('/admin/uzytkownicy',port=8089,expected=(302,),deadline=15),
                'Niechroniona administracja')
        require(_wait('/dev/flip-hunter',port=8089,expected=(302,),deadline=15),
                'Zmiana ochrony starego panelu')
        require(_wait('/api/v1/public/config',port=8089,expected=(200,),deadline=15),
                'Nie dziala API React')
        require(_wait('/_expo/static/js/web/'+next(DIST.glob('_expo/static/js/web/*.js')).name,
                      port=8089,expected=(200,),deadline=15),
                'Brak plikow JS oryginalnego React')
        out('PASS: V12.2 OPUBLIKOWANE: oryginalny React /, konto, radary, admin i logowanie')
        out('Zachowane: SQLite V9/V10, skanery, Cloudflare Access, stare narzedzia.')
        out('BACKUP:',target)
    except Exception:
        out('ERROR: Publikacja V12.2. Przywracam overlay i most bez nadpisywania SQLite...')
        shutil.copy2(target/'flip_v2_overlay_dev.py',ENTRY)
        if previous_bridge.is_file():shutil.copy2(previous_bridge,copy_path)
        else:copy_path.unlink(missing_ok=True)
        FLAG.unlink(missing_ok=True)
        run(['systemctl','restart',SERVICE])
        raise


def rollback():
    marker=ROOT/'last_backup'
    require(marker.is_file(),'Brak rekordu backupu V12')
    target=Path(marker.read_text().strip())
    require(target.is_dir() and (target/'flip_v2_overlay_dev.py').is_file(),
            'Nie znaleziono prawidlowej kopii')
    shutil.copy2(target/'flip_v2_overlay_dev.py',ENTRY)
    existing_bridge=target/'v12_bridge.py'
    if existing_bridge.is_file():shutil.copy2(existing_bridge,OVERLAY/'v12_bridge.py')
    else:(OVERLAY/'v12_bridge.py').unlink(missing_ok=True)
    FLAG.unlink(missing_ok=True)
    run(['systemctl','restart',SERVICE])
    require(_wait('/login',port=8089,expected=(200,)), 'Nie działa poprzednie logowanie')
    out('PASS: przywrócono poprzedni interfejs. Bazy i skanery nietknięte.')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=('prepare','resume','smoke','stage','publish','rollback'))
    p.add_argument('--zip',default='/root/FlipRadar-Strona-i-Konta.zip')
    args=p.parse_args()
    actions={'prepare':lambda:prepare(Path(args.zip)),
             'resume':lambda:resume(Path(args.zip)),
             'smoke':smoke,'stage':stage,'publish':publish,'rollback':rollback}
    actions[args.action]()
