"""Conservative classification; never makes an automatic BUY decision."""
from dataclasses import asdict, dataclass
import re
from typing import Any

from .contracts import RawListing

CPU_INTEL = re.compile(r'(?<![A-Z0-9])(?:INTEL\s+)?(?:CORE\s+)?(I[3579])[-\s]+(\d{4,5}(?:KF|KS|HX|HS|HK|HQ|X3D|[A-Z])?)(?![A-Z0-9])')
CPU_RYZEN = re.compile(r'(?<![A-Z0-9])(?:AMD\s+)?(?:RYZEN\s+|R)([3579])[-\s]+(\d{4,5}(?:X3D|HX|HS|[A-Z])?)(?![A-Z0-9])')
GPU = re.compile(r'(?<![A-Z0-9])((?:RTX|GTX|RX)\s*[- ]?\s*\d{3,4}\s*(?:TI\s+SUPER|SUPER|TI|XTX|XT)?|ARC\s*[AB]\d{3})(?![A-Z0-9])')
RAM = [
    re.compile(r'\b(?:RAM|DDR[345])\s*[:\-]?\s*(\d{1,3})\s*GB\b'),
    re.compile(r'\b(\d{1,3})\s*GB\s*(?:RAM|DDR[345]|PAMIECI|PAMIĘCI)\b'),
    re.compile(r'\b(\d{1,2})\s*[X×]\s*(\d{1,2})\s*GB\s*(?:RAM|DDR[345])\b'),
]
LAPTOP = re.compile(r'\b(?:LAPTOP\w*|NOTEBOOK\w*|MACBOOK\w*|THINKPAD\w*|IDEAPAD\w*|PROBOOK\w*|ELITEBOOK\w*|VIVOBOOK\w*|ZENBOOK\w*|INSPIRON\w*|LATITUDE\w*|CHROMEBOOK\w*)\b')
DESKTOP = re.compile(r'\b(?:KOMPUTER\s+STACJONARNY|STACJONARKA|STACJONARNY|DESKTOP|PC\s+GAMING|KOMPUTER\s+GAMING|ZESTAW\s+KOMPUTEROWY|JEDNOSTKA\s+CENTRALNA)\b')
PHONE = re.compile(r'\b(?:IPHONE\w*|SMARTFON\w*|SMARTPHONE\w*|TELEFON\w*|GALAXY\s+[SAZ]\d{1,3}\w*|PIXEL\s+\d{1,2}\w*|REDMI\s+NOTE\s*\d+\w*|POCO\s+[FXM]\d+)\b')
GPU_PART = re.compile(r'\b(?:KARTA\s+GRAFICZNA|GPU|GRAFIKA|GEFORCE|RADEON)\b')
PART = re.compile(r'\b(?:PLYTA\s+GLOWNA|PŁYTA\s+GŁÓWNA|ZASILACZ|OBUDOWA|RAM\s+DDR|DYSK\s+(?:SSD|HDD))\b')
STORAGE = re.compile(r'\b(64|128|256|512|1024)\s*GB\b')


def _compact(value: str) -> str:
    return re.sub(r'\s+', ' ', value.strip().upper())


def _cpu(text: str):
    matches = []
    for match in CPU_INTEL.finditer(text):
        matches.append(match.group(1) + '-' + match.group(2))
    for match in CPU_RYZEN.finditer(text):
        matches.append('RYZEN ' + match.group(1) + ' ' + match.group(2))
    return sorted(set(matches))


def _gpus(text: str):
    return sorted(set(re.sub(r'\s+', ' ', v.group(1).strip()).replace(' -', ' ') for v in GPU.finditer(text)))


def _ram(text: str):
    for i, regex in enumerate(RAM):
        match = regex.search(text)
        if match:
            result = int(match.group(1))
            if i == 2:
                result *= int(match.group(2))
            if 2 <= result <= 256:
                return result
    return None


