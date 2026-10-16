#!/usr/bin/env python3
"""Isolated, localhost-only preview for the FlipRadar UI ZIP.

Does not modify /opt/olx-bot, databases, existing timers or Cloudflare.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import socketserver
import subprocess
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile

ROOT = Path('/opt/flipradar-ui-preview')
SERVICE = Path('/etc/systemd/system/flipradar-ui-preview.service')
PORT = 8093


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def _normalize_url(self):
        path = unquote(urlsplit(self.path).path)
        if "\\" in path or "\x00" in path or any(p == ".." for p in path.split("/")):
            return None
        if path == "/":
            return "/index.html"
        if not Path(path).suffix:
            relative = path.lstrip("/").rstrip("/")
            if (Path(self.directory) / (relative + ".html")).is_file():
                return "/" + relative + ".html"
            if (Path(self.directory) / relative / "index.html").is_file():
                return "/" + relative + "/index.html"
        return path

    def do_GET(self):
        path = self._normalize_url()
        if path is None:
            self.send_error(400, "Invalid path")
            return
        self.path = path
        return super().do_GET()

    def do_HEAD(self):
        path = self._normalize_url()
        if path is None:
            self.send_error(400, "Invalid path")
            return
        self.path = path
        return super().do_HEAD()

    def list_directory(self, path):
        self.send_error(403, "Directory listing disabled")
        return None

    def end_headers(self):
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        return super().end_headers()


def serve(args):
    root = Path(args.root)
    if not (root / 'index.html').is_file():
        raise SystemExit(f'Preview missing: {root}/index.html')
    from functools import partial
    with ThreadingHTTPServer(('127.0.0.1', args.port), partial(PreviewHandler, directory=str(root))) as httpd:
        print(f'FlipRadar DEMO (NOT LIVE): http://127.0.0.1:{args.port}/', flush=True)
        httpd.serve_forever()


def extract_preview(source, dest):
    count = 0
    total = 0
    with ZipFile(source) as archive:
        names = {i.filename for i in archive.infolist()}
        required = ('web-demo/index.html', 'web-demo/login.html', 'web-demo/register.html', 'web-demo/bot.html')
        missing = [n for n in required if n not in names]
        if missing:
            raise ValueError('ZIP does not contain preview files: ' + ', '.join(missing))
        for info in archive.infolist():
            if not info.filename.startswith('web-demo/') or info.is_dir():
                continue
            relative = info.filename[len('web-demo/'):]
            path = Path(relative)
            if not relative or path.is_absolute() or any(part in ('..', '') for part in path.parts):
                raise ValueError('Unsafe archive path')
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Symlink in archive')
            total += info.file_size
            if total > 30_000_000:
                raise ValueError('Unexpectedly large demo')
            target = dest / path
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as inp, target.open('wb') as out:
                shutil.copyfileobj(inp, out)
            target.chmod(0o644)
            count += 1
    if count < 10:
        raise ValueError('Too few preview files')
    return count


def run(command):
    print('+', ' '.join(command), flush=True)
    subprocess.run(command, check=True)


def install(args):
    if os.geteuid() != 0:
        raise SystemExit('Run as root for systemd installation')
    src = Path(args.zip).expanduser().resolve()
    if not src.is_file():
        raise SystemExit(f'ZIP not found: {src}')
    digest = hashlib.sha256(src.read_bytes()).hexdigest()[:16]
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / 'releases').mkdir(exist_ok=True)
    release = ROOT / 'releases' / digest
    if not release.is_dir():
        with tempfile.TemporaryDirectory(prefix='.stage-', dir=ROOT) as td:
            staging = Path(td) / 'site'
            staging.mkdir()
            count = extract_preview(src, staging)
            print(f'PASS: extracted {count} web-demo files')
            shutil.copytree(staging, release)
    target_script = ROOT / 'preview_server.py'
    shutil.copyfile(Path(__file__).resolve(), target_script)
    target_script.chmod(0o644)
    active = ROOT / 'current'
    previous = ROOT / 'previous'
    if active.is_symlink():
        previous.unlink(missing_ok=True)
        previous.symlink_to(active.resolve())
    temp_link = ROOT / 'current.new'
    temp_link.unlink(missing_ok=True)
    temp_link.symlink_to(release)
    temp_link.replace(active)
    service_text = f'''[Unit]
Description=FlipRadar new UI preview (DEMO only, localhost)
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 {target_script} serve --root {active} --port {PORT}
WorkingDirectory={ROOT}
Restart=on-failure
RestartSec=3
User=nobody
Group=nogroup
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadOnlyPaths={ROOT}

[Install]
WantedBy=multi-user.target
'''
    if SERVICE.exists():
        old = SERVICE.read_text()
        if 'FlipRadar new UI preview (DEMO only, localhost)' not in old:
            raise SystemExit('Existing different service; refusing to overwrite')
    SERVICE.write_text(service_text)
    run(['systemctl', 'daemon-reload'])
    run(['systemctl', 'enable', '--now', 'flipradar-ui-preview.service'])
    run(['systemctl', 'restart', 'flipradar-ui-preview.service'])
    run(['systemctl', 'is-active', '--quiet', 'flipradar-ui-preview.service'])
    print('\nPASS: FlipRadar UI demo active on 127.0.0.1:8093')
    print('Production /opt/olx-bot, accounts V10 and database were NOT modified.')
    print('From your PC: ssh -N -L 8093:127.0.0.1:8093 root@YOUR_SERVER')
    print('Then open: http://127.0.0.1:8093')


def rollback(args):
    if os.geteuid() != 0:
        raise SystemExit('Run as root')
    active = ROOT / 'current'
    previous = ROOT / 'previous'
    if not previous.is_symlink():
        raise SystemExit('No previous preview version')
    old = previous.resolve()
    temp_link = ROOT / 'current.new'
    temp_link.unlink(missing_ok=True)
    temp_link.symlink_to(old)
    temp_link.replace(active)
    run(['systemctl', 'restart', 'flipradar-ui-preview.service'])
    print('PASS: previous demo restored, production untouched')


def main():
    parser = argparse.ArgumentParser(description='FlipRadar isolated UI preview')
    actions = parser.add_subparsers(dest='command', required=True)
    cmd = actions.add_parser('install')
    cmd.add_argument('--zip', default='/root/FlipRadar-Strona-i-Konta.zip')
    cmd = actions.add_parser('serve')
    cmd.add_argument('--root', default=str(ROOT / 'current'))
    cmd.add_argument('--port', type=int, default=PORT)
    actions.add_parser('rollback')
    args = parser.parse_args()
    {'install': install, 'serve': serve, 'rollback': rollback}[args.command](args)


if __name__ == '__main__':
    main()
