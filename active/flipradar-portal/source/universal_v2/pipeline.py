from .model import (
    Listing,
    PriceKind,
    Decision,
)

from .registry import identify
from .sources import Sources
from .store import Store
from .comparables import estimate
from .valuation import calculate, decide
from .profiles import Profile
from .outbox import Outbox


def analyze(
    row: Listing,
    category: str,
    sources: Sources,
    profile: Profile,
    store: Store,
    outbox: Outbox,
    comparables,
    costs,
):
    sources.check(
        row,
        'import',
    )

    sources.check(
        row,
        'analyze',
    )

    sources.check(
        row,
        'store',
    )

    if not profile.eligible(
        row,
        category,
    ):
        return {
            'decision': Decision.SKIP.value,
            'reason': 'PROFILE_MISMATCH',
        }

    identity = identify(
        category,
        row,
    )

    observation_id, _ = store.observe(
        row
    )

    market = estimate(
        comparables,
        identity.key,
        row.external_id,
    )

    if (
        row.price_kind != PriceKind.FULL
        or identity.key is None
    ):
        market = {
            'status': 'NO_RELIABLE_VALUATION',
            'reason': 'INCOMPLETE_OR_WRONG_PRICE_KIND',
        }

    if market['status'] != 'OK':
        decision = (
            Decision.NO_RELIABLE_VALUATION.value
        )

        value = {
            'reason': market['reason'],
        }

    else:
        limits = profile.limits(
            category
        )

        value = calculate(
            row.price_minor,
            market['base_minor'],
            costs,
            limits['min_profit_minor'],
        )

        decision = decide(
            market,
            value,
            limits,
        )

    result = {
        'observation_id': observation_id,
        'category': category,
        'identity': identity.key,
        'decision': decision,
        'market': market,
        'valuation': value,
        'warnings': identity.warnings,
    }

    vid, _ = store.valuation(
        observation_id,
        'universal-v2',
        'profile-' + profile.user_id,
        'offline-sample',
        result,
    )

    if (
        decision
        == Decision.BUY_CANDIDATE.value
    ):
        sources.check(
            row,
            'notify',
        )

        outbox.enqueue(
            f'{profile.user_id}:{vid}:{decision}',
            result,
        )

    return result
