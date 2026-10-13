import re

CPU_INTEL = re.compile(
    r'(?<![A-Z0-9])(?:INTEL\s+)?(?:CORE\s+)?'
    r'(I[3579])\s*[- ]?\s*'
    r'(\d{4,5}(?:HK|KF|KS|HX|F|K|T|H|U)?)'
    r'(?![A-Z0-9])',
    re.I
)

CPU_AMD = re.compile(
    r'(?<![A-Z0-9])(?:AMD\s+)?RYZEN\s*'
    r'([3579])\s*[- ]?\s*'
    r'(\d{4,5}(?:X3D|XT|GT|GE|X|G|F)?)'
    r'(?![A-Z0-9])',
    re.I
)

GPU = re.compile(
    r'(?<![A-Z0-9])(RTX|GTX|RX)\s*[- ]?\s*'
    r'(\d{3,4})'
    r'(?:\s*[- ]?\s*(TI|SUPER|XTX|XT))?'
    r'(?:\s*[- ]?\s*(SUPER))?'
    r'(?![A-Z0-9])',
    re.I
)

SIZES = r'(?:4|8|12|16|24|32|48|64|96|128)'

RAM_PATTERNS = [
    re.compile(
        r'(?<![A-Z0-9])(?:RAM|PAMIEC|DDR[345])'
        r'\s*[:=\-]?\s*(' + SIZES + r')\s*GB\b',
        re.I
    ),
    re.compile(
        r'\b(' + SIZES + r')\s*GB\s*'
        r'(?:RAM|PAMIEC|DDR[345])\b',
        re.I
    ),
]

RAM_MULTIPLIER = re.compile(
    r'(?<![A-Z0-9])([234])\s*[X×]\s*('
    + SIZES + r')\s*GB\s*(?:RAM|DDR[345])?\b',
    re.I
)

RAM_ALTERNATIVES = re.compile(
    r'\b\d{1,3}\s*/\s*\d{1,3}\s*GB\b',
    re.I
)


def unique(values):
    values = set(values)
    return next(iter(values)) if len(values) == 1 else None


def extract(title):
    text = str(title or "").upper()
    text = text.replace("Ę", "E").replace("Ć", "C")

    cpus = [
        f"{generation.upper()}-{model.upper()}"
        for generation, model in CPU_INTEL.findall(text)
    ]

    cpus.extend(
        f"RYZEN {generation} {model.upper()}"
        for generation, model in CPU_AMD.findall(text)
    )

    gpus = []

    for family, number, variant, suffix in GPU.findall(text):
        model = " ".join(
            x for x in (
                family.upper(),
                number,
                variant.upper(),
                suffix.upper()
            ) if x
        )
        gpus.append(model)

    rams = []

    if not RAM_ALTERNATIVES.search(text):
        spans = []

        for match in RAM_MULTIPLIER.finditer(text):
            capacity = int(match.group(1)) * int(match.group(2))

            if capacity <= 128:
                rams.append(capacity)

            spans.append((match.start(), match.end()))

        masked = list(text)

        for start, end in spans:
            masked[start:end] = " " * (end - start)

        masked = "".join(masked)

        for pattern in RAM_PATTERNS:
            rams.extend(
                int(value)
                for value in pattern.findall(masked)
            )

    return {
        "cpu": unique(cpus),
        "gpu": unique(gpus),
        "ram_gb": unique(rams),
    }
