"""Ręczna analiza w katalogu developerskim."""

import hashlib
from dataclasses import replace

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from .manual_input import convert
from .guarded_pipeline import analyze_safe
from .model import Decision
from .sources import Sources
from .profiles import Profile
from .store import Store
from .outbox import Outbox


class ManualRequest(BaseModel):
    external_id: str = Field(
        min_length=1,
        max_length=120
    )
    title: str = Field(
        min_length=1,
        max_length=500
    )
    price: str = Field(
        min_length=1,
        max_length=30
    )
    price_kind: str = 'FULL'
    category: str = 'ELECTRONICS'
    description: str = Field(
        default='',
        max_length=10000
    )
    attributes: dict = Field(
        default_factory=dict
    )
    costs_minor: dict[str, int] = Field(
        default_factory=dict
    )


def attach_manual(app, cfg, current_user):

    @app.post('/api/v1/universal/manual/analyze')
    def analyze_offer(
        data: ManualRequest,
        user_id: str = Depends(current_user)
    ):
        if not cfg.manual_enabled:
            raise HTTPException(
                403,
                'Manual analysis disabled'
            )

        if data.category not in (
            'ELECTRONICS',
            'CAR',
            'FASHION'
        ):
            raise HTTPException(
                422,
                'Unsupported category'
            )

        try:
            row = convert({
                'external_id': data.external_id,
                'title': data.title,
                'price': data.price,
                'price_kind': data.price_kind,
                'description': data.description,
                'attributes': data.attributes,
            })

            # Różny identyfikator dla każdego użytkownika.
            private_id = hashlib.sha256(
                (
                    user_id
                    + '\x00'
                    + row.external_id
                ).encode('utf-8')
            ).hexdigest()

            row = replace(
                row,
                external_id='MANUAL:' + private_id
            )

            store = Store(
                cfg.dev_dir / 'observations.sqlite'
            )
            store.init()

            outbox = Outbox(
                cfg.dev_dir / 'outbox.sqlite'
            )
            outbox.init()

            policies = Sources({
                'MANUAL': {
                    'mode': 'IMPORT_ONLY',
                    'operations': [
                        'import',
                        'analyze',
                        'store',
                        'notify'
                    ]
                }
            })

            profile = Profile(
                user_id=user_id,
                name='manual',
                categories=(
                    'ELECTRONICS',
                    'CAR',
                    'FASHION'
                ),
                sources=('MANUAL',),
                budget_minor=1_000_000_000
            )

            result = analyze_safe(
                row,
                data.category,
                policies,
                profile,
                store,
                outbox,
                [],
                data.costs_minor
            )

            # Nie mamy tu cen faktycznie sprzedanych
            # przedmiotów. Nie wolno wymyślać okazji.
            if (
                result.get('decision')
                == Decision.BUY_CANDIDATE.value
            ):
                raise RuntimeError(
                    'Unexpected candidate without market data'
                )

            return result

        except (ValueError, TypeError) as exc:
            raise HTTPException(
                422,
                str(exc)
            ) from None
