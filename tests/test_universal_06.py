import unittest

from universal_v2.vehicles import classify_car
from universal_v2.model import Listing, PriceKind


class Test06(unittest.TestCase):

    def tesla(
        self,
        drive,
        kind=PriceKind.FULL,
    ):
        return Listing(
            'MANUAL',
            'a',
            'Tesla Model 3',
            9000000,
            kind,
            attributes={
                'year': 2022,
                'mileage_km': 75000,
                'generation': 'pre-highland',
                'drive_variant': drive,
                'battery_chemistry': 'LFP',
            },
        )

    def test_drive(self):
        self.assertNotEqual(
            classify_car(
                self.tesla('RWD')
            ).key,
            classify_car(
                self.tesla('LONG_RANGE')
            ).key,
        )

    def test_lease(self):
        self.assertIsNone(
            classify_car(
                self.tesla(
                    'RWD',
                    PriceKind.LEASE,
                )
            ).key
        )

    def test_unknown_battery(self):
        car = Listing(
            'MANUAL',
            't',
            'Tesla Model 3',
            9000000,
            PriceKind.FULL,
            attributes={
                'year': 2022,
                'mileage_km': 30000,
                'generation': 'old',
                'drive_variant': 'RWD',
            },
        )

        self.assertIsNone(
            classify_car(car).key
        )

    def test_unknown_model(self):
        car = Listing(
            'MANUAL',
            'x',
            'Auto osobowe',
            100000,
            PriceKind.FULL,
        )

        self.assertIsNone(
            classify_car(car).key
        )
