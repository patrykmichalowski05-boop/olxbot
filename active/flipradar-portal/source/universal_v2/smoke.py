"""Test całego przepływu bez internetu."""

import tempfile
from pathlib import Path

from .manual_input import convert
from .sources import Sources
from .profiles import Profile
from .store import Store
from .outbox import Outbox
from .pipeline import analyze


def run():
    with tempfile.TemporaryDirectory(
        prefix='flip-smoke-'
    ) as t:

        root = Path(t)

        store = Store(
            root / 'obs.sqlite'
        )

        store.init()

        out = Outbox(
            root / 'out.sqlite'
        )

        out.init()

        row = convert({
            'external_id': 'demo-01',
            'title': 'RTX 5060 Ti 16GB',
            'price': '1200',
            'price_kind': 'FULL'
        })

        sources = Sources({
            'MANUAL': {
                'mode': 'IMPORT_ONLY',
                'operations': [
                    'import',
                    'analyze',
                    'store',
                    'notify'
                ]
            }
        })

        profile = Profile(
            'dev-user',
            'test'
        )

        result = analyze(
            row,
            'ELECTRONICS',
            sources,
            profile,
            store,
            out,
            [],
            {'transport': 2000}
        )

        assert (
            result['decision']
            == 'NO_RELIABLE_VALUATION'
        ), result

        assert out.pending() == 0

        return {
            'status': 'PASS',
            'decision': result['decision'],
            'notifications': out.pending()
        }


if __name__ == '__main__':
    print(run())
