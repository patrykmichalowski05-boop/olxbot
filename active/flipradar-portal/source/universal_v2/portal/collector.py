"""Account-scoped collector; Telegram is restricted to the configured owner."""

import argparse
import json
import signal
import threading

from flip_core.auth_store import AuthStore
from universal_v2.hunter.config import Config
from universal_v2.hunter.notify import Telegram, dispatch
from universal_v2.hunter.runner import Runner
from universal_v2.hunter.sources import SourceRegistry
from universal_v2.hunter.store import Store

from .store import AccessDenied, PortalStore


def scan_accounts(portal, runner, network=False):
    results = []
    for search in portal.store.searches():
        if not search.enabled:
            continue
        try:
            account = portal.require_bot(search.owner_id)
        except AccessDenied:
            continue
        result = runner.scan(
            search,
            network=network,
            notifications_enabled=account["access"]["can_receive_notifications"],
        )
        results.append({"user_id": search.owner_id, **result})
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Kolektor profili wszystkich uprawnionych kont FlipRadar"
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--auth-db", required=True)
    parser.add_argument("--network", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--deliver-owner",
        action="store_true",
        help="Telegram wyłącznie dla właściciela konfiguracji",
    )
    parser.add_argument("--env-file")
    args = parser.parse_args()
    if args.env_file:
        from dotenv import load_dotenv

        load_dotenv(args.env_file, override=False)
    config = Config.load(args.config)
    store = Store(config.database)
    portal = PortalStore(store, AuthStore(args.auth_db), config.owner_id)
    account = portal.account(config.owner_id)
    if account["role"] != "OWNER":
        parser.error("owner_id konfiguracji musi wskazywać konto właściciela portalu")
    known = {s.id for s in store.searches(config.owner_id)}
    for search in config.searches:
        if search.id not in known:
            store.save_search(search)
    sources = SourceRegistry(config.sources, config.root)
    sender = Telegram(config.telegram_token_env, config.telegram_chat_env)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    try:
        runner = Runner(store, sources)
        while not stop.is_set():
            for result in scan_accounts(portal, runner, network=args.network):
                print(json.dumps(result, ensure_ascii=False), flush=True)
            if (
                args.deliver_owner
                and portal.account(config.owner_id)["access"][
                    "can_receive_notifications"
                ]
            ):
                print(
                    json.dumps(
                        {"owner_delivery": dispatch(store, config.owner_id, sender)}
                    ),
                    flush=True,
                )
            if args.once:
                break
            stop.wait(config.interval_seconds)
    finally:
        sources.close()
        sender.close()


if __name__ == "__main__":
    main()
