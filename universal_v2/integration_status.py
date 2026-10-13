"""Status informacyjny nie nadaje dostępu do platform."""

from dataclasses import dataclass


KNOWN = (
    'OLX',
    'FACEBOOK',
    'ALLEGRO',
    'ALLEGRO_LOKALNIE',
    'OTOMOTO',
    'VINTED',
    'EBAY',
)


@dataclass(frozen=True)
class Integration:

    platform: str

    state: str = 'DISABLED'

    detail: str = 'Niezweryfikowany dostep'

    def __post_init__(self):
        if self.platform not in KNOWN:
            raise ValueError('Nieznana platforma')

        if self.state not in (
            'DISABLED',
            'IMPORT_ONLY',
            'ACCESS_PENDING',
        ):
            raise ValueError('Nieznany status')

    @property
    def auto_discovery_available(self):
        # Brak zatwierdzonego adaptera.
        return False


def catalog():
    return [
        Integration(name)
        for name in KNOWN
    ]
