from pathlib import Path

from runtime_check import REQUIRED, inspect_runtime


def test_missing_dependencies_are_reported_without_imports_or_database_creation(tmp_path):
    bot=tmp_path/'bot';overlay=tmp_path/'overlay';dist=tmp_path/'dist'
    bot.mkdir();overlay.mkdir()
    (bot/'flip_v2_overlay_dev.py').write_text('raise RuntimeError("must not run")')
    result=inspect_runtime(bot,overlay,dist)
    assert result['ready'] is False
    assert 'multiuser_v2.py' in result['missing_modules']
    assert 'accounts_v10.py' in result['missing_modules']
    assert not list(tmp_path.rglob('*.sqlite3'))


def test_sources_export_and_fonts_are_checked(tmp_path):
    bot=tmp_path/'bot';overlay=tmp_path/'overlay';dist=tmp_path/'dist'
    bot.mkdir();overlay.mkdir()
    (bot/'flip_v2_overlay_dev.py').write_text('app = None')
    for name in REQUIRED: (overlay/(name+'.py')).write_text('value = None')
    for name in ('index.html','login.html','account.html','radar/index.html'):
        path=dist/name;path.parent.mkdir(parents=True,exist_ok=True);path.touch()
    assert inspect_runtime(bot,overlay,dist)['fonts_ready'] is False
    font=dist/'assets/icons.ttf';font.parent.mkdir();font.touch()
    assert inspect_runtime(bot,overlay,dist)['ready'] is True
    (overlay/'accounts_v10.py').write_text('def broken(')
    assert inspect_runtime(bot,overlay,dist)['invalid_sources']
