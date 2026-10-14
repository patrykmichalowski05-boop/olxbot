import unittest
from pathlib import Path


class Test38(unittest.TestCase):

    def test_legacy_default_and_opt_in(self):
        config = Path(
            "mobile/src/utils/config.ts"
        ).read_text(encoding="utf-8")

        radar = Path(
            "mobile/src/api/endpoints/radar.ts"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "EXPO_PUBLIC_FLIP_RADAR_SOURCE",
            config,
        )

        self.assertIn(
            "    : 'legacy';",
            config,
        )

        self.assertIn(
            "/api/v1/universal/mobile-radar",
            radar,
        )

        self.assertIn(
            "/api/v1/radar",
            radar,
        )
