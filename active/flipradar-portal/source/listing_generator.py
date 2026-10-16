def _clean(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


def _money(value):
    if value is None:
        return None

    try:
        return int(
            round(float(value))
        )
    except (TypeError, ValueError):
        return None


def _disk_text(disks):
    if not disks:
        return None

    if isinstance(
        disks,
        str,
    ):
        return disks.strip()

    if isinstance(
        disks,
        dict,
    ):
        parts = []

        for key, value in disks.items():
            if value:
                parts.append(
                    f"{key}: {value}"
                )

        return ", ".join(parts) or None

    if isinstance(
        disks,
        (list, tuple),
    ):
        parts = []

        for disk in disks:
            if isinstance(
                disk,
                dict,
            ):
                name = (
                    disk.get("name")
                    or disk.get("model")
                    or disk.get("type")
                )

                size = (
                    disk.get("size")
                    or disk.get("capacity")
                )

                text = " ".join(
                    str(x)
                    for x in [
                        name,
                        size,
                    ]
                    if x
                )

                if text:
                    parts.append(text)

            elif disk:
                parts.append(
                    str(disk)
                )

        return ", ".join(parts) or None

    return str(disks)


def _specs(details):
    details = details or {}

    return {
        "cpu": _clean(
            details.get("cpu")
        ),

        "gpu": _clean(
            details.get("gpu")
        ),

        "ram": _clean(
            details.get("ram")
        ),

        "disks": _disk_text(
            details.get("disks")
        ),

        "motherboard": _clean(
            details.get("motherboard")
            or details.get("board")
        ),

        "psu": _clean(
            details.get("psu")
        ),

        "case": _clean(
            details.get("case")
        ),
    }


def build_title(
    details,
):
    specs = _specs(
        details
    )

    parts = [
        "Komputer Gamingowy",
    ]

    for key in (
        "cpu",
        "gpu",
        "ram",
    ):
        value = specs.get(key)

        if value:
            parts.append(
                value
            )

    if specs["disks"]:
        parts.append(
            specs["disks"]
        )

    title = " | ".join(
        parts
    )

    # Tytuł ma być konkretny i niezbyt długi.
    if len(title) > 120:
        title = title[:117].rstrip() + "..."

    return title


def build_olx_description(
    details,
    sale_prep,
):
    specs = _specs(
        details
    )

    price = _money(
        sale_prep.get(
            "target_price"
        )
    )

    lines = [
        "Na sprzedaż w pełni sprawny, "
        "przygotowany do użytkowania komputer.",
        "",
        "SPECYFIKACJA:",
    ]

    mapping = [
        (
            "Procesor",
            specs["cpu"],
        ),
        (
            "Karta graficzna",
            specs["gpu"],
        ),
        (
            "Pamięć RAM",
            specs["ram"],
        ),
        (
            "Dysk / dyski",
            specs["disks"],
        ),
        (
            "Płyta główna",
            specs["motherboard"],
        ),
        (
            "Zasilacz",
            specs["psu"],
        ),
        (
            "Obudowa",
            specs["case"],
        ),
    ]

    for label, value in mapping:
        if value:
            lines.append(
                f"• {label}: {value}"
            )

    lines.extend([
        "",
        "Komputer został sprawdzony "
        "przed wystawieniem.",
        "Przetestowane zostało działanie "
        "podzespołów, temperatury oraz stabilność.",
    ])

    prep_cost = float(
        sale_prep.get(
            "prep_cost"
        )
        or 0
    )

    if prep_cost > 0:
        lines.append(
            "Sprzęt został dodatkowo "
            "przygotowany do sprzedaży."
        )

    lines.extend([
        "",
        "Komputer jest gotowy do użytkowania.",
        "Możliwość sprawdzenia sprzętu "
        "przed zakupem.",
    ])

    if price:
        lines.extend([
            "",
            f"Cena: {price} zł",
        ])

    lines.extend([
        "",
        "W razie pytań zapraszam do kontaktu.",
    ])

    return "\n".join(
        lines
    )


def build_facebook_description(
    details,
    sale_prep,
):
    specs = _specs(
        details
    )

    price = _money(
        sale_prep.get(
            "target_price"
        )
    )

    headline = []

    if specs["cpu"]:
        headline.append(
            specs["cpu"]
        )

    if specs["gpu"]:
        headline.append(
            specs["gpu"]
        )

    title = (
        " + ".join(headline)
        if headline
        else "Komputer Gamingowy"
    )

    lines = [
        f"🔥 {title}",
        "",
    ]

    if price:
        lines.append(
            f"💰 Cena: {price} zł"
        )
        lines.append("")

    mapping = [
        ("⚙️ CPU", specs["cpu"]),
        ("🎮 GPU", specs["gpu"]),
        ("🧠 RAM", specs["ram"]),
        ("💾 Dysk", specs["disks"]),
        ("🔌 PSU", specs["psu"]),
    ]

    for label, value in mapping:
        if value:
            lines.append(
                f"{label}: {value}"
            )

    lines.extend([
        "",
        "✅ Komputer sprawdzony i przetestowany",
        "✅ Gotowy do użytkowania",
        "✅ Możliwość sprawdzenia przed zakupem",
        "",
        "📩 Zainteresowanych zapraszam do wiadomości.",
    ])

    return "\n".join(
        lines
    )


def build_listing(
    details,
    sale_prep,
):
    return {
        "title": build_title(
            details
        ),

        "olx": build_olx_description(
            details,
            sale_prep,
        ),

        "facebook":
            build_facebook_description(
                details,
                sale_prep,
            ),
    }
