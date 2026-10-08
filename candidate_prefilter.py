import re


# ============================================================
# NORMALIZE
# ============================================================

def normalize(text):

    return re.sub(
        r"\s+",
        " ",
        str(text or "").lower(),
    ).strip()


# ============================================================
# MARKERS
# ============================================================

PC_HARDWARE_MARKERS = [
    "rtx 20",
    "rtx 30",
    "rtx 40",
    "rtx 50",

    "gtx 9",
    "gtx 10",
    "gtx 16",

    "rx 5",
    "rx 6",
    "rx 7",
    "rx 9",
    "radeon",

    "ryzen 3",
    "ryzen 5",
    "ryzen 7",
    "ryzen 9",

    "i3-",
    "i3 ",
    "i5-",
    "i5 ",
    "i7-",
    "i7 ",
    "i9-",
    "i9 ",

    "core ultra",
]


FULL_PC_WORDS = [
    "komputer",
    "komputer gamingowy",
    "komputer stacjonarny",
    "gaming pc",
    "gamingowy pc",
    "pc gaming",
    "pecet",
]


# ============================================================
# OBVIOUS PARTS
# ============================================================

PART_PHRASES = [
    "obudowa komputera",
    "obudowa pc",
    "sama obudowa",
    "obudowa gamingowa",

    "zasilacz komputerowy",
    "sam zasilacz",
    "zasilacz atx",

    "płyta główna",
    "plyta glowna",
    "sama płyta",
    "sama plyta",

    "sam procesor",

    "sama karta graficzna",
    "sprzedam kartę graficzną",
    "sprzedam karte graficzna",

    "pamięć ram",
    "pamiec ram",
    "kości ram",
    "kosci ram",

    "sam dysk",
    "dysk ssd",
    "dysk nvme",
    "dysk hdd",

    "chłodzenie cpu",
    "chlodzenie cpu",
    "cooler cpu",

    "wentylator pc",
    "wentylatory pc",

    "zestaw części",
    "zestaw czesci",
]


ACCESSORY_PHRASES = [
    "sam monitor",
    "monitor gamingowy",
    "klawiatura gamingowa",
    "mysz gamingowa",
    "podkładka gamingowa",
    "podkladka gamingowa",
]


# ============================================================
# HELPERS
# ============================================================

def has_pc_hardware(title):

    text = normalize(title)

    return any(
        marker in text
        for marker in PC_HARDWARE_MARKERS
    )


def looks_like_computer(title):

    text = normalize(title)

    return any(
        marker in text
        for marker in FULL_PC_WORDS
    )


# ============================================================
# PREFILTER
# ============================================================

def prefilter_candidate(
    title,
    price=None,
    trigger=None,
):

    text = normalize(title)

    trigger = str(
        trigger or ""
    ).upper()

    hardware = has_pc_hardware(
        text
    )

    computer_word = looks_like_computer(
        text
    )

    # ========================================================
    # BUNDLE
    # ========================================================

    # Bundle może być nietypowo opisany.
    # Nie odrzucamy go tutaj agresywnie.

    if trigger.startswith(
        "BUNDLE"
    ):

        return {
            "skip": False,
            "reason": None,
        }

    # ========================================================
    # OBVIOUS PART
    # ========================================================

    # Nie odrzucamy calego PC tylko dlatego,
    # ze tytul wymienia dysk, RAM lub plyte.

    import re

    full_pc_title = bool(
        re.search(
            r"\b(?:komputer|pecet)\b|jednostka centralna|\b(?:gaming|gamingowy|stacjonarny)\s+pc\b|\bpc\s+(?:gaming|gamingowy|stacjonarny)\b",
            text,
        )
    )

    explicit_part_only = any(
        phrase in text
        for phrase in [
            "sama obudowa",
            "sam zasilacz",
            "sama płyta",
            "sama plyta",
            "sam procesor",
            "sama karta graficzna",
            "sam dysk",
            "same kości ram",
            "same kosci ram",
            "zestaw części",
            "zestaw czesci",
            "tylko obudowa",
            "tylko zasilacz",
            "tylko procesor",
            "tylko karta graficzna",
            "tylko dysk",
        ]
    )

    part_phrase_found = any(
        phrase in text
        for phrase in PART_PHRASES
    )

    cpu_in_title = bool(re.search(
        r"\b(?:ryzen\s*(?:[3579]\s*[- ]?)?\d{4}"
        r"|r[3579]\s*[- ]?\s*\d{4}"
        r"|(?:core\s*)?i[3579]\s*[- ]?\s*\d{4,5})",
        text,
    ))

    gpu_in_title = bool(re.search(
        r"\b(?:rtx|gtx|rx)\s*[- ]?\s*\d{3,4}",
        text,
    ))

    complete_config = cpu_in_title and gpu_in_title

    if part_phrase_found and (
        explicit_part_only
        or not (full_pc_title or complete_config)
    ):

        return {
            "skip": True,
            "reason": "OBVIOUS_PART",
        }

    # ========================================================
    # ACCESSORY ONLY
    # ========================================================

    if (
        any(
            phrase in text
            for phrase in ACCESSORY_PHRASES
        )
        and
        not hardware
    ):

        return {
            "skip": True,
            "reason": "ACCESSORY_ONLY",
        }

    # ========================================================
    # ONLY COMPONENT
    # ========================================================

    only_component = [
        "tylko obudowa",
        "tylko zasilacz",
        "tylko procesor",
        "tylko karta",
        "tylko ram",
        "tylko dysk",
    ]

    if any(
        phrase in text
        for phrase in only_component
    ):

        return {
            "skip": True,
            "reason": "ONLY_COMPONENT",
        }

    # ========================================================
    # VERY LOW PRICE
    # ========================================================

    try:

        numeric_price = int(
            price
        )

    except Exception:

        numeric_price = None

    if (
        numeric_price is not None
        and
        numeric_price < 300
        and
        not hardware
        and
        not computer_word
    ):

        return {
            "skip": True,
            "reason": "LOW_PRICE_NO_PC",
        }

    # ========================================================
    # CHEAP UNKNOWN PC
    # ========================================================

    # To jest celowe:
    #
    # "Komputer Lenovo 150 zł"
    #
    # może wyglądać słabo, ale nie chcemy stracić
    # potencjalnej okazji przez ubogi tytuł.

    if (
        numeric_price is not None
        and
        numeric_price < 300
        and
        computer_word
    ):

        return {
            "skip": False,
            "reason": "CHEAP_UNKNOWN_PC",
        }

    # ========================================================
    # PASS
    # ========================================================

    return {
        "skip": False,
        "reason": None,
    }


# ============================================================
# SELF TEST
# ============================================================

if __name__ == "__main__":

    tests = [
        (
            "Obudowa komputera, zasilacz Feel 300ATX",
            50,
        ),

        (
            "Ryzen 5 5600 RTX 3060 16GB",
            1800,
        ),

        (
            "Karta graficzna RTX 3070",
            900,
        ),

        (
            "Komputer gamingowy i5-10400F RTX 3060",
            1600,
        ),

        (
            "Monitor gamingowy 27 165Hz",
            500,
        ),

        (
            "Komputer stacjonarny Lenovo",
            99,
        ),

        (
            "Mini Komputer HP T630",
            200,
        ),
    ]

    for title, price in tests:

        result = prefilter_candidate(
            title=title,
            price=price,
            trigger="NEW",
        )

        print(
            f"{price:5} zł | "
            f"{str(result['skip']):5} | "
            f"{str(result['reason']):20} | "
            f"{title}"
        )
