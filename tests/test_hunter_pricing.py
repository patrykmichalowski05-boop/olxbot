from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from universal_v2.hunter.matching import comparable_key, matches
from universal_v2.hunter.models import Costs, Offer, Search, money_input, platform_url
from universal_v2.hunter.pricing import estimate, evaluate, quote


def offer(identity="1", price=80000, title="RTX 4070 12GB", **kwargs):
    return Offer(
        "OLX",
        identity,
        title,
        price,
        f"https://www.olx.pl/d/oferta/gpu-ID{identity}.html",
        condition="USED",
        **kwargs,
    )


def search(**kwargs):
    return Search(
        "gpu", "owner-a", "RTX 4070", "RTX 4070", min_profit_minor=20000, **kwargs
    )


def peers(count=5, **kwargs):
    return [offer(str(i + 10), 200000 + i * 1000, **kwargs) for i in range(count)]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1 234,56 zł", 123456),
        ("1.234,56", 123456),
        ("1,234.56", 123456),
        ("2.500", 250000),
        ("1200", 120000),
        ("0,01", 1),
    ],
)
def test_minor_units(raw, expected):
    assert money_input(raw) == expected


def test_json_decimal_is_never_interpreted_as_thousands():
    assert money_input(Decimal("1234.56")) == 123456
    with pytest.raises(ValueError):
        money_input(Decimal("1.234"))


@pytest.mark.parametrize(
    "raw", [1.23, True, "-1", "nan", "1,234", "1e6", None, "1.2.3"]
)
def test_money_rejects_ambiguous_or_fractional_amounts(raw):
    with pytest.raises(ValueError):
        money_input(raw)


@pytest.mark.parametrize(
    "url",
    [
        "http://www.olx.pl/x",
        "https://olx.pl.evil.test/x",
        "https://user:pass@olx.pl/x",
        "https://olx.pl:8443/x",
        "file:///etc/passwd",
    ],
)
def test_url_is_scoped_to_platform(url):
    with pytest.raises(ValueError):
        platform_url("OLX", url)


@pytest.mark.parametrize(
    "title",
    [
        "RTX 4070 TI 12GB",
        "RTX 4070 SUPER 12GB",
        "Komputer RTX 4070 32GB",
        "RTX 40700 12GB",
        "RTX 4070 16GB",
    ],
)
def test_model_and_variant_do_not_leak(title):
    candidate = offer(title=title)
    assert not matches(candidate, search(attributes={"vram_gb": 12}))


@pytest.mark.parametrize(
    "title",
    [
        "Lenovo LOQ15ARP9 / RTX 4070 / Ryzen 7 / 16 GB RAM / 1 TB SSD",
        "ASUS ROG Zephyrus G16 RTX 4070 / 32GB RAM / OLED",
        "HP OMEN 17 RTX 4070 8GB / 16GB DDR5",
        "Dell Alienware m16R1 RTX 4070 / 32 GB RAM",
    ],
)
def test_laptop_ram_never_becomes_desktop_gpu_vram(title):
    from universal_v2.hunter.matching import attributes

    listing = offer(title=title)
    observed = attributes(listing)
    assert observed["item_type"] == "PC"
    assert not matches(listing, search(attributes={"vram_gb": 12}))


def test_known_desktop_gpu_vram_and_explicit_conflict():
    from universal_v2.hunter.matching import attributes

    standalone = offer(title="RTX 4070 MSI Gaming X Trio karta graficzna")
    spec = attributes(standalone)
    assert spec["item_type"] == "GPU"
    assert spec["vram_gb"] == 12
    assert spec["vram_source"] == "MODEL_SPEC"
    assert matches(standalone, search(attributes={"vram_gb": 12}))

    contradictory = offer(title="RTX 4070 16GB karta graficzna")
    assert attributes(contradictory)["vram_gb"] == 16
    assert not matches(contradictory, search(attributes={"vram_gb": 12}))

    unknown_variant = offer(title="RTX 5060 Ti karta graficzna")
    assert "vram_gb" not in attributes(unknown_variant)


def test_phone_suffix_and_storage_are_distinct():
    profile = Search("phone", "a", "phone", "iPhone 14")
    assert not matches(offer(title="iPhone 14 Pro 128GB"), profile)
    a = offer(title="iPhone 14 128GB")
    b = offer("2", title="iPhone 14 256GB")
    assert comparable_key(a, profile) != comparable_key(b, profile)


@pytest.mark.parametrize(
    "query,title",
    [
        ("iPhone 14", "iPhone14ProMax 128GB"),
        ("RTX 4070", "RTX4070TiSuper 16GB"),
        ("Galaxy S23", "Samsung Galaxy S23+ 128GB"),
        ("iPhone 14 Pro", "Case iPhone 14 Pro 128GB"),
        ("iPhone 14 Pro", "Szkło iPhone 14 Pro 128GB"),
    ],
)
def test_compact_suffixes_and_accessories_do_not_match_base_model(query, title):
    assert not matches(offer(title=title), Search("variant", "a", query, query))


