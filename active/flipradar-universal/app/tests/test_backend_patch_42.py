import unittest
from pydantic import ValidationError
from universal_v2.manual_routes import ManualRequest


class ManualValidationTest(unittest.TestCase):

    def setUp(self):
        self.data = dict(
            external_id='A',
            title='PC',
            price='1000'
        )

    def test_rejects_unexpected_fields(self):
        with self.assertRaises(ValidationError):
            ManualRequest.model_validate({
                **self.data,
                'user_id': 'other'
            })

    def test_rejects_invalid_cost_types(self):
        for value in (True, 1.5):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    ManualRequest.model_validate({
                        **self.data,
                        'costs_minor': {'fee': value}
                    })

    def test_limits_attributes_and_cost_count(self):
        for key, payload in (
            ('attributes', {
                str(i): i for i in range(49)
            }),
            ('costs_minor', {
                str(i): 1 for i in range(33)
            }),
        ):
            with self.subTest(key=key):
                with self.assertRaises(ValidationError):
                    ManualRequest.model_validate({
                        **self.data,
                        key: payload
                    })
