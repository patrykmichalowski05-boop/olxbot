import unittest
import tempfile

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from universal_v2.model import (
    Listing,
    PriceKind,
)

from universal_v2.sources import (
    Sources,
)

from universal_v2.profiles import (
    Profile,
)

from universal_v2.store import (
    Store,
)

from universal_v2.outbox import (
    Outbox,
)

from universal_v2.pipeline import (
    analyze,
)

from universal_v2.comparables import (
    Comparable,
)


class Test11(unittest.TestCase):

    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)

        self.store = Store(
            Path(t.name) / 'db.sqlite'
        )

        self.store.init()

        self.out = Outbox(
            Path(t.name) / 'out.sqlite'
        )

        self.out.init()

        self.sources = Sources({
            'MANUAL': {
                'mode': 'IMPORT_ONLY',
                'operations': [
                    'import',
                    'analyze',
                    'store',
                    'notify',
                ],
            }
        })

        self.profile = Profile(
            'u',
            'mine',
            budget_minor=200000,
        )

        self.listing = Listing(
            'MANUAL',
            'offer',
            'RTX 5060 Ti 16GB',
            100000,
            PriceKind.FULL,
        )

        self.comps = [
            Comparable(
                'GPU:RTX 5060 TI:16GB:DESKTOP',
                str(i),
                180000 + i * 5000,
                'SOLD_VERIFIED',
                'invoice',
            )
            for i in range(3)
        ]

    def run_case(self, comps=None):
        return analyze(
            self.listing,
            'ELECTRONICS',
            self.sources,
            self.profile,
            self.store,
            self.out,
            (
                self.comps
                if comps is None
                else comps
            ),
            {'fees': 5000},
        )

    def test_no_comparables(self):
        self.assertEqual(
            self.run_case(
                []
            )['decision'],
            'NO_RELIABLE_VALUATION',
        )

    def test_stored_observation(self):
        self.assertGreater(
            self.run_case(
                []
            )['observation_id'],
            0,
        )

    def test_repeat(self):
        self.assertEqual(
            self.run_case(
                []
            )['observation_id'],
            self.run_case(
                []
            )['observation_id'],
        )

    def test_no_alert_without_valuation(self):
        self.run_case([])

        self.assertEqual(
            self.out.pending(),
            0,
        )

    def test_outbox_idempotence(self):
        self.assertTrue(
            self.out.enqueue(
                'uniq',
                {'x': 1},
            )
        )

        self.assertFalse(
            self.out.enqueue(
                'uniq',
                {'x': 1},
            )
        )

        self.assertEqual(
            self.out.pending(),
            1,
        )

    def test_parallel_idempotence(self):
        with ThreadPoolExecutor(
            max_workers=4
        ) as pool:
            results = list(
                pool.map(
                    lambda _: self.out.enqueue(
                        'same',
                        {'x': 2},
                    ),
                    range(8),
                )
            )

        self.assertEqual(
            sum(results),
            1,
        )

    def test_reject_unapproved_source(self):
        from universal_v2.sources import (
            SourceDenied,
        )

        with self.assertRaises(SourceDenied):
            analyze(
                self.listing,
                'ELECTRONICS',
                Sources(),
                self.profile,
                self.store,
                self.out,
                [],
                {},
            )
