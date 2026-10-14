import unittest
from pathlib import Path


class Test38(unittest.TestCase):

    def test_legacy_default_and_opt_in(self):
        text = Path(
            'mobile/src/api.ts'
        ).read_text(encoding='utf-8')

        self.assertIn(
            "EXPO_PUBLIC_FLIP_RADAR_SOURCE === 'universal'",
            text
        )
        self.assertIn(
            '/api/v1/universal/mobile-radar',
            text
        )
        self.assertIn(
            ": '/api/v1/radar'",
            text
        )
