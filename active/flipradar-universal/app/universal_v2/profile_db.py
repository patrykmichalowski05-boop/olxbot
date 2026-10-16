import json
import sqlite3

from dataclasses import asdict
from pathlib import Path

from .profiles import Profile


class ProfileDB:

    def __init__(self, path):
        self.path = Path(path).resolve()

        if (
            Path('/opt/olx-bot') == self.path
            or Path('/opt/olx-bot') in self.path.parents
        ):
            raise ValueError(
                'baza produkcyjna zabroniona'
            )

    def init(self):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with sqlite3.connect(self.path) as d:
            d.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles(
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    data TEXT NOT NULL,
                    PRIMARY KEY(user_id,name)
                )
            ''')

    def save(self, profile):
        if not isinstance(profile, Profile):
            raise TypeError(
                'wymagany Profile'
            )

        raw = json.dumps(
            asdict(profile),
            ensure_ascii=False,
            sort_keys=True
        )

        with sqlite3.connect(self.path) as d:
            d.execute('''
                INSERT INTO user_profiles
                VALUES(?,?,?)
                ON CONFLICT(user_id,name)
                DO UPDATE SET data=excluded.data
            ''', (
                profile.user_id,
                profile.name,
                raw
            ))

    def get(self, user_id, name):
        with sqlite3.connect(self.path) as d:
            row = d.execute('''
                SELECT data
                FROM user_profiles
                WHERE user_id=?
                AND name=?
            ''', (
                user_id,
                name
            )).fetchone()

        if row is None:
            return None

        data = json.loads(row[0])

        data['categories'] = tuple(
            data['categories']
        )

        data['sources'] = tuple(
            data['sources']
        )

        return Profile(**data)
