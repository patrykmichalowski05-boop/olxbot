def _money(value):
    if value is None:
        return None

    return int(
        round(float(value))
    )


def build_negotiation_message(
    negotiation,
):
    max_buy = negotiation.get(
        "max_buy"
    )

    seller_offer = negotiation.get(
        "seller_offer"
    )

    next_offer = negotiation.get(
        "next_offer"
    )

    status = negotiation.get(
        "status"
    )


    # Sprzedający zszedł już do
    # akceptowalnej ceny.
    if (
        status == "BUY"
        and seller_offer is not None
    ):
        price = _money(
            seller_offer
        )

        return (
            f"Dzień dobry, {price} zł jest "
            "dla mnie w porządku. "
            "Jeśli oferta jest nadal aktualna, "
            "mogę odebrać komputer jeszcze dzisiaj."
        )


    # Mamy wyliczoną kolejną ofertę.
    if next_offer is not None:

        price = _money(
            next_offer
        )

        return (
            f"Dzień dobry, czy {price} zł "
            "byłoby do przyjęcia? "
            "Jeśli tak, mogę odebrać komputer "
            "jeszcze dzisiaj."
        )


    # Jest limit, ale z jakiegoś powodu
    # nie udało się policzyć następnej ceny.
    if max_buy is not None:

        price = _money(
            max_buy
        )

        return (
            f"Dzień dobry, moja maksymalna "
            f"propozycja to {price} zł. "
            "Jeśli taka cena jest w porządku, "
            "mogę szybko sfinalizować zakup."
        )


    return (
        "Dzień dobry, czy jest możliwość "
        "negocjacji ceny komputera?"
    )
