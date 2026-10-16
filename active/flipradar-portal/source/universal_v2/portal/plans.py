from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Plan:
    code: str
    name: str
    price_minor: int
    searches: int | None
    days: int | None
    notifications: bool

    def payload(self):
        return {
            **asdict(self),
            "currency": "PLN",
            "prices_are_examples": True,
            "activation": "ADMIN_REVIEW",
        }


PLANS = {
    "START": Plan("START", "Start", 0, 3, None, False),
    "STANDARD": Plan("STANDARD", "Standard", 1900, 20, 30, True),
    "PLUS": Plan("PLUS", "Plus", 3900, 60, 90, True),
    "LEGACY": Plan("LEGACY", "Dotychczasowy dostęp", 0, None, None, True),
}
PUBLIC_PLANS = ("START", "STANDARD", "PLUS")
