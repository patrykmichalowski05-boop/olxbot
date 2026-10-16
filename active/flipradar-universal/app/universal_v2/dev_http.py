"""
Lokalne API demonstracyjne.
NIE jest publicznym API mobilnym.
"""

import hmac
import json
import os

from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer
)

from urllib.parse import (
    urlsplit,
    parse_qs
)

from .radar_service import RadarService
from .sandbox import database_file


def handler_factory(token, database):
    if (
        not isinstance(token, str)
        or len(token) < 32
    ):
        raise ValueError(
            'FLIP_DEV_TOKEN musi miec >=32 znaki'
        )

    service = RadarService(database)

    class Handler(BaseHTTPRequestHandler):

        def log_message(self, *args):
            pass

        def reply(self, status, data):
            raw = json.dumps(
                data,
                ensure_ascii=False
            ).encode('utf-8')

            self.send_response(status)

            self.send_header(
                'Content-Type',
                'application/json; charset=utf-8'
            )

            self.send_header(
                'Content-Length',
                str(len(raw))
            )

            self.send_header(
                'Cache-Control',
                'no-store'
            )

            self.send_header(
                'X-Content-Type-Options',
                'nosniff'
            )

            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            auth = self.headers.get(
                'Authorization',
                ''
            )

            if not hmac.compare_digest(
                auth,
                'Bearer ' + token
            ):
                return self.reply(
                    401,
                    {'error': 'Unauthorized'}
                )

            url = urlsplit(self.path)

            if url.path == '/dev/health':
                return self.reply(
                    200,
                    {
                        'status': 'ok',
                        'mode': 'LOCAL_ONLY',
                        'production_ready': False
                    }
                )

            if url.path == '/dev/radar':
                try:
                    params = parse_qs(
                        url.query
                    )

                    phrase = params.get(
                        'q',
                        ['']
                    )[0]

                    limit = int(
                        params.get(
                            'limit',
                            ['20']
                        )[0]
                    )

                    before = params.get(
                        'before_id',
                        [None]
                    )[0]

                    before = (
                        int(before)
                        if before is not None
                        else None
                    )

                    result = service.page(
                        'dev-owner',
                        query=phrase,
                        limit=limit,
                        before_id=before
                    )

                    return self.reply(
                        200,
                        result
                    )

                except (ValueError, TypeError):
                    return self.reply(
                        400,
                        {'error': 'Invalid parameters'}
                    )

            return self.reply(
                404,
                {'error': 'Not found'}
            )

    return Handler


def serve():
    token = os.environ.get(
        'FLIP_DEV_TOKEN',
        ''
    )

    directory = os.environ.get(
        'FLIP_DEV_DATA_DIR',
        ''
    )

    db = database_file(directory)

    handler = handler_factory(
        token,
        db
    )

    print(
        'DEVELOPMENT ONLY: '
        'http://127.0.0.1:8765'
    )

    ThreadingHTTPServer(
        ('127.0.0.1', 8765),
        handler
    ).serve_forever()


if __name__ == '__main__':
    serve()
