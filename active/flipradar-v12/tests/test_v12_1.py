"""Isolated regression for V12.1 recovery. Never touches live services or DBs."""
import importlib.util
import tempfile
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'deploy_v12.py'
spec = importlib.util.spec_from_file_location('flip_v12_1_deploy_test', MODULE)
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)

with tempfile.TemporaryDirectory(prefix='flip-v12-1-test-') as temp:
    root = Path(temp)
    d.ROOT = root
    d.MOBILE = root / 'mobile'
    d.DIST = root / 'dist'
    d.HERE = root
    d.FLAG = root / '.v12_live'
    d.OVERLAY = root / 'overlay'
    src = d.MOBILE / 'src/features/portal/PortalPage.web.tsx'
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text('deleteMemberAccount', encoding='utf-8')
    for name in ('index.html', 'login.html', 'bot.html', 'account.html',
                 '_expo/static/js/index.js', '_expo/static/css/index.css'):
        f = d.MOBILE / 'dist' / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text('V12 test', encoding='utf-8')
    for name in ('v12_bridge.py', 'v12_preview.py', 'v12_smoke.py', 'flipradar_legacy_bridge.py'):
        (root / name).write_text('original module', encoding='utf-8')
    d._finish_prepare()
    assert (root / 'dist' / 'bot.html').is_file()
    d._finish_prepare()  # samefile must be a harmless no-op
    assert (root / 'VERSION').is_file()
    print('PASS: V12.1 restartable finalization; no SameFileError')
    (root / 'v12_smoke.py').write_text(
        'import os;assert "/opt/olx-bot" in os.environ["PYTHONPATH"];'
        'assert "overlay" in os.environ["PYTHONPATH"];'
        'print("PASS: test process imports enabled")', encoding='utf-8')
    d._prepublish_check = lambda: None  # This test covers recovery/PYTHONPATH; production preflight has separate tests.
    d.smoke()
    print('PASS: V12.1 test environment PYTHONPATH')
print('PASS: ALL V12.1 PATCH REGRESSION TESTS')