def _hint(hints: dict, key: str):
    value = hints.get(key)
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return str(value).strip()[:100]
    return ''


@dataclass(frozen=True)
class CategoryResult:
    category: str
    confidence: str
    attributes: dict[str, Any]
    missing: tuple[str, ...]
    comparable_key: str | None
    pc_pricing_input_complete: bool
    reason: str

    def to_dict(self):
        return asdict(self)


def categorize(listing: RawListing, hints: dict | None = None) -> CategoryResult:
    """Separate bundled listings and unknown categories; only verified PC specs pass gate."""
    hints = hints if isinstance(hints, dict) else {}
    title = _compact(str(listing.title or ''))
    description = _compact(str(listing.description or '')[:12000])
    text = f'{title} {description}'
    if not title:
        return CategoryResult('UNKNOWN', 'LOW', {}, ('title',), None, False, 'MISSING_TITLE')
    laptop = bool(LAPTOP.search(text))
    desktop = bool(DESKTOP.search(text))
    phone = bool(PHONE.search(text))
    cpus = _cpu(text)
    gpus = _gpus(text)
    cpu_hint = _cpu(_compact(_hint(hints, 'cpu')))
    gpu_hint = _gpus(_compact(_hint(hints, 'gpu')))
    if cpu_hint and not cpus:
        cpus = cpu_hint
    if gpu_hint and not gpus:
        gpus = gpu_hint
    ram = _ram(text)
    if ram is None:
        hinted = _hint(hints, 'ram_gb') or _hint(hints, 'ram')
        ram = _ram('RAM ' + hinted + 'GB' if hinted.isdecimal() else 'RAM ' + hinted)
    attrs: dict[str, Any] = {
        'cpu': cpus[0] if len(cpus) == 1 else None,
        'gpu': gpus[0] if len(gpus) == 1 else None,
        'ram_gb': ram,
    }
    if len(cpus) > 1 or len(gpus) > 1:
        return CategoryResult('AMBIGUOUS', 'LOW', attrs, ('single_product',), None, False, 'MULTIPLE_COMPONENT_MODELS')
    if sum((laptop, desktop, phone)) > 1:
        return CategoryResult('AMBIGUOUS', 'LOW', attrs, ('single_product',), None, False, 'MULTIPLE_PRODUCT_TYPES')
    if phone:
        storage = STORAGE.search(text)
        attrs = {'storage_gb': int(storage.group(1)) if storage else None}
        return CategoryResult('SMARTPHONE', 'HIGH', attrs, (), None, False, 'PHONE_IDENTIFIED')
    if laptop:
        return CategoryResult('LAPTOP', 'HIGH', attrs, (), None, False, 'LAPTOP_IDENTIFIED')
    if desktop or (len(cpus) == 1 and len(gpus) == 1 and ram is not None):
        missing = tuple(name for name, value in attrs.items() if value is None)
        ready = not missing and listing.currency == 'PLN' and listing.price_minor is not None and listing.price_minor > 0
        key = ('PC:' + attrs['cpu'] + ':' + attrs['gpu'] + ':' + str(ram) + 'GB') if not missing else None
        return CategoryResult('DESKTOP_PC', 'HIGH' if desktop else 'MEDIUM', attrs, missing, key, ready, 'DESKTOP_IDENTIFIED' if desktop else 'PC_COMPONENTS_IDENTIFIED')
    if len(gpus) == 1 and not cpus and not PART.search(text):
        return CategoryResult('GPU', 'HIGH' if GPU_PART.search(text) else 'MEDIUM', {'gpu': gpus[0]}, (), None, False, 'STANDALONE_GPU')
    if PART.search(text):
        return CategoryResult('COMPONENT', 'MEDIUM', attrs, (), None, False, 'COMPONENT_IDENTIFIED')
    return CategoryResult('UNKNOWN', 'LOW', attrs, ('category',), None, False, 'INSUFFICIENT_EVIDENCE')
