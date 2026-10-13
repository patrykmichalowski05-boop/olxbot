#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

export NVM_DIR="/root/.nvm"

if [ -s "$NVM_DIR/nvm.sh" ]; then
    . "$NVM_DIR/nvm.sh"
fi

node -v >/dev/null
npm -v >/dev/null

python3 scripts/check_https_api.py

if [ ! -x node_modules/.bin/expo ]; then
    echo "Brak Expo CLI. Wykonaj npm ci."
    exit 1
fi

echo "Uruchamiam Expo w trybie tunelowym."
echo "Aplikacja i API to oddzielne polaczenia."

exec ./node_modules/.bin/expo start --tunnel
