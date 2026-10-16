"""Kontrola uprawnień do komercyjnego użycia źródeł danych.

Domyślnie wszystko jest zablokowane (fail closed).
Konfiguracja jest deklaracją administratora, nie dowodem
posiadania licencji ani gwarancją zgodności z prawem.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


class SourceDenied(PermissionError):
    pass


OPERATIONS = frozenset({
    "fetch",
    "store",
    "analyze",
    "redistribute",
})

CONFIG_PATH = Path(
    os.environ.get(
        "FLIP_SOURCE_POLICY",
        "/etc/flip-hunter/source-policy.json",
    )
)


def utc_now():
    return datetime.now(timezone.utc)


def load_policy(path=None):
    path = Path(path) if path else CONFIG_PATH

    if not path.is_file():
        raise SourceDenied(
            "Brak konfiguracji uprawnień: " + str(path)
        )

    if path.is_symlink():
        raise SourceDenied("Konfiguracja nie może być symlinkiem")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SourceDenied("Niepoprawna konfiguracja") from exc

    if not isinstance(data, dict):
        raise SourceDenied("Konfiguracja musi być obiektem JSON")

    return data


def check_source(source, operation, path=None, now=None):
    """Odmów dostępu, jeśli brak potwierdzonego zakresu praw."""

    if not isinstance(source, str) or not source.strip():
        raise SourceDenied("Brak identyfikatora źródła")

    if operation not in OPERATIONS:
        raise SourceDenied("Nieznana operacja")

    policy = load_policy(path)
    sources = policy.get("sources", {})

    if not isinstance(sources, dict):
        raise SourceDenied("Niepoprawna lista źródeł")

    entry = sources.get(source)

    if not isinstance(entry, dict):
        raise SourceDenied("Źródło niezarejestrowane")

    if entry.get("status") != "approved":
        raise SourceDenied("Źródło niezatwierdzone")

    if entry.get("commercial_use") is not True:
        raise SourceDenied("Brak zgody na użycie komercyjne")

    if entry.get("evidence_verified") is not True:
        raise SourceDenied("Niezweryfikowana dokumentacja")

    evidence = entry.get("evidence_reference")

    if not isinstance(evidence, str) or not evidence.strip():
        raise SourceDenied("Brak odniesienia do dokumentacji")

    allowed = entry.get("allowed_operations", [])

    if not isinstance(allowed, list) or operation not in allowed:
        raise SourceDenied(
            "Operacja niedozwolona dla źródła: " + operation
        )

    expiry = entry.get("expires_at")

    if not isinstance(expiry, str) or not expiry:
        raise SourceDenied("Brak daty ważności uprawnień")

    try:
        expires = datetime.fromisoformat(
            expiry.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise SourceDenied("Niepoprawna data ważności") from exc

    if expires.tzinfo is None:
        raise SourceDenied("Data musi zawierać strefę czasową")

    current = now or utc_now()

    if current.tzinfo is None or current >= expires:
        raise SourceDenied("Uprawnienia wygasły")

    return True


def validate_listing(record, policy_path=None):
    """Sprawdź uprawnienia i minimalne dane wejściowe."""

    if not isinstance(record, dict):
        raise ValueError("Ogłoszenie musi być obiektem")

    source = record.get("source")
    url = record.get("url")

    if not isinstance(url, str):
        raise ValueError("Brak adresu ogłoszenia")

    parsed = urlparse(url)

    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Wymagany poprawny adres HTTPS")

    if parsed.username or parsed.password:
        raise ValueError("Adres nie może zawierać danych logowania")

    check_source(source, "analyze", policy_path)

    return {
        "source": source,
        "url": url,
        "title": str(record.get("title") or "")[:500],
        "price": record.get("price"),
        "currency": record.get("currency", "PLN"),
        "specs": record.get("specs", {}),
    }
