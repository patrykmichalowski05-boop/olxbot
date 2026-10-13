import re


def parse_cpu(text):
    if not text:
        return None

    # Intel: i5 4570 / i5-10400F / Core i7 9700K
    m = re.search(
        r'(?:intel\s+)?(?:core\s+)?i([3579])[\s-]*(\d{4,5})([a-z]{0,2})\b',
        text,
        re.I
    )

    if m:
        tier = m.group(1)
        model = m.group(2)
        suffix = m.group(3).upper()

        return f"i{tier}-{model}{suffix}"

    # AMD: Ryzen 5 3600 / Ryzen 7 3700X / Ryzen 9 5950X
    m = re.search(
        r'\bryzen\s+([3579])\s+(\d{4})[ \t]*((?:X3D|XT|X|GE|G|HX|HS|H|U)?)\b',
        text,
        re.I
    )

    if m:
        tier = m.group(1)
        model = m.group(2)
        suffix = m.group(3).upper()

        return f"Ryzen {tier} {model}{suffix}"

    return None


def parse_gpu(text):
    if not text:
        return None

    # NVIDIA
    m = re.search(
        r'\b(RTX|GTX)\s*[- ]?\s*(\d{3,4})(?:\s*(SUPER|TI))?\b',
        text,
        re.I
    )

    if m:
        family = m.group(1).upper()
        model = m.group(2)
        suffix = m.group(3)

        gpu = f"{family} {model}"

        if suffix:
            gpu += f" {suffix.upper()}"

        return gpu

    # AMD Radeon
    m = re.search(
        r'\bRX\s*[- ]?\s*(\d{4})(?:\s*(XT|XTX))?\b',
        text,
        re.I
    )

    if m:
        model = m.group(1)
        suffix = m.group(2)

        gpu = f"RX {model}"

        if suffix:
            gpu += f" {suffix.upper()}"

        return gpu

    return None


def parse_ram(text):
    """Read system RAM only from explicit RAM/DDR/kit evidence."""

    if not isinstance(text, str) or not text.strip():
        return None

    qty = r'(?:[1-8]\s*[x×]\s*\d{1,3}|\d{1,3})\s*GB'

    label = (
        r'(?:RAM|pami[eę]ć\s+(?:operacyjna|RAM)|'
        r'system\s+memory)'
    )

    patterns = (
        (
            'ram_before',
            rf'\b{label}\b\s*[:=\-–]?\s*'
            rf'(?:DDR[345]\s*)?(?P<size>{qty})\b',
        ),
        (
            'ram_after',
            rf'(?P<size>{qty})\s*(?:DDR[345]\s*)?'
            rf'\b{label}\b',
        ),
        (
            'ddr_before',
            rf'\bDDR[345]\b\s*[:=\-–]?\s*'
            rf'(?P<size>{qty})\b',
        ),
        (
            'ddr_after',
            rf'(?P<size>{qty})\s*\bDDR[345]\b',
        ),
        (
            'kit',
            r'(?P<size>[1-8]\s*[x×]\s*\d{1,3}\s*GB)\b',
        ),
    )

    for kind, pattern in patterns:
        for match in re.finditer(pattern, text, re.I):

            amount = match.group('size')

            kit = re.fullmatch(
                r'([1-8])\s*[x×]\s*(\d{1,3})\s*GB',
                amount,
                re.I,
            )

            if kit:
                gb = int(kit[1]) * int(kit[2])
            else:
                gb = int(
                    re.search(r'\d{1,3}', amount).group()
                )

            if not 4 <= gb <= 256:
                continue

            # Nie traktuj pamięci GPU jako RAM.

            start = match.start('size')

            last_sep = max(
                (
                    text.rfind(c, 0, start)
                    for c in '\n;|,'
                ),
                default=-1,
            )

            prefix = text[last_sep + 1:start]

            gpu_matches = list(re.finditer(
                r'\b(?:RTX|GTX|Radeon|VRAM|'
                r'GDDR[456]\w*|RX\s*\d{4})\b',
                prefix,
                re.I,
            ))

            if gpu_matches and kind != 'ram_before':
                # Rozdzielamy VRAM GPU od RAM komputera.
                suffix = prefix[gpu_matches[-1].end():]

                previous_capacity = re.search(
                    r'\b\d{1,3}\s*GB\b',
                    suffix,
                    re.I,
                )

                if not previous_capacity:
                    continue

            near = text[
                max(0, match.start() - 15):
                match.end() + 15
            ]

            if kind == 'kit' and re.search(
                r'\b(?:VRAM|GDDR\w*)\b',
                near,
                re.I,
            ):
                continue

            return gb

    return None



def parse_disks(text):
    if not text:
        return []

    disks = []

    # 512GB SSD / 1TB HDD / 1 TB NVMe
    pattern1 = re.compile(
        r'(\d+(?:[.,]\d+)?)\s*(TB|GB)\s*(SSD|HDD|NVME|M\.2)',
        re.I
    )

    for size, unit, kind in pattern1.findall(text):
        kind = kind.upper()


        value = f"{kind} {size.replace(',', '.')} {unit.upper()}"

        if value not in disks:
            disks.append(value)

    # SSD 512GB / HDD 1TB
    pattern2 = re.compile(
        r'\b(SSD|HDD|NVME|M\.2)\s*(\d+(?:[.,]\d+)?)\s*(TB|GB)',
        re.I
    )

    for kind, size, unit in pattern2.findall(text):
        kind = kind.upper()


        value = f"{kind} {size.replace(',', '.')} {unit.upper()}"

        if value not in disks:
            disks.append(value)

    return disks


def parse_line_value(text, labels):
    # FLEXIBLE_SPEC_LINES_V1
    if not text:
        return None

    for line in text.splitlines():
        for label in labels:
            match = re.match(
                rf"^\s*(?:[-*•▪–—]\s*)?(?:{label})"
                rf"(?:\s*[:：\-–—]\s*|\s+)(.+?)\s*$",
                line,
                re.I,
            )
            if match:
                value = match.group(1).strip()
                if value:
                    return value

    return None


def parse_pc_specs(title=None, description=None):

    title = title or ""
    description = description or ""

    combined = (
        title
        + "\n"
        + description
    )

    return {
        "cpu": parse_cpu(combined),
        "gpu": parse_gpu(combined),
        "ram": parse_ram(combined),
        "disks": parse_disks(combined),

        "motherboard": parse_line_value(
            description,
            [
                r'Płyta główna',
                r'Plyta glowna',
            ]
        ),

        "psu": parse_line_value(
            description,
            [
                r'Zasilacz',
                r'PSU',
            ]
        ),
    }
