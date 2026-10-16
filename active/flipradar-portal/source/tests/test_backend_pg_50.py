import unittest

from backend.app.services.deals import _amount


class Test50(unittest.TestCase):

    def test_money_validation(self):
        for amount in (
            True,
            1.5,
            -1,
            1_000_000_001,
        ):
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    _amount(amount)

    def test_positive(self):
        with self.assertRaises(ValueError):
            _amount(0, positive=True)

        _amount(100000, positive=True)
