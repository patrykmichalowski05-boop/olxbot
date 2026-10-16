from dataclasses import dataclass
from enum import Enum

from .money import valid_minor


class Condition(str, Enum):
    GOOD = "GOOD"
    NORMAL = "NORMAL"
    RISK = "RISK"
    BAD = "BAD"
    UNKNOWN = "UNKNOWN"


ALIASES = {
    "good": Condition.GOOD,
    "normal": Condition.NORMAL,
    "risk": Condition.RISK,
    "risky": Condition.RISK,
    "bad": Condition.BAD,
}


def normalize_condition(value):
    if isinstance(value, Condition):
        return value

    return ALIASES.get(
        str(value or "").strip().lower(),
        Condition.UNKNOWN,
    )


@dataclass(frozen=True)
class FlipPolicy:
    min_profit_minor: int = 40000
    hot_profit_minor: int = 70000
    max_purchase_minor: int = 0
    min_roi_bps: int = 0
    version: str = "pc-legacy-v1"

    def __post_init__(self):
        for name in (
            "min_profit_minor",
            "hot_profit_minor",
            "max_purchase_minor",
        ):
            valid_minor(getattr(self, name))

        if self.hot_profit_minor < self.min_profit_minor:
            raise ValueError("Nieprawidlowy prog HOT")

        if (
            type(self.min_roi_bps) is not int
            or not 0 <= self.min_roi_bps <= 100000
        ):
            raise ValueError("Nieprawidlowy ROI")

    @classmethod
    def from_legacy_settings(cls, settings):
        return cls(
            min_profit_minor=int(
                settings.get("min_profit", 400)
            ) * 100,
            hot_profit_minor=int(
                settings.get("hot_profit", 700)
            ) * 100,
            max_purchase_minor=int(
                settings.get("max_purchase_price", 0)
            ) * 100,
        )

    def decide(
        self,
        purchase_minor,
        profit_minor,
        *,
        confidence="LOW",
        condition="unknown",
    ):
        valid_minor(purchase_minor, positive=True)

        if type(profit_minor) is not int:
            raise ValueError("Nieprawidlowy zysk")

        if (
            self.max_purchase_minor
            and purchase_minor > self.max_purchase_minor
        ):
            return "SKIP"

        if normalize_condition(condition) == Condition.BAD:
            return "REVIEW"

        if str(confidence).upper() != "HIGH":
            return "REVIEW"

        if profit_minor < self.min_profit_minor:
            return "SKIP"

        if (
            profit_minor * 10000
            < purchase_minor * self.min_roi_bps
        ):
            return "SKIP"

        if profit_minor >= self.hot_profit_minor:
            return "HOT"

        return "BUY"
