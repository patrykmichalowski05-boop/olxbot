from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path("/opt/flipradar-portal-stage/source/mobile/dist")

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def rewrite(self):
        path = unquote(urlsplit(self.path).path)
        if path not in ("", "/") and not Path(path).suffix:
            candidate = ROOT / (path.strip("/") + ".html")
            if candidate.is_file():
                self.path = "/" + path.strip("/") + ".html"

    def do_GET(self):
        self.rewrite()
        super().do_GET()

    def do_HEAD(self):
        self.rewrite()
        super().do_HEAD()

ThreadingHTTPServer(("127.0.0.1", 8095), Handler).serve_forever()
