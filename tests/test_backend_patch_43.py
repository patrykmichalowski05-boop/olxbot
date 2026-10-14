import unittest

from pydantic import ValidationError
from universal_v2.watch_routes import (
    WatchRequest,
    CloseRequest
)


class WatchValidationTest(unittest.TestCase):

    def test_blank_rejected(self):
        for cls, data in (
            (WatchRequest, dict(key='   ', label='RTX')),
            (WatchRequest, dict(key='abc', label='   ')),
            (CloseRequest, dict(key='   ')),
        ):
            with self.subTest(cls=cls.__name__):
                with self.assertRaises(ValidationError):
                    cls.model_validate(data)

    def test_trim_and_disallow_extra(self):
        item = WatchRequest(
            key='  OLX-1  ',
            label=' GPU '
        )

        self.assertEqual(
            (item.key, item.label),
            ('OLX-1', 'GPU')
        )

        self.assertEqual(
            CloseRequest(key=' X ').key,
            'X'
        )

        with self.assertRaises(ValidationError):
            WatchRequest.model_validate({
                'key': 'A',
                'label': 'B',
                'user_id': 'other'
            })
