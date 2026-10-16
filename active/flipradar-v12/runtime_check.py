"""Inspect an existing V10/V12 installation without importing it or opening its databases."""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
REQUIRED = (
    'flip_gui_data_dev', 'personal_inventory_v1', 'premium_radar_v2',
    'premium_inventory_stats_v2', 'multiuser_v2', 'user_one_search_v3',
    'workspace_v4_live', 'flipradar_gui_v5', 'guide_v7', 'monitor_v8_web',
    'flipradar_user_web_v9', 'accounts_v10', 'v11_ui',
)


def inspect_runtime(bot_root: Path, overlay_root: Path, dist: Path) -> dict:
    roots = [overlay_root.resolve(), bot_root.resolve(), HERE]
    found, missing = {}, []
    for name in REQUIRED:
        source = next((root / (name + '.py') for root in roots if (root / (name + '.py')).is_file()), None)
        if source is None:
            missing.append(name + '.py')
        else:
            found[name] = str(source)
    entry = next((root / 'flip_v2_overlay_dev.py' for root in roots if (root / 'flip_v2_overlay_dev.py').is_file()), None)
    if entry is None:
        missing.append('flip_v2_overlay_dev.py')
    invalid = []
    for path in [*found.values(), *([str(entry)] if entry else [])]:
        try:
            ast.parse(Path(path).read_text(encoding='utf-8'), filename=path)
        except (OSError, UnicodeError, SyntaxError):
            invalid.append(path)
    export_ready = all((dist / name).is_file() for name in ('index.html', 'login.html', 'account.html', 'radar/index.html'))
    fonts_ready = dist.is_dir() and any(dist.glob('assets/**/*.ttf'))
    return {'ready': not missing and not invalid and export_ready and fonts_ready,
            'missing_modules': missing, 'invalid_sources': invalid,
            'modules': found, 'entrypoint': str(entry) if entry else None,
            'frontend_ready': export_ready, 'fonts_ready': fonts_ready}


def main():
    parser = argparse.ArgumentParser(description='Kontrola połączenia GUI z istniejącym serwerem')
    parser.add_argument('--bot-root', type=Path, default=Path(os.getenv('OLX_BOT_DIR', str(REPO))))
    parser.add_argument('--overlay-root', type=Path, default=Path(os.getenv('FLIPRADAR_OVERLAY_DIR', '/opt/olx-bot-budget-dev')))
    parser.add_argument('--dist', type=Path, default=Path(os.getenv('FLIPRADAR_V12_DIST', str(HERE / 'dist'))))
    args = parser.parse_args()
    result = inspect_runtime(args.bot_root, args.overlay_root, args.dist)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ready'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
