"""Historia wycen zależna od wersji dowodów."""

import hashlib
import json


def fingerprint(value):
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
        allow_nan=False
    )

    return hashlib.sha256(
        raw.encode('utf-8')
    ).hexdigest()[:20]


def save_revision(
    store,
    observation_id,
    engine_version,
    user_profile,
    market_evidence,
    result
):
    if (
        not isinstance(engine_version, str)
        or not engine_version.strip()
    ):
        raise ValueError(
            'brak wersji silnika'
        )

    market_id = fingerprint(
        market_evidence
    )

    return store.valuation(
        observation_id,
        engine_version,
        'profile-' + user_profile,
        market_id,
        result
    )
