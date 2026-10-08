import sqlite3
from pathlib import Path


def connect(path, *, readonly=False):
    path = Path(path)

    if readonly:
        if not path.exists():
            return None
        conn = sqlite3.connect(
            f"file:{path}?mode=ro",
            uri=True,
            timeout=5,
        )
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, timeout=5)

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def query(path, sql, params=()):
    conn = None
    try:
        conn = connect(path, readonly=True)
        if conn is None:
            return []
        return conn.execute(sql, params).fetchall()
    except sqlite3.Error:
        return []
    finally:
        if conn is not None:
            conn.close()


def one(path, sql, params=()):
    rows = query(path, sql, params)
    return rows[0] if rows else None


def scalar(path, sql, params=(), default=0):
    row = one(path, sql, params)
    if row is None:
        return default
    try:
        return row[0]
    except (IndexError, KeyError, TypeError):
        return default


def execute(path, sql, params=()):
    conn = connect(path, readonly=False)
    try:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def table_exists(path, table):
    row = one(
        path,
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return row is not None


def columns(path, table):
    # table pochodzi wyłącznie ze stałych aplikacji, nie z requestu.
    rows = query(path, f"PRAGMA table_info({table})")
    return {row["name"] for row in rows}
