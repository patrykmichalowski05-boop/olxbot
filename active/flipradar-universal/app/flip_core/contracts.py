from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class SourceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REMOVED = "REMOVED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Capabilities:
    discover: bool = False
    fetch_listing: bool = False
    verify_listing: bool = False
    publish: bool = False


@dataclass(frozen=True)
class RawListing:
    platform: str
    external_id: str
    canonical_url: str
    title: str
    description: str
    price_minor: int | None
    currency: str
    status: SourceStatus
    fetched_at: str
    parser_version: str


class PlatformConnector(Protocol):
    def capabilities(self) -> Capabilities: ...

    def discover(self, query: str) -> list[RawListing]: ...

    def fetch_listing(
        self,
        external_id: str,
    ) -> RawListing: ...

    def verify_listing(
        self,
        external_id: str,
    ) -> SourceStatus: ...


class CategoryEngine(Protocol):
    def extract_attributes(
        self,
        listing: RawListing,
    ) -> dict: ...

    def validate_completeness(
        self,
        attributes: dict,
    ) -> list[str]: ...

    def comparable_key(
        self,
        attributes: dict,
    ) -> str | None: ...
