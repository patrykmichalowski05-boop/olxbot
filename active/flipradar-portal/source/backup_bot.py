import json
import os
import shutil
import sqlite3
import subprocess
import tarfile

from datetime import datetime
from pathlib import Path


PROJECT = Path("/opt/olx-bot")
BACKUP_ROOT = Path("/opt/olx-backups")
SYSTEMD_DIR = Path("/etc/systemd/system")

RETENTION = 14


def backup_sqlite(
    source,
    destination,
):
    print(
        "[BACKUP][DB]",
        source.name,
    )

    src = sqlite3.connect(
        f"file:{source}?mode=ro",
        uri=True,
        timeout=30,
    )

    dst = sqlite3.connect(
        destination
    )

    try:
        src.backup(
            dst
        )

    finally:
        dst.close()
        src.close()


def copy_optional(
    source,
    destination,
):
    if not source.exists():
        return False

    if source.is_dir():

        shutil.copytree(
            source,
            destination,
            dirs_exist_ok=True,
        )

    else:

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source,
            destination,
        )

    return True


def main():
    stamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    BACKUP_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    os.chmod(
        BACKUP_ROOT,
        0o700,
    )

    work = (
        BACKUP_ROOT
        /
        f".tmp_{stamp}"
    )

    if work.exists():
        shutil.rmtree(
            work
        )

    work.mkdir(
        mode=0o700,
        parents=True,
    )

    db_dir = work / "databases"
    code_dir = work / "code"
    systemd_dir = work / "systemd"

    db_dir.mkdir()
    code_dir.mkdir()
    systemd_dir.mkdir()

    backed_databases = []

    # ==========================================
    # SQLITE
    # ==========================================

    for db in sorted(
        PROJECT.glob("*.db")
    ):
        destination = (
            db_dir
            /
            db.name
        )

        backup_sqlite(
            db,
            destination,
        )

        backed_databases.append(
            db.name
        )


    # ==========================================
    # KOD PYTHON
    # ==========================================

    backed_code = []

    for source in sorted(
        PROJECT.glob("*.py")
    ):

        shutil.copy2(
            source,
            code_dir / source.name,
        )

        backed_code.append(
            source.name
        )


    # ==========================================
    # WAŻNE PLIKI PROJEKTU
    # ==========================================

    important = [
        ".env",
        "check.sh",
        "requirements.txt",
        "pyproject.toml",
    ]

    for name in important:

        source = PROJECT / name

        if source.exists():

            copy_optional(
                source,
                code_dir / name,
            )


    # ==========================================
    # TESTY
    # ==========================================

    tests = PROJECT / "tests"

    if tests.exists():

        copy_optional(
            tests,
            code_dir / "tests",
        )


    # ==========================================
    # SYSTEMD
    # ==========================================

    backed_units = []

    for unit in sorted(
        SYSTEMD_DIR.glob("olx-*")
    ):

        if not unit.is_file():
            continue

        shutil.copy2(
            unit,
            systemd_dir / unit.name,
        )

        backed_units.append(
            unit.name
        )


    # ==========================================
    # PIP FREEZE
    # ==========================================

    try:

        result = subprocess.run(
            [
                "/opt/olx-bot/venv/bin/python",
                "-m",
                "pip",
                "freeze",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        (
            work
            /
            "pip-freeze.txt"
        ).write_text(
            result.stdout,
            encoding="utf-8",
        )

    except Exception as e:

        print(
            "[BACKUP][WARN] pip freeze:",
            e,
        )


    # ==========================================
    # MANIFEST
    # ==========================================

    manifest = {
        "created_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "project":
            str(PROJECT),

        "databases":
            backed_databases,

        "python_files":
            backed_code,

        "systemd_units":
            backed_units,
    }

    (
        work
        /
        "manifest.json"
    ).write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


    # ==========================================
    # ARCHIWUM
    # ==========================================

    archive = (
        BACKUP_ROOT
        /
        f"olx-bot_{stamp}.tar.gz"
    )

    with tarfile.open(
        archive,
        "w:gz",
    ) as tar:

        for child in work.iterdir():

            tar.add(
                child,
                arcname=child.name,
            )


    shutil.rmtree(
        work
    )

    os.chmod(
        archive,
        0o600,
    )


    # ==========================================
    # RETENCJA
    # ==========================================

    archives = sorted(
        BACKUP_ROOT.glob(
            "olx-bot_*.tar.gz"
        ),
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )

    removed = 0

    for old in archives[
        RETENTION:
    ]:

        print(
            "[BACKUP] usuwam starą kopię:",
            old.name,
        )

        old.unlink()

        removed += 1


    # ==========================================
    # WERYFIKACJA ARCHIWUM
    # ==========================================

    with tarfile.open(
        archive,
        "r:gz",
    ) as tar:

        members = (
            tar.getmembers()
        )

        if not members:
            raise RuntimeError(
                "Archiwum backupu jest puste"
            )


    size_mb = (
        archive.stat().st_size
        /
        1024
        /
        1024
    )

    print()
    print(
        "=== BACKUP OK ==="
    )

    print(
        "Plik:",
        archive,
    )

    print(
        "Rozmiar:",
        f"{size_mb:.2f} MB",
    )

    print(
        "Bazy:",
        len(backed_databases),
    )

    print(
        "Python:",
        len(backed_code),
    )

    print(
        "Systemd:",
        len(backed_units),
    )

    print(
        "Usunięte stare:",
        removed,
    )


if __name__ == "__main__":
    main()
