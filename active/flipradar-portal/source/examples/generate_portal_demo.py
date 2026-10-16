"""Bind synthetic offers to an existing owner; never generates credentials."""

import argparse
import json
from pathlib import Path

from examples.generate_hunter_demo import generate
from flip_core.auth_store import AuthStore
from universal_v2.hunter.config import Config
from universal_v2.hunter.runner import Runner
from universal_v2.hunter.sources import SourceRegistry
from universal_v2.hunter.store import Store
from universal_v2.portal.store import PortalStore


def create_demo(root, auth_path, username):
    auth = AuthStore(auth_path)
    with auth.transaction() as db:
        owner = db.execute(
            "SELECT id FROM users WHERE username=?", (username,)
        ).fetchone()
    if not owner:
        raise ValueError("Najpierw utwórz konto właściciela przez bootstrap")
    config_path = generate(Path(root))
    raw = json.loads(config_path.read_text())
    raw["owner_id"] = owner["id"]
    config_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n")
    config = Config.load(config_path)
    store = Store(config.database)
    PortalStore(store, auth, owner["id"])
    sources = SourceRegistry(config.sources, config.root)
    try:
        runner = Runner(store, sources)
        for profile in config.searches:
            store.save_search(profile)
            runner.scan(profile)
    finally:
        sources.close()
    return {
        "config": str(config_path.resolve()),
        "FLIP_HUNTER_DB": str(config.database),
        "FLIP_PORTAL_OWNER_ID": owner["id"],
        "FLIP_PORTAL_PUBLIC_SEARCH_OWNER_ID": owner["id"],
        "FLIP_PORTAL_PUBLIC_DATA_IS_DEMO": "1",
        "FLIP_PORTAL_ENABLED": "1",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Syntetyczna baza do sprawdzenia portalu bez sieci"
    )
    parser.add_argument("--output", default="runtime/portal-demo")
    parser.add_argument("--auth-db", required=True)
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            create_demo(args.output, args.auth_db, args.username),
            ensure_ascii=False,
            indent=2,
        )
    )
