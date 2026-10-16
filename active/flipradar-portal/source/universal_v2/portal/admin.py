import argparse
import json
import uuid

from flip_core.auth_store import AuthStore
from universal_v2.hunter.store import Store

from .store import PortalStore


def main():
    parser = argparse.ArgumentParser(
        description="Lokalne zarządzanie dostępem FlipRadar"
    )
    parser.add_argument("--database", required=True)
    parser.add_argument("--auth-db", required=True)
    parser.add_argument("--owner-id", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    activate = commands.add_parser("activate")
    activate.add_argument("--user-id", required=True)
    activate.add_argument(
        "--plan", choices=("START", "STANDARD", "PLUS"), required=True
    )
    disable = commands.add_parser("disable")
    disable.add_argument("--user-id", required=True)
    args = parser.parse_args()
    portal = PortalStore(Store(args.database), AuthStore(args.auth_db), args.owner_id)
    if args.command == "list":
        result = portal.admin_list(args.owner_id)
    else:
        result = portal.admin_access(
            args.owner_id,
            uuid.uuid4().hex,
            args.user_id,
            args.command,
            getattr(args, "plan", None),
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
