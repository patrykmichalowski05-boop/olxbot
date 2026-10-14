import json

from .dev_radar import radar


class RadarService:

    def __init__(self, path):
        self.path = path

    def page(
        self,
        user,
        query='',
        limit=20,
        before_id=None
    ):
        if (
            not isinstance(user, str)
            or not user
            or len(user) > 120
        ):
            raise ValueError(
                'Nieprawidlowy uzytkownik'
            )

        rows = radar(
            self.path,
            user,
            q=query,
            limit=limit,
            cursor=before_id
        )

        result = []

        for row in rows:
            valuation = json.loads(
                row['result']
            )

            if not isinstance(
                valuation,
                dict
            ):
                raise ValueError(
                    'Zly wynik wyceny'
                )

            result.append({
                'id': row['id'],
                'source': row['source'],
                'external_id': row['ext'],
                'title': row['title'],
                'decision': valuation.get(
                    'decision',
                    'UNKNOWN'
                ),
                'analysis': valuation
            })

        return {
            'items': result,
            'next_before_id': (
                rows[-1]['id']
                if len(rows) == limit
                else None
            )
        }
