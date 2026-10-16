import json

from pathlib import Path
from datetime import datetime, timezone

from .model import utc, Listing


class SourceDenied(PermissionError):
    pass


PLATFORMS = (
    'OLX',
    'FACEBOOK',
    'ALLEGRO',
    'ALLEGRO_LOKALNIE',
    'OTOMOTO',
    'VINTED',
    'EBAY',
)

OPERATIONS = {
    'discover',
    'fetch',
    'import',
    'store',
    'analyze',
    'notify',
    'redistribute',
}


class Sources:

    def __init__(self, cfg=None):
        self.cfg = (
            cfg if isinstance(cfg, dict) else {}
        )

    @classmethod
    def from_json(cls, path):
        p = Path(path)

        if not p.is_file() or p.is_symlink():
            raise SourceDenied(
                'Brak polityki źródeł'
            )

        data = json.loads(
            p.read_text(encoding='utf-8')
        )

        if (
            not isinstance(data, dict)
            or not isinstance(
                data.get('sources'),
                dict,
            )
        ):
            raise SourceDenied(
                'Zła polityka'
            )

        return cls(data['sources'])

    def check(
        self,
        row: Listing,
        operation: str,
    ):
        if operation not in OPERATIONS:
            raise SourceDenied(
                'Nieznana operacja'
            )

        policy = self.cfg.get(
            row.source,
            {},
        )

        if not isinstance(policy, dict):
            raise SourceDenied(
                'Błąd polityki'
            )

        mode = policy.get(
            'mode',
            'DISABLED',
        )

        operations = policy.get(
            'operations',
            [],
        )

        if (
            mode not in (
                'DISABLED',
                'IMPORT_ONLY',
                'AUTHORIZED',
            )
            or not isinstance(
                operations,
                list,
            )
        ):
            raise SourceDenied(
                'Zła konfiguracja'
            )

        if (
            mode == 'DISABLED'
            or operation not in operations
        ):
            raise SourceDenied(
                'Brak zgody na operację'
            )

        if mode == 'IMPORT_ONLY':
            if operation in (
                'discover',
                'fetch',
                'redistribute',
            ):
                raise SourceDenied(
                    'Tylko import'
                )

            if row.provenance not in (
                'user_supplied',
                'first_party',
            ):
                raise SourceDenied(
                    'Import wymaga legalnie dostarczonych danych'
                )

            return

        # Flaga administratora nie zastępuje
        # prawnego potwierdzenia uprawnień.
        if (
            policy.get('commercial_use')
            is not True
            or policy.get('evidence_verified')
            is not True
            or not isinstance(
                policy.get('evidence_reference'),
                str,
            )
            or not policy.get(
                'evidence_reference'
            ).strip()
        ):
            raise SourceDenied(
                'Brak potwierdzonych uprawnień'
            )

        if (
            not policy.get('expires_at')
            or utc(
                policy['expires_at']
            ) <= datetime.now(
                timezone.utc
            ).isoformat()
        ):
            raise SourceDenied(
                'Brak ważnego terminu uprawnienia'
            )

        allowed = policy.get(
            'categories',
            [],
        )

        if not isinstance(allowed, list):
            raise SourceDenied(
                'Błąd listy kategorii'
            )
