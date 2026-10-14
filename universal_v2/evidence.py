"""Pochodzenie danych i dowody transakcji."""

from dataclasses import dataclass

from .model import Listing, assert_minor
from .comparables import Comparable


@dataclass(frozen=True)
class SaleEvidence:
    source: str
    reference_id: str
    comparable_key: str
    amount_minor: int
    currency: str
    state: str
    proof_ref: str = ''
    reviewed: bool = False
    provenance: str = 'user_supplied'

    def __post_init__(self):
        assert_minor(self.amount_minor)

        if not all((
            self.source,
            self.reference_id,
            self.comparable_key
        )):
            raise ValueError('Brak identyfikatorow')

        if self.currency != 'PLN':
            raise ValueError('Wymagana waluta PLN')

        if self.state not in {
            'ASKING', 'SALE_CONFIRMED', 'REMOVED'
        }:
            raise ValueError('Niepoprawny status')

        if self.provenance not in {
            'user_supplied',
            'licensed_feed',
            'first_party'
        }:
            raise ValueError('Nieznane pochodzenie')

        if self.state == 'SALE_CONFIRMED':
            if not self.reviewed or not self.proof_ref.strip():
                raise ValueError(
                    'Wymagany dowod i reczna weryfikacja'
                )


def permitted_comparables(samples, policies):
    result = []

    for sample in samples:
        row = Listing(
            sample.source,
            sample.reference_id,
            'Dowod transakcji',
            sample.amount_minor,
            provenance=sample.provenance
        )

        for operation in ('import', 'analyze'):
            policies.check(row, operation)

        if sample.state == 'REMOVED':
            continue

        kind = (
            'SOLD_VERIFIED'
            if sample.state == 'SALE_CONFIRMED'
            else 'ASKING'
        )

        result.append(
            Comparable(
                sample.comparable_key,
                sample.reference_id,
                sample.amount_minor,
                kind,
                (
                    sample.proof_ref
                    if kind == 'SOLD_VERIFIED'
                    else ''
                )
            )
        )

    return result
