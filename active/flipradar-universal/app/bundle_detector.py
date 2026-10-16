import re
import unicodedata


# ============================================================
# HELPERS
# ============================================================

def normalize(text):

    if not text:
        return ""

    text = str(text).lower()

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = "".join(
        c
        for c in text
        if not unicodedata.combining(c)
    )

    # Ujednolicenie separatorów:
    # PC + monitor
    # PC/monitor
    # PC z monitorem

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def contains_any(
    text,
    phrases,
):

    return any(
        phrase in text
        for phrase in phrases
    )


# ============================================================
# MONITOR
# ============================================================

def detect_monitor(text):

    strong = [
        "nanoips",
        "nano ips",
        "monitor 4k",
        "monitor 32",
        "monitor 34",
        "monitor 27",
        "monitor 240hz",
        "monitor 165hz",
        "monitor 144hz",
        "ultrawide",
    ]

    if contains_any(
        text,
        strong
    ):

        return {
            "type": "monitor",
            "label": "Monitor",
            "quick_value": 800,
            "confidence": "HIGH",
        }

    if "monitor" in text:

        return {
            "type": "monitor",
            "label": "Monitor",
            "quick_value": 400,
            "confidence": "MEDIUM",
        }

    return None


# ============================================================
# WHEEL
# ============================================================

def detect_wheel(text):

    strong = [
        "t300rs",
        "t300 rs",
        "t300 rs gt",
        "t248",
        "g29",
        "g920",
        "g923",
        "fanatec",
        "moza r5",
        "moza r9",
    ]

    if contains_any(
        text,
        strong
    ):

        return {
            "type": "wheel",
            "label": "Kierownica / Simracing",
            "quick_value": 600,
            "confidence": "HIGH",
        }

    generic = [
        "kierownica",
        "simracing",
        "sim racing",
    ]

    if contains_any(
        text,
        generic
    ):

        return {
            "type": "wheel",
            "label": "Kierownica / Simracing",
            "quick_value": 300,
            "confidence": "MEDIUM",
        }

    return None


# ============================================================
# SHIFTER
# ============================================================

def detect_shifter(text):

    if contains_any(
        text,
        [
            "th8a",
            "th8s",
            "shifter",
        ]
    ):

        return {
            "type": "shifter",
            "label": "Shifter",
            "quick_value": 300,
            "confidence": "HIGH",
        }

    if contains_any(
        text,
        [
            "skrzynia biegow",
            "lewarek",
        ]
    ):

        return {
            "type": "shifter",
            "label": "Shifter",
            "quick_value": 150,
            "confidence": "MEDIUM",
        }

    return None


# ============================================================
# HOTAS
# ============================================================

def detect_hotas(text):

    if contains_any(
        text,
        [
            "hotas",
            "x52",
            "x56",
            "warthog",
            "t16000m",
        ]
    ):

        return {
            "type": "hotas",
            "label": "HOTAS",
            "quick_value": 250,
            "confidence": "HIGH",
        }

    if contains_any(
        text,
        [
            "joystick lotniczy",
            "joystick do latania",
        ]
    ):

        return {
            "type": "hotas",
            "label": "Joystick lotniczy",
            "quick_value": 120,
            "confidence": "MEDIUM",
        }

    return None


# ============================================================
# VR
# ============================================================

def detect_vr(text):

    if contains_any(
        text,
        [
            "meta quest",
            "oculus quest",
            "quest 2",
            "quest 3",
            "pico 4",
            "valve index",
            "htc vive",
        ]
    ):

        return {
            "type": "vr",
            "label": "VR",
            "quick_value": 600,
            "confidence": "HIGH",
        }

    if contains_any(
        text,
        [
            "gogle vr",
            "zestaw vr",
            "vr headset",
        ]
    ):

        return {
            "type": "vr",
            "label": "VR",
            "quick_value": 300,
            "confidence": "MEDIUM",
        }

    return None


# ============================================================
# PERIPHERALS
# ============================================================

def detect_peripherals(text):

    matches = 0

    for phrase in [
        "klawiatura",
        "mysz",
        "sluchawki",
        "headset",
    ]:

        if phrase in text:
            matches += 1

    if matches >= 2:

        return {
            "type": "peripherals",
            "label": "Peryferia",
            "quick_value": 100,
            "confidence": "LOW",
        }

    return None


