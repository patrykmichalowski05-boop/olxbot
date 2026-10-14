import unittest

from backend.app.api.app import create_app


class Test66(unittest.TestCase):

    def test_app_factory_available(self):
        self.assertTrue(
            callable(create_app)
        )
