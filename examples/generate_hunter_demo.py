"""Synthetic data only. Run from the repository root; no network or secrets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from universal_v2.hunter.models import PLATFORMS

PRODUCTS = [
    ("gpu", "RTX 4070 12GB", "ELECTRONICS", 200000, 95000, {"vram_gb": 12}, []),
    ("phone", "iPhone 14 128GB", "ELECTRONICS", 190000, 80000, {"storage_gb": 128}, []),
    (
        "car",
        "Volkswagen Golf 2018 2.0 TDI manual",
        "CAR",
        5500000,
        3000000,
        {
            "year": 2018,
            "mileage_km": 118000,
            "engine": "2.0 TDI",
            "gearbox": "manual",
            "generation": "VII",
            "body_type": "hatchback",
        },
        ["generation", "body_type"],
    ),
    (
        "fashion",
        "Nike Dunk Low DD1503-101 38",
        "FASHION",
        40000,
        10000,
        {"style_code": "DD1503-101", "size": "38"},
        [],
    ),
    ("tools", "Makita DDF484 body", "TOOLS", 45000, 15000, {"kit": "body"}, ["kit"]),
]


def demo_url(platform, number):
    return {
        "OLX": f"https://www.olx.pl/d/oferta/demo-ID{number}.html",
        "FACEBOOK": f"https://www.facebook.com/marketplace/item/{number}/",
        "ALLEGRO_LOKALNIE": f"https://allegrolokalnie.pl/oferta/demo-{number}",
        "OTOMOTO": f"https://www.otomoto.pl/osobowe/oferta/demo-ID{number}.html",
        "VINTED": f"https://www.vinted.pl/items/{number}-demo",
    }[platform]


def generate(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    feeds = {p: [] for p in PLATFORMS}
    profiles = []
    for n, (key, title, category, reference, bargain, attrs, variant_keys) in enumerate(
        PRODUCTS
    ):
        query = {
            "gpu": "RTX 4070",
            "phone": "iPhone 14",
            "car": "Volkswagen Golf",
            "fashion": "Nike Dunk Low",
            "tools": "Makita DDF484",
        }[key]
        profiles.append(
            {
                "id": key,
                "name": f"DEMO · {title}",
                "query": query,
                "category": category,
                "attributes": attrs,
                "variant_keys": variant_keys,
                "notify_initial": True,
                "min_profit_minor": 5000,
                "min_roi_bps": 1500,
                "costs": {"shipping_minor": 1500, "reserve_bps": 500},
            }
        )
        for i in range(6):
            platform = PLATFORMS[(n + i) % len(PLATFORMS)]
            identity = str(1000000000 + n * 100 + i)
            feeds[platform].append(
                {
                    "platform": platform,
                    "external_id": identity,
                    "title": title,
                    "price_minor": bargain if i == 0 else reference + i * 100,
                    "url": demo_url(platform, identity),
                    "condition": "USED",
                    "attributes": attrs,
                    "seller_key": f"demo-seller-{n}-{i}",
                }
            )
    for platform, items in feeds.items():
        (root / f"{platform.lower()}.json").write_text(
            json.dumps({"items": items}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    config = {
        "owner_id": "demo-owner",
        "database": "hunter.sqlite3",
        "sources": [
            {"platform": p, "mode": "json", "feed_path": f"{p.lower()}.json"}
            for p in PLATFORMS
        ],
        "searches": profiles,
    }
    target = root / "config.json"
    target.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="runtime/demo")
    args = parser.parse_args()
    print(generate(Path(args.output)).resolve())
