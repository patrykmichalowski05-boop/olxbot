import pytest

from universal_v2.hunter.matching import attributes, matches
from universal_v2.hunter.models import Offer, Search

PROFILE = Search(
    "rtx-4070-12gb",
    "test-owner",
    "RTX 4070 12GB",
    "RTX 4070",
    platforms=("ALLEGRO_LOKALNIE",),
    attributes={"vram_gb": 12},
)


def listing(title: str) -> Offer:
    return Offer(
        platform="ALLEGRO_LOKALNIE",
        external_id="test",
        title=title,
        price_minor=100000,
        url="https://allegrolokalnie.pl/oferta/test-radar",
    )


@pytest.mark.parametrize("title", [
    "Gigabyte AORUS 15X ASF | i9-13980HX | RTX 4070 | 32GB RAM | 1TB SSD",
    "ASUS Zenbook Pro 14 UX6404VI i9 13900H 32GB 2TB RTX4070",
    "Lenovo ThinkPad P1 Gen7 Intel Ultra 7 32GB 1TB RTX 4070 16 cali",
    "RTX 4070 / i7-13700K / 32GB DDR5 / 2TB SSD / Z790 WiFi",
    "Hp Victus 16 Rayzen 7 8845HS /16Gb Ram / Rtx 4070 / 512ssd",
    "ASUS ROG STRIX G16 RTX 4070 / 32GB RAM / 1,5TB SSD",
    "HP Victus 16-r1975nd (i7-14650HX / RTX 4070 / 144Hz)",
])
def test_laptop_desktop_never_match_standalone_gpu(title):
    offer = listing(title)
    assert attributes(offer)["item_type"] == "PC"
    assert not matches(offer, PROFILE)


@pytest.mark.parametrize("title", [
    "RTX 4070 MSI Gaming X Trio Karta Graficzna Stan Idealny Cicha Chlodna",
    "Karta Nvidia RTX 4070 Asus Dual cicha chlodna 100% sprawna",
    "Gigabyte GeForce RTX 4070 Windforce OC 12G",
    "Gigabyte AORUS GeForce RTX 4070 Master 12 GB karta graficzna",
    "ASUS ROG STRIX RTX 4070 12GB karta graficzna",
])
def test_standalone_gpu_still_matches(title):
    offer = listing(title)
    assert attributes(offer)["item_type"] == "GPU"
    assert matches(offer, PROFILE)
