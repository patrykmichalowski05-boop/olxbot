from dataclasses import dataclass, field

from .model import assert_minor


@dataclass(frozen=True)
class Profile:
    user_id: str
    name: str

    categories: tuple[str, ...] = (
        'ELECTRONICS',
    )

    sources: tuple[str, ...] = (
        'MANUAL',
    )

    budget_minor: int = 200000
    min_profit_minor: int = 40000
    min_roi_bps: int = 1500
    min_confidence: str = 'MEDIUM'

    overrides: dict = field(
        default_factory=dict
    )

    def __post_init__(self):
        if not self.user_id or not self.name:
            raise ValueError(
                'Brak profilu'
            )

        assert_minor(
            self.budget_minor
        )

        assert_minor(
            self.min_profit_minor
        )

        if (
            type(self.min_roi_bps) is not int
            or not 0 <= self.min_roi_bps <= 100000
        ):
            raise ValueError(
                'Błędne ROI'
            )

        if self.min_confidence not in (
            'LOW',
            'MEDIUM',
            'HIGH',
        ):
            raise ValueError(
                'Błędna pewność'
            )

    def limits(self, category):
        c = self.overrides.get(
            category,
            {},
        )

        min_profit = c.get(
            'min_profit_minor',
            self.min_profit_minor,
        )

        min_roi = c.get(
            'min_roi_bps',
            self.min_roi_bps,
        )

        assert_minor(min_profit)

        if (
            type(min_roi) is not int
            or min_roi < 0
        ):
            raise ValueError(
                'Błędne ROI'
            )

        return {
            'min_profit_minor': min_profit,
            'min_roi_bps': min_roi,
        }

    def eligible(
        self,
        row,
        category,
    ):
        return (
            category in self.categories
            and row.source in self.sources
            and row.price_minor is not None
            and row.price_minor
            <= self.budget_minor
        )
