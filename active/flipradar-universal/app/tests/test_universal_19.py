import unittest
import tempfile

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from universal_v2.delivery_queue import DeliveryQueue


class Test19(unittest.TestCase):

    def test_one_claim(self):
        with tempfile.TemporaryDirectory() as t:

            q = DeliveryQueue(
                Path(t) / 'queue.sqlite'
            )

            q.init()

            self.assertTrue(
                q.put('k', {'a': 1})
            )

            self.assertFalse(
                q.put('k', {'a': 1})
            )

            with ThreadPoolExecutor(
                max_workers=4
            ) as pool:

                claimed = list(
                    pool.map(
                        lambda _: q.claim(),
                        range(8)
                    )
                )

            found = [
                x
                for x in claimed
                if x
            ]

            self.assertEqual(
                len(found),
                1
            )

            self.assertTrue(
                q.ack(found[0]['id'])
            )

            self.assertIsNone(
                q.claim()
            )
