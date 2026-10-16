import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from pathlib import Path

from flip_core.auth_store import AuthStore

ROOT = Path("/root/olx-mobile-api-dev")
ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)

AUTH_DB = ROOT / "auth.db"
CREDS = ROOT / "credentials.json"
DATA_ROOT = Path("/opt/olx-bot")

for name in ("alert_history.db", "offer_snapshots.db"):
    if not (DATA_ROOT / name).is_file():
        raise SystemExit("STOP: Nie znaleziono " + name)

if AUTH_DB.exists() != CREDS.exists():
    raise SystemExit(
        "STOP: Niespojny stan konta testowego"
    )

if not AUTH_DB.exists():
    password = secrets.token_urlsafe(32)

    store = AuthStore(AUTH_DB)
    store.init_db()
    store.create_owner("mobiledev", password)

    os.chmod(AUTH_DB, 0o600)

    with CREDS.open("x", encoding="utf-8") as f:
        json.dump({
            "username": "mobiledev",
            "password": password,
        }, f)

    os.chmod(CREDS, 0o600)

credentials = json.loads(
    CREDS.read_text(encoding="utf-8")
)

with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]

base = f"http://127.0.0.1:{port}"

env = os.environ.copy()
env.update({
    "FLIP_API_AUTH_DB": str(AUTH_DB),
    "FLIP_API_DATA_ROOT": str(DATA_ROOT),
    "PYTHONPATH":
        "/root/flip-git-worktree-JmkMpF",
})

def request(path, payload=None, token=None):
    headers = {"Content-Type": "application/json"}

    if token:
        headers["Authorization"] = "Bearer " + token

    req = urllib.request.Request(
        base + path,
        data=(
            json.dumps(payload).encode("utf-8")
            if payload is not None
            else None
        ),
        headers=headers,
        method="POST" if payload is not None else "GET",
    )

    try:
        with urllib.request.urlopen(
            req, timeout=15
        ) as response:
            return (
                response.status,
                json.loads(response.read()),
            )
    except urllib.error.HTTPError as exc:
        return (
            exc.code,
            json.loads(exc.read()),
        )


with (ROOT / "smoke.log").open(
    "a", encoding="utf-8"
) as logfile:
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m", "uvicorn",
            "flip_core.mobile_api:create_app",
            "--factory",
            "--host", "127.0.0.1",
            "--port", str(port),
            "--no-access-log",
        ],
        env=env,
        stdout=logfile,
        stderr=subprocess.STDOUT,
    )

    try:
        for attempt in range(60):
            if proc.poll() is not None:
                raise RuntimeError(
                    "API zakonczono podczas startu"
                )

            try:
                status, _ = request("/api/v1/me")
                if status == 401:
                    break
            except (
                urllib.error.URLError,
                TimeoutError,
            ):
                pass

            time.sleep(0.15)
        else:
            raise RuntimeError("API nie odpowiada")

        print("OK: API nasluchuje na 127.0.0.1")
        print("OK: Brak tokenu -> HTTP 401")

        status, data = request(
            "/api/v1/auth/login",
            credentials,
        )

        if status != 200:
            raise RuntimeError(
                f"Logowanie HTTP {status}: {data}"
            )

        token = data["access_token"]
        print("OK: Logowanie HTTP 200")

        for path in (
            "/api/v1/radar?limit=3",
            "/api/v1/listings?limit=3",
        ):
            status, result = request(
                path, token=token
            )

            if status != 200:
                raise RuntimeError(
                    f"{path}: HTTP {status}: {result}"
                )

            print(
                "OK:", path,
                "ofert:", len(result["items"])
            )

        print("API_SMOKE: OK")
        print("DANE PRODUKCYJNE: TYLKO ODCZYT")

    finally:
        proc.terminate()

        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

print("SERWER TESTOWY: ZATRZYMANY")
