import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from commercial_core.source_policy import (
    SourceDenied,
    check_source,
    validate_listing,
)


class SourcePolicyTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "policy.json"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, entry):
        self.path.write_text(
            json.dumps({"sources": {"test": entry}}),
            encoding="utf-8",
        )

    def approved(self):
        return {
            "status": "approved",
            "commercial_use": True,
            "evidence_verified": True,
            "evidence_reference": "contract-123",
            "allowed_operations": ["analyze"],
            "expires_at": "2030-01-01T00:00:00Z",
        }

    def test_missing_policy_denied(self):
        with self.assertRaises(SourceDenied):
            check_source("test", "analyze", self.path)

    def test_blocked_source_denied(self):
        self.write({"status": "blocked"})
        with self.assertRaises(SourceDenied):
            check_source("test", "analyze", self.path)

    def test_approved_analysis(self):
        self.write(self.approved())
        self.assertTrue(
            check_source(
                "test", "analyze", self.path,
                now=datetime(2026, 10, 13, tzinfo=timezone.utc),
            )
        )

    def test_redistribution_denied(self):
        self.write(self.approved())
        with self.assertRaises(SourceDenied):
            check_source("test", "redistribute", self.path)

    def test_expired_denied(self):
        entry = self.approved()
        entry["expires_at"] = "2020-01-01T00:00:00Z"
        self.write(entry)
        with self.assertRaises(SourceDenied):
            check_source("test", "analyze", self.path)

    def test_listing_requires_https(self):
        self.write(self.approved())
        with self.assertRaises(ValueError):
            validate_listing(
                {"source": "test", "url": "http://example.com"},
                self.path,
            )

    def test_unverified_denied(self):
        entry = self.approved()
        entry["evidence_verified"] = False
        self.write(entry)
        with self.assertRaises(SourceDenied):
            check_source("test", "analyze", self.path)


if __name__ == "__main__":
    unittest.main()
