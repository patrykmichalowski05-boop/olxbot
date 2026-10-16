QUESTION_MAP = {
    "psu": (
        "Jaki jest dokładny model i moc zasilacza?"
    ),

    "gpu_temp": (
        "Jakie temperatury osiąga karta graficzna "
        "pod obciążeniem / po benchmarku?"
    ),

    "cpu_temp": (
        "Jakie temperatury osiąga procesor "
        "pod obciążeniem?"
    ),

    "smart": (
        "Czy może Pan wysłać zdjęcie "
        "CrystalDiskInfo / SMART dysku?"
    ),

    "benchmark": (
        "Czy może Pan wysłać wynik benchmarku "
        "karty graficznej, np. FurMark, "
        "3DMark albo Unigine?"
    ),

    "inside_photo": (
        "Czy można dostać wyraźne zdjęcie "
        "wnętrza komputera?"
    ),

    "serial": (
        "Czy można potwierdzić numery seryjne "
        "lub dokładne modele podzespołów?"
    ),

    "noise": (
        "Czy komputer pracuje cicho? "
        "Czy występują piski cewek, "
        "hałas wentylatorów albo inne odgłosy?"
    ),
}


def build_questions(
    checklist,
):
    questions = []

    for item in checklist:

        status = str(
            item.get(
                "status"
            )
            or
            "UNKNOWN"
        ).upper()

        # UNKNOWN i MISSING oznaczają,
        # że warto zapytać sprzedającego.
        if status not in [
            "UNKNOWN",
            "MISSING",
        ]:
            continue

        key = item.get(
            "key"
        )

        question = (
            QUESTION_MAP.get(
                key
            )
        )

        if question:
            questions.append(
                question
            )

    return questions


def build_message(
    checklist,
):
    questions = build_questions(
        checklist
    )

    if not questions:

        return (
            "Dzień dobry, dziękuję za informacje. "
            "Mam już wszystkie najważniejsze dane "
            "dotyczące komputera."
        )

    lines = [
        "Dzień dobry, mam jeszcze kilka pytań "
        "przed zakupem:",
        "",
    ]

    for question in questions:

        lines.append(
            f"• {question}"
        )

    lines.extend([
        "",
        "Dziękuję.",
    ])

    return "\n".join(
        lines
    )
