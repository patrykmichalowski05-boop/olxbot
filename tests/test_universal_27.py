import tempfile
import unittest

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from universal_v2.dispatch_v2 import Dispatch


class Test27(unittest.TestCase):

    def test_idempotency_claim_retry(self):
        with tempfile.TemporaryDirectory() as t:
            q = Dispatch(
                Path(t) / 'q.sqlite'
            )
            q.init()

            self.assertTrue(
                q.put('u', 'x', {'a': 1})
            )

            self.assertFalse(
                q.put('u', 'x', {'a': 1})
            )

            with self.assertRaises(ValueError):
                q.put('u', 'x', {'a': 2})

            with ThreadPoolExecutor(
                max_workers=4
            ) as pool:
                claims = list(
                    pool.map(
                        lambda _: q.claim(now=100),
                        range(8)
                    )
                )

            claims = [
                c for c in claims if c
            ]

            self.assertEqual(
                len(claims), 1
            )

            self.assertEqual(
                q.finish(
                    claims[0],
                    False,
                    now=100
                ),
                'RETRY'
            )

            self.assertIsNone(
                q.claim(now=100)
            )

            second = q.claim(now=200)

            with self.assertRaises(ValueError):
                q.finish(
                    claims[0],
                    True,
                    now=200
                )

            self.assertEqual(
                q.finish(
                    second,
                    True,
                    now=200
                ),
                'DONE'
            )

            self.assertIsNone(
                q.claim(now=9999)
            )
