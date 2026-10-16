"""Conservative asking-price market evidence for desktop PCs.

Listing prices are NOT confirmed transaction prices.
This module NEVER issues automatic BUY decisions.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3

from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from .category_router import categorize
from .contracts import RawListing, SourceStatus


ENGINE_VERSION = "asking-evidence-v1"

REQUIRED_COLUMNS = frozenset({
    "offer_id",
    "title",
    "url",
    "price",
    "cpu",
    "gpu",
    "ram",
    "last_seen",
    "active",
})

RISK_RESERVE_MINOR = 10000


def normalize_cpu(value):
    text = re.sub(
        r"\s+",
        " ",
        str(value or "").upper().strip(),
    )

    text = re.sub(
        r"\b(?:INTEL|CORE|AMD)\b",
        "",
        text,
    ).strip()

    intel = re.search(
        r"(?<![A-Z0-9])"
        r"I([3579])[- ]?"
        r"(\d{4,5})"
        r"(KF|KS|F|K|T)?"
        r"(?![A-Z0-9])",
        text,
    )

    if intel:
        return (
            f"I{intel.group(1)}-"
            f"{intel.group(2)}"
            f"{intel.group(3) or ''}"
        )

    ryzen = re.search(
        r"(?<![A-Z0-9])"
        r"(?:RYZEN\s+|R)"
        r"([3579])[- ]?"
        r"(\d{4,5})"
        r"(X3D|X|G|GE)?"
        r"(?![A-Z0-9])",
        text,
    )

    if ryzen:
        return (
            f"RYZEN {ryzen.group(1)} "
            f"{ryzen.group(2)}"
            f"{ryzen.group(3) or ''}"
        )

    return None


def normalize_gpu(value):
    text = re.sub(
        r"\s+",
        " ",
        str(value or "").upper().strip(),
    )

    match = re.search(
        r"(?<![A-Z0-9])"
        r"(RTX|GTX|RX)"
        r"\s*[- ]?\s*"
        r"(\d{3,4})"
        r"\s*"
        r"(TI\s+SUPER|SUPER|TI|XTX|XT)?"
        r"(?![A-Z0-9])",
        text,
    )

    if not match:
        return None

    suffix = re.sub(
        r"\s+",
        " ",
        match.group(3) or "",
    ).strip()

    return (
        f"{match.group(1)} {match.group(2)}"
        + (f" {suffix}" if suffix else "")
    )


def normalize_ram(value):
    if isinstance(value, bool):
        return None

    try:
        number = int(value)

        if (
            2 <= number <= 256
            and str(value).strip() == str(number)
        ):
            return number

        return None

    except (
        ValueError,
        TypeError,
        OverflowError,
    ):
        return None


def hardware_key(cpu, gpu, ram):
    cpu = normalize_cpu(cpu)
    gpu = normalize_gpu(gpu)
    ram = normalize_ram(ram)

    if cpu and gpu and ram:
        return cpu, gpu, ram

    return None


def canonical_id(url):
    try:
        parsed = urlsplit(str(url or ""))

        if parsed.scheme not in (
            "http",
            "https",
        ):
            return None

        host = (
            parsed.hostname or ""
        ).lower()

        if (
            host not in {"olx.pl", "www.olx.pl"}
            and not host.endswith(".olx.pl")
        ):
            return None

        match = re.search(
            r"\b(ID[A-Z0-9]+)\b",
            parsed.path.upper(),
        )

        if match:
            return match.group(1)

        return (
            host
            + parsed.path.rstrip("/").lower()
        )

    except ValueError:
        return None


def read_time(text):
    try:
        if not text:
            return None

        result = datetime.fromisoformat(
            str(text)
        )

        if result.tzinfo is not None:
            return (
                result.astimezone()
                .replace(tzinfo=None)
            )

        return result

    except (
        ValueError,
        TypeError,
        OverflowError,
    ):
        return None


def percentile(values, fraction):
    values = sorted(values)

    if not values:
        return None

    position = (
        len(values) - 1
    ) * fraction

    lower = int(math.floor(position))
    upper = int(math.ceil(position))

    return round(
        values[lower]
        + (
            values[upper] - values[lower]
        ) * (position - lower)
    )


class MarketEvidence:

    def __init__(
        self,
        market_path,
        *,
        max_age_days=30,
        min_samples=5,
    ):
        if (
            not 1 <= max_age_days <= 90
            or not 3 <= min_samples <= 30
        ):
            raise ValueError(
                "Nieprawidlowe ustawienia rynku"
            )

        self.path = Path(
            market_path
        ).resolve()

        self.max_age_days = max_age_days
        self.min_samples = min_samples

        self.rows = []
        self.total_loaded = 0
        self.rejections = {}

        self.read_market()

    def _reject(self, reason):
        self.rejections[reason] = (
            self.rejections.get(reason, 0) + 1
        )

    def read_market(self):
        if not self.path.is_file():
            raise FileNotFoundError(self.path)

        uri = self.path.as_uri() + "?mode=ro"

        with closing(
            sqlite3.connect(
                uri,
                uri=True,
                timeout=20,
            )
        ) as conn:
            conn.row_factory = sqlite3.Row

            columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(market_offers)"
                )
            }

            missing = (
                REQUIRED_COLUMNS - columns
            )

            if missing:
                raise ValueError(
                    "Brak kolumn market_offers: "
                    + ", ".join(sorted(missing))
                )

            raw = conn.execute("""
                SELECT
                    offer_id,
                    title,
                    url,
                    price,
                    cpu,
                    gpu,
                    ram,
                    last_seen,
                    active
                FROM market_offers
                WHERE price IS NOT NULL
                ORDER BY last_seen DESC
                LIMIT 20000
            """).fetchall()

        now = datetime.now()

        cutoff = now - timedelta(
            days=self.max_age_days
        )

        seen_urls = set()

        self.total_loaded = len(raw)

        for item in raw:
            row = dict(item)

            when = read_time(
                row["last_seen"]
            )

            if (
                when is None
                or when < cutoff
                or when > now + timedelta(days=1)
            ):
                self._reject(
                    "STALE_OR_INVALID_DATE"
                )
                continue

            if row["active"] != 1:
                self._reject("NOT_ACTIVE")
                continue

            price = row["price"]

            if (
                isinstance(price, bool)
                or not isinstance(
                    price, (float, int)
                )
                or not math.isfinite(price)
                or not 100 <= price <= 100000
            ):
                self._reject("BAD_PRICE")
                continue

            key = hardware_key(
                row["cpu"],
                row["gpu"],
                row["ram"],
            )

            if key is None:
                self._reject(
                    "INCOMPLETE_SPECS"
                )
                continue

            title = str(
                row["title"] or ""
            )

            if re.search(
                r"\b("
                r"uszkodzony|"
                r"niesprawny|"
                r"nie\s+dziala|"
                r"na\s+czesci|"
                r"bez\s+karty|"
                r"bez\s+gpu"
                r")\b",
                title,
                re.I,
            ):
                self._reject(
                    "DAMAGED_OR_INCOMPLETE"
                )
                continue

            if re.search(
                r"\b("
                r"laptop\w*|"
                r"notebook\w*|"
                r"macbook\w*|"
                r"thinkpad\w*|"
                r"probook\w*|"
                r"ideapad\w*|"
                r"chromebook\w*|"
                r"legion\w*"
                r")\b",
                title,
                re.I,
            ):
                self._reject(
                    "POSSIBLE_LAPTOP"
                )
                continue

            if re.search(
                r"\b("
                r"karta\s+graficzna|"
                r"monitor|"
                r"bez\s+komputera"
                r")\b",
                title,
                re.I,
            ):
                self._reject(
                    "POSSIBLE_PART_OR_BUNDLE"
                )
                continue

            url_id = canonical_id(
                row["url"]
            )

            if url_id is None:
                self._reject(
                    "INVALID_OLX_URL"
                )
                continue

            parsed_listing = RawListing(
                platform="OLX",
                external_id=str(
                    row["offer_id"]
                ),
                canonical_url=str(
                    row["url"]
                ),
                title=title,
                description="",
                price_minor=round(
                    price * 100
                ),
                currency="PLN",
                status=SourceStatus.UNKNOWN,
                fetched_at=str(
                    row["last_seen"]
                ),
                parser_version=(
                    "market-evidence-v1"
                ),
            )

            classified = categorize(
                parsed_listing,
                hints={
                    "cpu": row["cpu"],
                    "gpu": row["gpu"],
                    "ram": row["ram"],
                },
            )

            if (
                classified.category
                != "DESKTOP_PC"
                or not classified
                .pc_pricing_input_complete
            ):
                self._reject(
                    "NOT_VERIFIED_DESKTOP"
                )
                continue

            classified_key = hardware_key(
                classified.attributes.get(
                    "cpu"
                ),
                classified.attributes.get(
                    "gpu"
                ),
                classified.attributes.get(
                    "ram_gb"
                ),
            )

            if classified_key != key:
                self._reject(
                    "SPECS_TITLE_MISMATCH"
                )
                continue

            if url_id in seen_urls:
                self._reject(
                    "DUPLICATE_URL"
                )
                continue

            seen_urls.add(url_id)

            self.rows.append({
                "offer_id": str(
                    row["offer_id"]
                ),
                "canonical_id": url_id,
                "key": key,
                "price_minor": round(
                    price * 100
                ),
                "last_seen": str(
                    row["last_seen"]
                ),
            })

    def estimate(
        self,
        category,
        *,
        target_price_minor,
        target_url="",
    ):
        base = {
            "engine_version":
                ENGINE_VERSION,

            "price_source":
                "OLX_ACTIVE_ASKING_PRICES",

            "confirmed_sales": 0,

            "automatic_buy_allowed": False,

            "decision": "REVIEW",

            "status": "INSUFFICIENT_DATA",

            "comparable_count": 0,

            "asking_p25_minor": None,

            "asking_median_minor": None,

            "illustrative_resale_minor": None,

            "illustrative_profit_minor": None,

            "risk_reserve_minor":
                RISK_RESERVE_MINOR,

            "additional_costs_unknown": True,

            "note": (
                "Asking prices are not "
                "confirmed transactions. "
                "Human review required."
            ),
        }

        if (
            getattr(
                category,
                "category",
                None,
            ) != "DESKTOP_PC"
            or not getattr(
                category,
                "pc_pricing_input_complete",
                False,
            )
        ):
            return {
                **base,
                "status": "NOT_ELIGIBLE",
            }

        attrs = category.attributes

        key = hardware_key(
            attrs.get("cpu"),
            attrs.get("gpu"),
            attrs.get("ram_gb"),
        )

        if (
            key is None
            or type(target_price_minor) is not int
            or target_price_minor <= 0
        ):
            return {
                **base,
                "status": "INVALID_TARGET",
            }

        own = canonical_id(
            target_url
        )

        pool = [
            row
            for row in self.rows
            if (
                row["key"] == key
                and row["canonical_id"] != own
            )
        ]

        pool = list({
            row["canonical_id"]: row
            for row in pool
        }.values())

        if len(pool) < self.min_samples:
            return {
                **base,
                "status": "INSUFFICIENT_DATA",
                "comparable_count": len(pool),
            }

        prices = [
            row["price_minor"]
            for row in pool
        ]

        median = percentile(
            prices,
            0.5,
        )

        filtered = [
            row
            for row in pool
            if (
                median * 0.4
                <= row["price_minor"]
                <= median * 3
            )
        ]

        if len(filtered) < self.min_samples:
            return {
                **base,
                "status":
                    "INSUFFICIENT_AFTER_FILTER",

                "comparable_count":
                    len(filtered),
            }

        prices = [
            row["price_minor"]
            for row in filtered
        ]

        p25 = percentile(
            prices, 0.25
        )

        median = percentile(
            prices, 0.5
        )

        # Scenariusz orientacyjny:
        # 10% ponizej Q1 cen ofertowych.
        # Nie jest to potwierdzona cena sprzedazy.

        resale = (
            p25 * 90 // 100
        )

        profit = (
            resale
            - target_price_minor
            - RISK_RESERVE_MINOR
        )

        fingerprint = hashlib.sha256(
            json.dumps(
                sorted((
                    row["offer_id"],
                    row["price_minor"],
                    row["last_seen"],
                ) for row in filtered),
                separators=(",", ":"),
            ).encode()
        ).hexdigest()[:20]

        return {
            **base,

            "status": "SCENARIO_ONLY",

            "comparable_count":
                len(filtered),

            "asking_p25_minor":
                p25,

            "asking_median_minor":
                median,

            "illustrative_resale_minor":
                resale,

            "illustrative_profit_minor":
                profit,

            "roi_bps_before_unknown_costs":
                profit * 10000
                // (
                    target_price_minor
                    + RISK_RESERVE_MINOR
                ),

            "market_fingerprint":
                fingerprint,

            "market_age_limit_days":
                self.max_age_days,
        }
