import re
from valuation import GPU_VALUES, normalize_gpu


def evaluate_risk(offer):
    result = {
        "risk_review": False,
        "risk_reason": "",
        "risk_reference_zl": None,
    }

    price = offer.get("purchase_zl")

    if type(price) not in (int, float):
        return result

    if price <= 0 or price > 800:
        return result

    cpu = str(offer.get("cpu") or "").upper()
    gpu = normalize_gpu(offer.get("gpu"))

    gpu_reference = GPU_VALUES.get(gpu)

    if isinstance(gpu_reference, (int, float)):
        if gpu_reference > price:
            result.update({
                "risk_review": True,
                "risk_reason": (
                    "Cena całego komputera jest niższa "
                    "od istniejącej ceny referencyjnej GPU. "
                    "Sprawdź, czy oferta dotyczy całego PC, "
                    "jest aktualna i nie jest oszustwem."
                ),
                "risk_reference_zl": gpu_reference,
            })
            return result

    high_cpu = bool(re.search(
        r"\bRYZEN\s+9\b|\bI9[- ]",
        cpu
    ))

    if high_cpu:
        result.update({
            "risk_review": True,
            "risk_reason": (
                "Bardzo niska cena komputera "
                "z procesorem wysokiej klasy. "
                "Wymagana ręczna weryfikacja."
            ),
        })

    return result
