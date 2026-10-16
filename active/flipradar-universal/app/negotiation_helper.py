def _latest_amount(
    history,
    kind,
):
    for row in history:
        if row["kind"] == kind:
            value = row["amount"]

            if value is not None:
                return float(value)

    return None


def _calculate_next_offer(
    my_offer,
    seller_offer,
    max_buy,
    opening=None,
):
    if max_buy is None:
        return None

    max_buy = float(max_buy)

    # Sprzedający już jest w naszym limicie
    if (
        seller_offer is not None
        and seller_offer <= max_buy
    ):
        return float(seller_offer)

    # Jeszcze nic nie zaproponowaliśmy
    if my_offer is None:

        if opening is not None:
            proposal = float(opening)

        else:
            proposal = max_buy * 0.90

        # Zaokrąglenie do 50 zł
        proposal = round(
            proposal / 50
        ) * 50

        return min(
            proposal,
            max_buy,
        )

    my_offer = float(my_offer)

    # Już jesteśmy przy limicie
    if my_offer >= max_buy:
        return max_buy

    room = (
        max_buy
        - my_offer
    )

    # Im mniej zostało miejsca,
    # tym mniejszy krok negocjacyjny.
    if room <= 50:
        step = 25

    elif room <= 150:
        step = 50

    else:
        step = 100

    proposal = (
        my_offer
        + step
    )

    return min(
        proposal,
        max_buy,
    )


def calculate_negotiation(
    history,
    max_buy,
    opening=None,
):
    seller_offer = _latest_amount(
        history,
        "SELLER_OFFER",
    )

    my_offer = _latest_amount(
        history,
        "MY_OFFER",
    )

    result = {
        "seller_offer": seller_offer,
        "my_offer": my_offer,
        "max_buy": max_buy,

        "gap": None,

        "room_from_my_offer":
            None,

        "next_offer":
            None,

        "status":
            "NO_DATA",

        "label":
            "Brak ceny sprzedającego",
    }

    if max_buy is None:
        return result

    max_buy = float(
        max_buy
    )

    result["max_buy"] = (
        max_buy
    )

    if my_offer is not None:

        result[
            "room_from_my_offer"
        ] = (
            max_buy
            - my_offer
        )

    result["next_offer"] = (
        _calculate_next_offer(
            my_offer=my_offer,
            seller_offer=seller_offer,
            max_buy=max_buy,
            opening=opening,
        )
    )

    if seller_offer is None:

        result["status"] = (
            "WAITING"
        )

        result["label"] = (
            "Czekamy na cenę sprzedającego"
        )

        return result

    gap = (
        seller_offer
        - max_buy
    )

    result["gap"] = (
        gap
    )

    if gap <= 0:

        result["status"] = (
            "BUY"
        )

        result["label"] = (
            "CENA MIEŚCI SIĘ W MAX BUY"
        )

        return result

    if gap <= 100:

        result["status"] = (
            "CLOSE"
        )

        result["label"] = (
            "BLISKO — NEGOCJUJ DALEJ"
        )

        return result

    if gap <= 250:

        result["status"] = (
            "NEGOTIATE"
        )

        result["label"] = (
            "ZA DROGO — CIŚNIJ CENĘ"
        )

        return result

    result["status"] = (
        "TOO_EXPENSIVE"
    )

    result["label"] = (
        "DUŻO POWYŻEJ MAX BUY"
    )

    return result
