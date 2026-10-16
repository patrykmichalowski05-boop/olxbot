import unittest

from universal_v2.dev_http import handler_factory


class Test30(unittest.TestCase):

    def test_requires_strong_secret(self):
        with self.assertRaises(ValueError):
            handler_factory(
                'bad',
                '/tmp/not-used.sqlite'
            )

    def test_valid_handler(self):
        handler = handler_factory(
            'x' * 40,
            '/tmp/not-used.sqlite'
        )

        self.assertTrue(
            hasattr(handler, 'do_GET')
        )
