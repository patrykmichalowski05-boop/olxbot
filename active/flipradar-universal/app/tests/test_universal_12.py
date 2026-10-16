import sqlite3
import tempfile
import unittest

from pathlib import Path
from universal_v2.legacy_readonly import recent


class Test12(unittest.TestCase):

    def test_latest_search_and_readonly(self):

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'offer_snapshots.db'

            with sqlite3.connect(p) as d:
                d.execute('''
                    CREATE TABLE snapshots(
                        id INTEGER PRIMARY KEY,
                        offer_key TEXT,
                        title TEXT,
                        url TEXT,
                        created_at TEXT
                    )
                ''')

                d.executemany(
                    'INSERT INTO snapshots VALUES (?,?,?,?,?)',
                    [
                        (1, 'a', 'stara karta', '', ''),
                        (2, 'a', 'nowa RTX 5060', '', ''),
                        (3, 'b', 'iPhone', '', ''),
                        (4, 'c', 'RTX 3070', '', ''),
                    ]
                )

            before = p.read_bytes()

            self.assertEqual(
                [r['id'] for r in recent(p, search='RTX')],
                [4, 2]
            )

            self.assertEqual(
                [
                    r['id']
                    for r in recent(
                        p,
                        before_id=4,
                        search='RTX'
                    )
                ],
                [2]
            )

            self.assertEqual(before, p.read_bytes())
