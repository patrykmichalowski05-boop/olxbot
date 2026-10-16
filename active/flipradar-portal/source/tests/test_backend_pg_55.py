import unittest

from backend.app.api.app import (
    PurchaseBody,
    CostBody,
    SaleBody,
)
from pydantic import ValidationError


class Test55(unittest.TestCase):

    def test_money_is_integer_minor(self):
        with self.assertRaises(ValidationError):
            PurchaseBody(
                listing_id="x",
                amount_minor=1.5,
            )

        with self.assertRaises(ValidationError):
            SaleBody(amount_minor=True)

    def test_cost_valid(self):
        result = CostBody(
            kind="REPAIR",
            amount_minor=15000,
        )

        self.assertEqual(
            result.amount_minor,
            15000,
        )

    def test_extra_fields_forbidden(self):
        with self.assertRaises(ValidationError):
            PurchaseBody.model_validate({
                "listing_id": "abc",
                "amount_minor": 10000,
                "workspace_id": "other",
            })