# ============================================================
# DESK
# ============================================================

def detect_desk(text):

    if contains_any(
        text,
        [
            "biurko gamingowe",
            "gaming desk",
            "biurko",
        ]
    ):

        return {
            "type": "desk",
            "label": "Biurko",
            "quick_value": 100,
            "confidence": "LOW",
        }

    return None


# ============================================================
# EXPLICIT BUNDLE
# ============================================================

def explicit_bundle_detected(text):

    phrases = [
        "mega setup",
        "kompletny setup",
        "pelny setup",
        "caly setup",
        "gaming setup",
        "zestaw gamingowy",
        "kompletny zestaw",
        "caly zestaw",
        "zestaw pc",
        "pc + monitor",
        "pc z monitorem",
        "komputer + monitor",
        "komputer z monitorem",
        "komputer wraz z monitorem",
    ]

    if contains_any(
        text,
        phrases
    ):

        return True

    # Obsługuje:
    #
    # komputer gamingowy + monitor 27
    # komputer do gier + monitor
    # PC gamingowy + monitor

    if re.search(
        r"\b(?:komputer|pc)\b.{0,50}\+\s*monitor\b",
        text
    ):

        return True

    if re.search(
        r"\b(?:komputer|pc)\b.{0,50}\bz monitorem\b",
        text
    ):

        return True

    return False


# ============================================================
# MAIN
# ============================================================

def analyze_bundle(details):

    details = details or {}

    title = details.get(
        "title",
        ""
    )

    description = details.get(
        "description",
        ""
    )

    text = normalize(
        f"{title}\n{description}"
    )

    explicit_bundle = (
        explicit_bundle_detected(
            text
        )
    )

    detectors = [
        detect_monitor,
        detect_wheel,
        detect_shifter,
        detect_hotas,
        detect_vr,
        detect_peripherals,
        detect_desk,
    ]

    items = []

    for detector in detectors:

        result = detector(
            text
        )

        if result:

            items.append(
                result
            )

    accessory_types = {
        item["type"]
        for item in items
    }

    bonus = sum(
        item["quick_value"]
        for item in items
    )

    high_confidence_items = sum(
        1
        for item in items
        if item["confidence"] == "HIGH"
    )

    # ========================================================
    # SCORE
    # ========================================================

    score = 0

    if explicit_bundle:
        score += 3

    score += len(
        accessory_types
    )

    score += high_confidence_items

    # ========================================================
    # BUNDLE
    # ========================================================

    is_bundle = (
        explicit_bundle
        and len(items) >= 1
    ) or (
        len(accessory_types) >= 2
    )

    strong_bundle = (
        is_bundle
        and (
            score >= 6
            or bonus >= 800
        )
    )

    if strong_bundle:

        confidence = "HIGH"

    elif is_bundle:

        confidence = "MEDIUM"

    else:

        confidence = "LOW"

    return {
        "is_bundle":
            is_bundle,

        "strong_bundle":
            strong_bundle,

        "confidence":
            confidence,

        "score":
            score,

        "explicit_bundle":
            explicit_bundle,

        "items":
            items,

        "item_count":
            len(items),

        "accessory_quick_value":
            bonus,
    }


# ============================================================
# SELF TEST
# ============================================================

if __name__ == "__main__":

    tests = [
        {
            "title":
                "Ryzen 5 5600 RTX 3060 16GB",
            "description":
                "Komputer gamingowy",
        },

        {
            "title":
                "Komputer gamingowy + monitor 27",
            "description":
                "",
        },

        {
            "title":
                (
                    "Kompletny Mega Setup 4K VR "
                    "RTX 4070 Ti i5-13600K "
                    "Monitor LG 32 NanoIPS "
                    "T300RS GT TH8A HOTAS"
                ),

            "description":
                "",
        },
    ]

    for details in tests:

        print()
        print(
            "=" * 80
        )

        print(
            details["title"]
        )

        result = analyze_bundle(
            details
        )

        for key, value in result.items():

            print(
                f"{key:25}: {value}"
            )
