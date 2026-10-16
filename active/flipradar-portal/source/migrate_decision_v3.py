import sqlite3


DB = "/opt/olx-bot/decision_log.db"


NEW_COLUMNS = {
    "neighbor_samples": "INTEGER",
    "neighbor_exact_gpu_samples": "INTEGER",
    "neighbor_gpu_samples": "INTEGER",
    "neighbor_similarity": "REAL",
    "neighbor_p25": "INTEGER",
    "neighbor_median": "INTEGER",
    "neighbor_quick_raw": "INTEGER",
    "neighbor_quick_protected": "INTEGER",
    "neighbor_protected": "INTEGER DEFAULT 0",
}


conn = sqlite3.connect(DB)

columns = {
    row[1]
    for row in conn.execute(
        "PRAGMA table_info(decisions)"
    ).fetchall()
}

for name, definition in NEW_COLUMNS.items():

    if name not in columns:

        print(
            f"Dodaję kolumnę: {name}"
        )

        conn.execute(
            f"""
            ALTER TABLE decisions
            ADD COLUMN {name} {definition}
            """
        )


conn.commit()
conn.close()

print("Migracja decision_log V3 OK")
