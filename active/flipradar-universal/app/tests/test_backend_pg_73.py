import unittest

from pydantic import ValidationError

from backend.app.api.app import IngestBody
from backend.app.services.listing_ingest import ingest


class Test73(unittest.TestCase):

    def test_reject_float(self):
        with self.assertRaises(ValidationError):
            IngestBody(
                source="OLX",
                source_scope="PL",
                external_id="1",
                title="PC",
                price_minor=1.25,
            )

    def test_invalid_platform(self):
        with self.assertRaises(ValueError):
            ingest(
                None,
                "workspace",
                source="olx",
                source_scope="PL",
                external_id="1",
                title="PC",
                price_minor=100,
                payload={},
                key="request123",
            )

    def test_payload_limit(self):
        with self.assertRaises(ValueError):
            ingest(
                None,
                "workspace",
                source="OLX",
                source_scope="PL",
                external_id="1",
                title="PC",
                price_minor=100,
                payload={"x": "a" * 9000},
                key="request123",
            )