@pytest.mark.parametrize(
    "attributes",
    [
        {"year": {"min": "2010"}},
        {"year": {"min": 2020, "max": 2010}},
        {"bad": []},
        {"year": True},
        {"year": {"gte": 3}},
        {"x": float("nan")},
    ],
)
def test_search_validates_filters_before_scanning(attributes):
    with pytest.raises(ValueError):
        search(attributes=attributes)


def test_profit_and_roi_include_every_cost_and_ceiling_satisfies_both_limits():
    costs = Costs(
        shipping_minor=2000,
        repairs_minor=10000,
        travel_minor=3000,
        other_minor=1000,
        sale_fee_bps=600,
        reserve_bps=500,
    )
    value = quote(80000, 150000, costs, 20000, 2000)
    assert value["cost_minor"] == 29000
    assert value["profit_minor"] == 41000
    assert value["roi_bps"] == 41000 * 10000 // 109000
    ceiling = value["max_buy_minor"]
    assert quote(ceiling, 150000, costs, 20000, 2000)["affordable"]
    assert not quote(ceiling + 1, 150000, costs, 20000, 2000)["affordable"]


def test_zero_cost_ceiling_and_no_profitable_price():
    assert quote(0, 1, Costs(reserve_bps=0), 1, 5000)["affordable"]
    assert not quote(100, 100, Costs(shipping_minor=500), 1, 0)["affordable"]


def test_asking_prices_are_discounted_and_never_labelled_confirmed_sales():
    result = evaluate(offer(), search(), peers())
    assert result["qualifies"] is True
    assert result["decision"] == "WATCH"
    assert result["market"]["kind"] == "ASKING"
    assert result["market"]["resale_minor"] < result["market"]["low_minor"]
    assert result["valuation"]["profit_after_tax"] is False
    assert not evaluate(offer(), search(allow_asking_alerts=False), peers())[
        "qualifies"
    ]


def test_verified_sales_need_evidence_and_enough_independent_sellers():
    with pytest.raises(ValueError):
        offer(status="SOLD_VERIFIED")
    sold = peers(status="SOLD_VERIFIED", sale_evidence="imported-order-reference")
    assert evaluate(offer(), search(), sold)["decision"] == "BUY_CANDIDATE"
    assert (
        estimate(offer(), search(), peers(seller_key="one-seller"))["status"]
        == "NO_RELIABLE_VALUATION"
    )


def test_stale_future_removed_wrong_model_and_self_are_not_comparables():
    now = datetime.now(timezone.utc)
    bad = [
        offer(),
        offer("3", status="REMOVED"),
        offer("4", observed_at=(now - timedelta(days=30)).isoformat()),
        offer("5", observed_at=(now + timedelta(days=2)).isoformat()),
        offer("6", title="RTX 4070 TI 12GB"),
    ]
    assert estimate(offer(), search(), bad)["status"] == "NO_RELIABLE_VALUATION"
    assert not evaluate(
        offer(observed_at=(now + timedelta(days=2)).isoformat()), search(), peers()
    )["qualifies"]


@pytest.mark.parametrize(
    "title",
    [
        "RTX 4070 12GB uszkodzona",
        "RTX 4070 12GB samo pudełko",
        "Kupie RTX 4070 12GB",
        "RTX 4070 12GB raty",
    ],
)
def test_dangerous_title_is_not_a_deal(title):
    assert not evaluate(offer(title=title), search(), peers())["qualifies"]


def test_description_defects_and_negation():
    assert not evaluate(offer(description="Karta nie działa"), search(), peers())[
        "qualifies"
    ]
    assert evaluate(
        offer(description="Nie jest uszkodzona, bez uszkodzeń."), search(), peers()
    )["qualifies"]


def test_cheap_watch_has_no_invented_profit():
    profile = Search(
        "chair", "a", "Krzesło", "krzesło", purpose="cheap", max_price_minor=10000
    )
    result = evaluate(offer(title="Krzesło", price=5000), profile, [])
    assert result["qualifies"]
    assert result["valuation"] is None
    assert result["decision"] == "WATCH"


def test_unknown_product_without_variant_has_no_fabricated_roi():
    profile = Search("generic", "a", "Ikea Pax", "Ikea Pax")
    candidate = offer(title="Ikea Pax")
    comparisons = [offer(str(i), price=200000, title="Ikea Pax") for i in range(10, 20)]
    assert evaluate(candidate, profile, comparisons)["valuation"] is None


def test_car_missing_variant_and_distinct_mileage_bands():
    profile = Search("car", "a", "Golf", "Volkswagen Golf", category="CAR")
    base = offer(
        title="Volkswagen Golf 2018",
        attributes={
            "year": 2018,
            "mileage_km": 110000,
            "engine": "2.0 TDI",
            "gearbox": "manual",
        },
    )
    assert comparable_key(base, profile)
    assert comparable_key(replace(base, attributes={}), profile) is None
    assert comparable_key(
        replace(base, attributes={**base.attributes, "mileage_km": 210000}), profile
    ) != comparable_key(base, profile)
