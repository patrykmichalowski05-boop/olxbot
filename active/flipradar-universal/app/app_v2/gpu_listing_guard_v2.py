import re

from .gpu_attributes_v1 import analyze, normalize


def assess(title):
    text = normalize(title)
    attrs = analyze(title)

    def result(status, reason):
        return {
            "status": status,
            "reason": reason,
            "attributes": attrs
        }

    if attrs["model"] != "RTX 5060":
        return result("REJECT", "INNY_MODEL")

    # Oferty innych kart z RTX 5060 w opisie.
    if re.search(
        r"\b(radeon|powercolor|rx[\s-]*\d{4})\b",
        text
    ):
        return result("REJECT", "INNA_KARTA")

    # Kompletne komputery i laptopy.
    if re.search(
        r"\b(komputer\w*|laptop\w*|notebook\w*|"
        r"zestaw\w*|desktop|stacjonarn\w*|"
        r"gaming pc|pc do gier|g4m3r|"
        r"hp omen|level go)\b",
        text
    ):
        return result("REJECT", "CALY_KOMPUTER")

    # Procesory i podzespoly typowe dla calego PC.
    if re.search(
        r"\b(ryzen|core\s+i[3579]|"
        r"core\s+ultra|ultra\s+[3579]|"
        r"i[3579]-?\d{4,5}[a-z]*|"
        r"r[3579]-?\d{4,5}[a-z]*|"
        r"ram|ddr[345]|ssd|nvme)\b",
        text
    ):
        return result("REJECT", "SPECYFIKACJA_PC")

    if re.search(
        r"\b(pudelko|opakowanie|"
        r"uszkodzon\w*|niesprawn\w*|"
        r"do naprawy|na czesci)\b",
        text
    ):
        return result("REJECT", "NIEPELNY_SPRZET")

    if attrs["vram_gb"] == 16:
        return result("REVIEW", "NIEJASNE_16GB")

    if re.search(
        r"\b(zamienie|zamiana|wymienie)\b",
        text
    ):
        return result("REVIEW", "OFERTA_WYMIANY")

    if re.search(
        r"\b(lepszy od|wydajniejszy od|"
        r"alternatywa dla|porownanie z)\b",
        text
    ):
        return result("REVIEW", "POROWNANIE_MODELI")

    # Wymagamy oznak, ze oferta dotyczy GPU,
    # a nie tylko wspomina model.
    if not re.search(
        r"\b(karta graficzna|geforce|gpu|"
        r"asus|msi|palit|pny|zotac|"
        r"gigabyte|gainward|inno3d)\b",
        text
    ):
        return result("REVIEW", "NIEJASNY_PRODUKT")

    return result(
        "STANDALONE_GPU",
        "TYTUL_WSKAZUJE_NA_SAMA_KARTE"
    )
