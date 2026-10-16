#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

URL="${1:-}"

if [ -z "$URL" ]; then
    echo "Uzycie:"
    echo "bash scripts/set_api_url.sh https://api.twojadomena.pl"
    exit 1
fi

# Najpierw test realnego HTTPS.
python3 scripts/check_https_api.py --url "$URL"

if [ -e .env ]; then
    cp -p .env ".env.backup.$(date +%s)"
fi

umask 077

printf 'EXPO_PUBLIC_FLIP_API_URL=%s\n' \
    "${URL%/}" > .env

chmod 600 .env

echo "OK: zapisano mobile/.env"
echo "Nie zapisano tokenow ani hasel."
