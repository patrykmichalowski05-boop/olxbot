"""Oddzielne dane developerskie, istniejące konto mobilne."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BridgeConfig:
    auth_db: Path
    legacy_root: Path
    dev_dir: Path
    manual_enabled: bool

    @classmethod
    def from_env(cls):
        auth = os.environ.get('FLIP_API_AUTH_DB', '')
        legacy = os.environ.get('FLIP_API_DATA_ROOT', '')
        dev = os.environ.get('FLIP_UNIVERSAL_DEV_DIR', '')

        if not all((auth, legacy, dev)):
            raise RuntimeError(
                'Brak zmiennych FLIP_API_* lub '
                'FLIP_UNIVERSAL_DEV_DIR'
            )

        if not Path(dev).is_absolute():
            raise RuntimeError(
                'FLIP_UNIVERSAL_DEV_DIR musi byc '
                'absolutna sciezka'
            )

        root = Path(dev).resolve()
        prod = Path('/opt/olx-bot')

        if root == prod or prod in root.parents:
            raise RuntimeError(
                'Zabroniona lokalizacja developerskich baz'
            )

        if not root.is_dir():
            raise RuntimeError(
                'Utworz katalog FLIP_UNIVERSAL_DEV_DIR '
                'przed startem'
            )

        return cls(
            auth_db=Path(auth).resolve(),
            legacy_root=Path(legacy).resolve(),
            dev_dir=root,
            manual_enabled=(
                os.environ.get(
                    'FLIP_UNIVERSAL_ENABLE_MANUAL'
                ) == '1'
            ),
        )
