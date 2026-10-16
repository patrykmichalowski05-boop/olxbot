import unittest

from backend.app.services.outbox_dispatch import (
    backoff_seconds,
    MAX_ATTEMPTS,
)


class Test69(unittest.TestCase):

    def test_exponential_backoff(self):
        self.assertEqual(
            [
                backoff_seconds(x)
                for x in (1, 2, 3)
            ],
            [10, 20, 40],
        )

        self.assertEqual(
            backoff_seconds(100),
            3600,
        )

        self.assertEqual(MAX_ATTEMPTS, 5)

        with self.assertRaises(ValueError):
            backoff_seconds(0)
