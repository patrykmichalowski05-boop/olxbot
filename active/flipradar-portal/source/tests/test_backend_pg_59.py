import unittest
from backend.app.db.models import Deal, DealCost

class Test59(unittest.TestCase):
    def test_timestamps_are_db_generated(self):
        for model in (Deal, DealCost):
            column = model.__table__.c.created_at
            self.assertIsNotNone(column.server_default)
            self.assertFalse(column.nullable)
