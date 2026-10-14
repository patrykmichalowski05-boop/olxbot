"""Bezpieczna kontrola przed wycena."""

from .model import Decision, assert_minor
from .price_guard import check as price_check
from .registry import identify
from .pipeline import analyze


def analyze_safe(
    row, category, sources, profile,
    store, outbox, comps, costs
):
    for operation in ('import', 'analyze', 'store'):
        sources.check(row, operation)

    if not isinstance(costs, dict):
        raise ValueError('Niepoprawne koszty')

    for name, value in costs.items():
        if not isinstance(name, str) or not name:
            raise ValueError('Niepoprawna nazwa kosztu')
        assert_minor(value)

    identity = identify(category, row)
    purchase = price_check(row)

    if not purchase['ok'] or not identity.key:
        obs_id, _ = store.observe(row)

        result = {
            'observation_id': obs_id,
            'decision': (
                Decision.NO_RELIABLE_VALUATION.value
            ),
            'reasons': (
                list(purchase['reasons'])
                + list(identity.warnings)
            ),
            'notification_queued': False,
        }

        # Brak ceny rynkowej nie oznacza braku
        # informacji dla radaru.
        # Profil chroni izolacje uzytkownikow.
        store.valuation(
            obs_id,
            'guarded-no-valuation-v1',
            'profile-' + profile.user_id,
            'NO_RELIABLE_MARKET',
            result,
        )

        return result

    return analyze(
        row, category, sources, profile,
        store, outbox, comps, costs
    )
