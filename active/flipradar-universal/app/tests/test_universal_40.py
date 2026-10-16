import unittest
from pathlib import Path


class Test40(unittest.TestCase):

    def test_mobile_panel_wired(self):
        app = Path(
            'mobile/App.tsx'
        ).read_text(encoding='utf-8')

        self.assertIn(
            "import UniversalPanel",
            app
        )
        self.assertIn(
            "<UniversalPanel />",
            app
        )
        self.assertIn(
            "setScreen('universal')",
            app
        )
