"""Create the first local API account using the existing AuthStore contract."""

from __future__ import annotations

import argparse
import getpass
import sqlite3

from flip_core.auth_store import AuthStore


def main(argv=None):
    parser = argparse.ArgumentParser(description="Utwórz pierwsze konto FlipRadar")
    parser.add_argument("--auth-db", required=True)
    parser.add_argument("--username", required=True)
    args = parser.parse_args(argv)
    password = getpass.getpass("Hasło (minimum 12 znaków): ")
    confirmation = getpass.getpass("Powtórz hasło: ")
    if password != confirmation:
        parser.error("Hasła muszą być takie same")
    try:
        auth = AuthStore(args.auth_db)
        auth.init_db()
        owner = auth.create_owner(args.username, password)
    except (ValueError, OSError, sqlite3.Error):
        parser.error(
            "Nie udało się utworzyć konta. Sprawdź login, długość hasła, ścieżkę bazy i czy konto już istnieje."
        )
    print(f"owner_id: {owner}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
