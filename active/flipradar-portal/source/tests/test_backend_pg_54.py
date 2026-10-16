import inspect
import unittest

from backend.app.services.deals import sell


class Test54(unittest.TestCase):

    def test_sell_uses_row_lock(self):
        source = inspect.getsource(sell)

        self.assertIn(
            ".with_for_update()",
            source,
        )
