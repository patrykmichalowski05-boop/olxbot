#!/usr/bin/env python3
"""Isolated production-mode check of V12 routing. Never touches the live user DB."""
from __future__ import annotations
import os
import re
import tempfile
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory(prefix='v12-2-publish-check-') as tmp:
        os.environ.update({
            'FLIP_MULTIUSER_DB': str(Path(tmp) / 'isolated-users.sqlite3'),
            'DASHBOARD_AUTH_REQUIRED': '1',
            'DASHBOARD_USERNAME': 'v12-test-only-root',
            'DASHBOARD_PASSWORD': 'temporary-disposable-v12-check-password',
            'DASHBOARD_SECRET_KEY': 'temporary-disposable-v12-check-secret',
        })
        from flip_v2_overlay_dev import app
        import v12_bridge as bridge

        flag=Path(tmp)/'v12-active'
        flag.write_text('LIVE\n')
        bridge.FLAG=flag
        assert not app.config.get('v12_bridge'), 'V12 already installed in production overlay'
        bridge.install(app)
        client=app.test_client()
        index=(bridge.DIST/'index.html').read_bytes()

        response=client.get('/')
        assert response.status_code == 200, ('/',response.status_code)
        assert response.data == index, 'Root does not serve the exact compiled Expo HTML'
        assert response.headers.get('Content-Security-Policy'), 'Missing root CSP (V11 preflight)'
        print('PASS: / serves the original Expo index.html + CSP')

        for path in ('/login','/register','/rejestracja'):
            response=client.get(path)
            assert response.status_code==200, (path,response.status_code)
            assert b'FlipRadar' in response.data, path
            print('PASS:',path,'React HTTP 200')

        for path in ('/bot','/account','/admin/uzytkownicy','/dev/flip-hunter'):
            response=client.get(path)
            assert response.status_code==302, (path,response.status_code)
            assert '/login' in response.headers.get('Location',''), (path,'no auth redirect')
            print('PASS:',path,'requires authentication')

        result=client.get('/api/v1/public/config')
        assert result.status_code==200 and result.json.get('demo_data') is False
        print('PASS: React API on the same origin')

        assets=list(bridge.DIST.glob('_expo/static/js/web/*.js'))
        assert assets, 'Missing compiled Expo JS'
        asset=client.get('/'+assets[0].relative_to(bridge.DIST).as_posix())
        assert asset.status_code==200 and len(asset.data)>1024
        print('PASS: original Expo JS served from domain')

        response=client.post('/api/v1/portal/admin/delete',json={'user_id':1,'confirm':'fake'})
        assert response.status_code in (401,403),('unexpected public write',response.status_code)
        print('PASS: anonymous account deletion denied')
        print('PASS: V12.2 production-mode routing preflight')


if __name__=='__main__':
    main()
