import unittest

from universal_v2.profiles import Profile
from universal_v2.model import Listing


class Test10(unittest.TestCase):

    def test_default_profit(self):
        self.assertEqual(
            Profile(
                'u',
                'p',
            ).limits(
                'ELECTRONICS'
            )['min_profit_minor'],
            40000,
        )

    def test_car_override(self):
        p = Profile(
            'u',
            'p',
            overrides={
                'CAR': {
                    'min_profit_minor': 300000,
                }
            },
        )

        self.assertEqual(
            p.limits(
                'CAR'
            )['min_profit_minor'],
            300000,
        )

    def test_budget(self):
        p = Profile(
            'u',
            'p',
        )

        offer = Listing(
            'MANUAL',
            'a',
            'GPU',
            300000,
        )

        self.assertFalse(
            p.eligible(
                offer,
                'ELECTRONICS',
            )
        )

    def test_other_source(self):
        p = Profile(
            'u',
            'p',
        )

        offer = Listing(
            'OLX',
            'a',
            'GPU',
            100000,
        )

        self.assertFalse(
            p.eligible(
                offer,
                'ELECTRONICS',
            )
        )
