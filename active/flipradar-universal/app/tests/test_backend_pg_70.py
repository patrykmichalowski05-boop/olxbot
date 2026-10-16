import unittest

from backend.app.services.notification_inbox import (
    page,
)


class Test70(unittest.TestCase):

    def test_invalid_limits(self):
        for value in (0, 101, True):
            with self.assertRaises(ValueError):
                page(
                    None,
                    "workspace",
                    limit=value,
                )
