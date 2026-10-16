"""Build the Git-tracked Expo sources for the existing Flask session server."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

HERE = Path(__file__).resolve().parent


def validate_export(root: Path):
    required = ('index.html', 'login.html', 'register.html', 'account.html', 'bot.html',
                'radar/index.html', 'searches/index.html', 'searches/results.html',
                'market/index.html', 'offer/[id].html', 'flips/[dealId].html')
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise RuntimeError('Niepełny eksport: ' + ', '.join(missing))
    scripts = list(root.glob('_expo/static/js/web/*.js'))
    if not scripts or not list(root.glob('_expo/static/css/*.css')):
        raise RuntimeError('Brak JavaScript lub CSS')
    if not list(root.glob('assets/**/*.ttf')):
        raise RuntimeError('Brak fontów i ikon w eksporcie')
    if not any('same-origin' in path.read_text() and 'flask-v12' in path.read_text() for path in scripts):
        raise RuntimeError('Eksport nie zawiera konfiguracji LIVE dla obecnego serwera')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true', help='Run npm ci first')
    parser.add_argument('--output', type=Path, default=HERE / 'dist')
    args = parser.parse_args()
    mobile = HERE / 'mobile'
    if int(subprocess.check_output(['node', '-p', 'process.versions.node.split(".")[0]'], text=True)) < 22:
        raise RuntimeError('Wymagany Node.js 22 lub nowszy')
    environment = {**os.environ, 'EXPO_PUBLIC_FLIP_APP_MODE': 'live',
                   'EXPO_PUBLIC_FLIP_WEB_LIVE': '1', 'EXPO_PUBLIC_FLIP_PORTAL_ENABLED': '1',
                   'EXPO_PUBLIC_FLIP_RADAR_SOURCE': 'universal', 'EXPO_PUBLIC_FLIP_BACKEND': 'flask-v12',
                   'EXPO_PUBLIC_FLIP_API_URL': 'same-origin', 'EXPO_PUBLIC_FLIP_WORKSPACE_ID': 'legacy',
                   'EXPO_NO_TELEMETRY': '1', 'CI': '1'}
    if args.install or not (mobile / 'node_modules').is_dir():
        subprocess.run(['npm', 'ci', '--no-audit', '--no-fund'], cwd=mobile, env=environment, check=True)
    args.output = args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.dist-build-', dir=args.output.parent) as temp:
        stage = Path(temp) / 'export'
        subprocess.run(['npx', 'expo', 'export', '--platform', 'web', '--clear', '--output-dir', str(stage)], cwd=mobile, env=environment, check=True)
        validate_export(stage)
        (stage / 'build-info.json').write_text(json.dumps({'mode': 'live', 'backend': 'flask-v12', 'api': 'same-origin', 'lock_sha256': hashlib.sha256((mobile / 'package-lock.json').read_bytes()).hexdigest()}, indent=2)+'\n')
        backup = args.output.parent / ('.dist-backup-' + uuid.uuid4().hex)
        if args.output.exists():
            args.output.rename(backup)
        try:
            shutil.move(str(stage), args.output)
        except Exception:
            if backup.exists() and not args.output.exists():
                backup.rename(args.output)
            raise
    print('GUI LIVE gotowe:', args.output)


if __name__ == '__main__':
    main()
