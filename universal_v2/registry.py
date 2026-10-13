from .electronics import classify_electronics
from .vehicles import classify_car
from .fashion import classify_fashion


ENGINES = {
    'ELECTRONICS': classify_electronics,
    'CAR': classify_car,
    'FASHION': classify_fashion,
}


def register(name, engine):
    if name in ENGINES:
        raise ValueError(
            'Kategoria już istnieje'
        )

    if not callable(engine):
        raise TypeError(
            'Silnik musi być funkcją'
        )

    ENGINES[name] = engine


def identify(category, listing):
    if category not in ENGINES:
        raise ValueError(
            'Nieobsługiwana kategoria'
        )

    return ENGINES[category](listing)
