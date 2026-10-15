#!/usr/bin/env python3
"""Weryfikacja API HTTPS bez loginu i tokenu."""

import argparse
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

from pathlib import Path


def validate_url(raw):
    if not isinstance(raw, str):
        raise ValueError("Adres musi byc tekstem")

    raw = raw.strip()

    if not raw or any(x.isspace() for x in raw):
        raise ValueError("Brak lub niepoprawny URL")

    parsed = urllib.parse.urlsplit(raw)

    if parsed.scheme != "https":
        raise ValueError("Wymagany HTTPS")

    if not parsed.hostname:
        raise ValueError("Brak nazwy serwera")

    if parsed.username or parsed.password:
        raise ValueError("Dane logowania w URL zabronione")

    if parsed.query or parsed.fragment:
        raise ValueError("URL nie moze miec query/fragment")

    if parsed.path not in ("", "/"):
        raise ValueError(
            "Podaj glowny adres API bez sciezki"
        )

    if parsed.hostname.endswith(".invalid"):
        raise ValueError(
            "Adres przykladowy, a nie prawdziwe API"
        )

    try:
        parsed.port
    except ValueError as exc:
        raise ValueError(
            "Niepoprawny port URL"
        ) from exc

    return raw.rstrip("/")


def read_env(path):
    if not path.is_file():
        raise ValueError(
            "Brak mobile/.env - ustaw adres API"
        )

    values = []

    for line in path.read_text(
        encoding="utf-8"
    ).splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        key, sep, value = line.partition("=")

        if (
            sep and
            key.strip() == "EXPO_PUBLIC_FLIP_API_URL"
        ):
            values.append(
                value.strip().strip('"').strip("'")
            )

    if len(values) != 1:
        raise ValueError(
            "W .env wymagany jeden adres API"
        )

    return values[0]


def probe(base):
    base = validate_url(base)

    target = base + "/api/v1/me"

    request = urllib.request.Request(
        target,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )

    context = ssl.create_default_context()

    try:
        with urllib.request.urlopen(
            request,
            timeout=10,
            context=context,
        ) as response:
            raise RuntimeError(
                "API zwrocilo HTTP "
                + str(response.status)
                + " zamiast 401"
            )

    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            raise RuntimeError(
                "API zwrocilo HTTP "
                + str(exc.code)
                + " zamiast 401"
            ) from None

        if exc.geturl() != target:
            raise RuntimeError(
                "Nieoczekiwane przekierowanie"
            )

        content_type = (
            exc.headers.get("Content-Type", "")
        ).lower()

        if "application/json" not in content_type:
            raise RuntimeError(
                "Niepoprawny Content-Type"
            )

        try:
            body = json.loads(
                exc.read(4096)
            )
        except (ValueError, UnicodeError) as error:
            raise RuntimeError(
                "Niepoprawny JSON API"
            ) from error

        if body.get("detail") != "Unauthorized":
            raise RuntimeError(
                "Nieoczekiwana odpowiedz API"
            )

    print("OK: HTTPS i certyfikat TLS")
    print("OK: Endpoint /api/v1/me")
    print("OK: Brak autoryzacji -> HTTP 401")
    print("API_HTTPS: OK")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url")
    args = parser.parse_args()

    try:
        url = (
            args.url
            if args.url is not None
            else read_env(Path(".env"))
        )

        probe(url)
    except Exception as exc:
        print(
            "API_HTTPS: BLOKADA -",
            str(exc),
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
