"""python -m universal_v2.hunter --config CONFIG {validate,scan,watch,status,dispatch}."""

from __future__ import annotations

import argparse
import json
import signal
import sqlite3
import sys
import threading

from .config import Config
from .notify import Telegram, dispatch
from .runner import Runner
from .sources import SourceRegistry
from .store import Store


def output(value):
    print(json.dumps(value, ensure_ascii=False, sort_keys=True), flush=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="FlipRadar: uniwersalny radar okazji")
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--env-file", help="Opcjonalny lokalny plik .env z konfiguracją Telegrama"
    )
    parser.add_argument(
        "--network",
        action="store_true",
        help="Zezwól na skonfigurowane adaptery HTML/przeglądarki",
    )
    parser.add_argument(
        "--deliver",
        action="store_true",
        help="Wysyłaj zakolejkowane alerty do skonfigurowanego Telegrama",
    )
    parser.add_argument(
        "--sync-config",
        action="store_true",
        help="Zastąp profile w bazie profilami z konfiguracji",
    )
    parser.add_argument(
        "command",
        choices=("validate", "scan", "watch", "status", "dispatch", "retry-failed"),
    )
    args = parser.parse_args(argv)
    sources = sender = None
    stop = threading.Event()
    try:
        config = Config.load(args.config)
        if args.env_file:
            from pathlib import Path

            from dotenv import load_dotenv

            env_path = Path(args.env_file).expanduser()
            if not env_path.is_file():
                raise ValueError("Nie znaleziono wskazanego pliku środowiska")
            load_dotenv(env_path, override=False)
        if args.command == "validate":
            output(
                {
                    "valid": True,
                    "platforms": [s.platform for s in config.sources],
                    "searches": len(config.searches),
                }
            )
            return 0
        store = Store(config.database)
        known = {s.id for s in store.searches(config.owner_id)}
        for search in config.searches:
            if search.id not in known or args.sync_config:
                store.save_search(search)
        if args.command == "retry-failed":
            output({"requeued": store.retry_failed(config.owner_id)})
            return 0
        if args.command == "status":
            output(
                {
                    "sources": store.health(config.owner_id),
                    "queue": store.queue_summary(config.owner_id),
                    "searches": [s.payload() for s in store.searches(config.owner_id)],
                }
            )
            return 0
        if args.command == "dispatch" and not args.deliver:
            parser.error("Wysyłka wymaga jawnego --deliver")
        sender = Telegram(config.telegram_token_env, config.telegram_chat_env)
        sources = SourceRegistry(config.sources, config.root)
        runner = Runner(store, sources)
        if args.command == "watch":
            signal.signal(signal.SIGTERM, lambda *_: stop.set())
            signal.signal(signal.SIGINT, lambda *_: stop.set())
        while not stop.is_set():
            successful = False
            if args.command != "dispatch":
                for search in store.searches(config.owner_id):
                    if stop.is_set():
                        break
                    if search.enabled:
                        result = runner.scan(search, network=args.network)
                        successful = successful or "OK" in result["sources"].values()
                        output(result)
            if args.deliver:
                output({"delivery": dispatch(store, config.owner_id, sender)})
            if args.command != "watch":
                return 0 if successful or args.command == "dispatch" else 1
            stop.wait(config.interval_seconds)
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError) as error:
        # Configuration errors are local; never print an HTTP request/credential.
        output({"error": "CONFIGURATION_ERROR", "message": str(error)[:250]})
        return 2
    except sqlite3.Error:
        output(
            {
                "error": "STORAGE_UNAVAILABLE",
                "message": "Baza skanera jest niedostępna. Sprawdź dysk i uprawnienia.",
            }
        )
        return 3
    finally:
        if sources:
            sources.close()
        if sender:
            sender.close()


if __name__ == "__main__":
    sys.exit(main())
