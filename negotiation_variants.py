def _round_25(value):
    return round(
        float(value) / 25
    ) * 25


def _message(price):
    price = int(
        round(price)
    )

    return (
        f"Dzień dobry, czy {price} zł "
        "byłoby do przyjęcia? "
        "Jeśli tak, mogę szybko "
        "sfinalizować zakup."
    )


def build_variants(
    negotiation,
    opening=None,
):
    max_buy = negotiation.get(
        "max_buy"
    )

    my_offer = negotiation.get(
        "my_offer"
    )

    seller_offer = negotiation.get(
        "seller_offer"
    )


    if max_buy is None:
        return []


    max_buy = float(
        max_buy
    )


    # Sprzedający już podał cenę
    # mieszczącą się w naszym limicie.
    if (
        seller_offer is not None
        and float(seller_offer) <= max_buy
    ):

        price = float(
            seller_offer
        )

        return [
            {
                "key": "accept",
                "label": "AKCEPTUJ CENĘ",
                "price": price,
                "message": (
                    f"Dzień dobry, "
                    f"{int(round(price))} zł "
                    "jest dla mnie w porządku. "
                    "Mogę szybko sfinalizować zakup."
                ),
            }
        ]


    # Punkt startowy negocjacji.
    if my_offer is not None:

        base = float(
            my_offer
        )

        room = (
            max_buy
            - base
        )

        if room <= 0:
            prices = [
                max_buy
            ]

        elif room <= 75:

            prices = [
                base + room * 0.33,
                base + room * 0.66,
                max_buy,
            ]

        else:

            prices = [
                base + min(
                    25,
                    room * 0.25,
                ),

                base + min(
                    75,
                    room * 0.55,
                ),

                base + min(
                    125,
                    room * 0.80,
                ),
            ]

    else:

        if opening is not None:
            base = float(
                opening
            )

        else:
            base = (
                max_buy
                - 200
            )

        base = min(
            base,
            max_buy
        )

        prices = [
            base,
            base + 50,
            base + 100,
        ]


    # Zaokrąglamy i pilnujemy MAX BUY.
    clean = []

    for price in prices:

        price = min(
            _round_25(price),
            max_buy,
        )

        if price not in clean:
            clean.append(
                price
            )


    # Jeśli przez mały zakres ceny się
    # zdublowały, dokładamy MAX BUY.
    if (
        max_buy not in clean
        and len(clean) < 3
    ):
        clean.append(
            max_buy
        )


    labels = [
        (
            "aggressive",
            "🔥 AGRESYWNA",
        ),
        (
            "normal",
            "⚖️ NORMALNA",
        ),
        (
            "quick",
            "⚡ SZYBKI DEAL",
        ),
    ]


    variants = []

    for index, price in enumerate(
        clean[:3]
    ):

        key, label = labels[
            min(
                index,
                len(labels) - 1,
            )
        ]

        variants.append({
            "key": key,
            "label": label,
            "price": price,
            "message": _message(
                price
            ),
        })


    return variants
