import unittest
from backend.app.db.models import Deal

class Test61(unittest.TestCase):
    def test_pagination_index(self):
        names = {i.name for i in Deal.__table__.indexes}
        self.assertIn('ix_deals_workspace_created_id', names)
