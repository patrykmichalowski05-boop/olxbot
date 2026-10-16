import re

from dataclasses import dataclass
from .model import Listing, PriceKind


@dataclass(frozen=True)
class Identity:
    category: str
    model: str
    variant: str
    key: str | None
    warnings: tuple = ()


def classify_electronics(row: Listing):
    text = (
        row.title + ' ' + row.description
    ).upper()

    title = row.title.upper()
    warnings = []

    if re.search(
        r'PUSTE?\s+PUDEŁKO|'
        r'SAMO?\s+PUDEŁKO|'
        r'SAM\s+KARTON|'
        r'BOX ONLY',
        text,
    ):
        warnings.append('BOX_ONLY')

    if re.search(
        r'USZKODZON|NIE DZIAŁA|ICLOUD|NA CZĘŚCI',
        text,
    ):
        warnings.append('DAMAGED_OR_LOCKED')

    if row.price_kind != PriceKind.FULL:
        warnings.append('NOT_FULL_PRICE')

    if row.quantity != 1:
        warnings.append('MULTIPLE_UNITS')

    phone = re.search(
        r'\b('
        r'IPHONE\s*(?:1[1-7]|SE)\s*'
        r'(?:PRO MAX|PRO|PLUS|MINI)?'
        r'|SAMSUNG\s+GALAXY\s+[SAZ]\d{1,3}\s*'
        r'(?:ULTRA|PLUS|FE)?'
        r')\b',
        title,
    )

    if phone:
        mem = re.findall(
            r'\b(64|128|256|512|1024)\s*GB\b',
            title,
        )

        unique = set(mem)

        if len(unique) != 1:
            warnings.append(
                'MISSING_OR_AMBIGUOUS_STORAGE'
            )

        model = ' '.join(
            phone.group(1).split()
        )

        size = (
            next(iter(unique))
            if len(unique) == 1
            else '?'
        )

        key = (
            f'PHONE:{model}:{size}GB'
            if not warnings
            else None
        )

        return Identity(
            'SMARTPHONE',
            model,
            size + 'GB',
            key,
            tuple(warnings),
        )

    gpu = re.search(
        r'\b(RTX|GTX|RX)\s*-?\s*'
        r'(\d{3,4})\s*'
        r'(TI\s*SUPER|SUPER|TI|XTX|XT)?\b',
        title,
    )

    if gpu:
        name = ' '.join(
            x for x in gpu.groups() if x
        ).replace('  ', ' ')

        vrams = set(
            re.findall(
                r'\b(4|6|8|10|12|16|20|24|32)'
                r'\s*GB\s*(?:VRAM|GDDR\d+)?\b',
                text,
            )
        )

        if re.search(
            r'\bPC\s|\bKOMPUTER\b|'
            r'\bLAPTOP\b|\bNOTEBOOK\b',
            text,
        ):
            return Identity(
                'DESKTOP_OR_LAPTOP',
                name,
                '',
                None,
                ('NEEDS_FULL_PC_PARSER',),
            )

        if len(vrams) != 1:
            warnings.append(
                'MISSING_OR_CONFLICTING_VRAM'
            )

        cap = (
            next(iter(vrams))
            if len(vrams) == 1
            else '?'
        )

        form = (
            'MOBILE'
            if re.search(
                r'\bMOBILE GPU\b',
                text,
            )
            else 'DESKTOP'
        )

        key = (
            f'GPU:{name}:{cap}GB:{form}'
            if not warnings
            else None
        )

        return Identity(
            'GPU',
            name,
            cap + 'GB ' + form,
            key,
            tuple(warnings),
        )

    return Identity(
        'UNKNOWN',
        '',
        '',
        None,
        ('UNSUPPORTED_ELECTRONICS',),
    )
