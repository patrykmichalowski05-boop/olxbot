"""Read-only category audit of the separate shadow replay database."""
import argparse
from collections import Counter
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from .category_router import categorize
from .contracts import RawListing, SourceStatus


def audit_shadow(db_path, limit=10000):
    db_path = Path(db_path).resolve()
    if not 1 <= limit <= 100000:
        raise ValueError('Nieprawidlowy limit')
    if not db_path.is_file():
        raise FileNotFoundError(db_path)
    categories = Counter()
    platforms = Counter()
    reasons = Counter()
    eligible = 0
    invalid = 0
    with closing(sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True, timeout=20)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute('''
            SELECT id, payload_json FROM listing_observations
            ORDER BY id DESC LIMIT ?
        ''', (limit,)).fetchall()
        for row in rows:
            try:
                payload = json.loads(row['payload_json'])
                if not isinstance(payload, dict):
                    raise ValueError('payload')
                raw_status = payload.get('status', 'UNKNOWN')
                status = SourceStatus(raw_status) if raw_status in SourceStatus._value2member_map_ else SourceStatus.UNKNOWN
                listing = RawListing(
                    platform=str(payload.get('platform') or 'UNKNOWN'),
                    external_id=str(payload.get('external_id') or ''),
                    canonical_url=str(payload.get('canonical_url') or ''),
                    title=str(payload.get('title') or ''),
                    description=str(payload.get('description') or ''),
                    price_minor=payload.get('price_minor'),
                    currency=str(payload.get('currency') or ''),
                    status=status,
                    fetched_at='',
                    parser_version='legacy-shadow',
                )
                result = categorize(listing, hints=payload.get('attributes'))
                categories[result.category] += 1
                platforms[listing.platform] += 1
                reasons[result.reason] += 1
                eligible += int(result.pc_pricing_input_complete)
            except (ValueError, TypeError, KeyError):
                invalid += 1
    return {
        'inspected_observations': len(rows),
        'categories': dict(categories),
        'platforms': dict(platforms),
        'reasons': dict(reasons),
        'pc_pricing_inputs_complete': eligible,
        'invalid_records': invalid,
        'wrote_to_source': False,
        'note': 'Classification is not a market valuation or BUY decision',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--limit', type=int, default=10000)
    args = parser.parse_args()
    source = Path(args.source).resolve()
    report = Path(args.report).resolve()
    root = Path('/root/olx-shadow').resolve()
    if not source.is_relative_to(root) or not report.is_relative_to(root):
        parser.error('Pliki musza byc w /root/olx-shadow')
    data = audit_shadow(source, args.limit)
    report.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
