import glob
import json
import sqlite3
from datetime import date, datetime, timedelta

DB_PATH = "data/app.db"

PERIOD_DAYS = {
    "last": 14,
    "month": 30,
    "quarter": 90,
    "year": 365,
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS weights (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    date   TEXT NOT NULL,
    weight REAL NOT NULL,
    UNIQUE(date)
);
"""


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.executescript(SCHEMA)


def _row_to_dict(row):
    return {"id": row["id"], "date": row["date"], "weight": row["weight"]}


def migrate_from_json():
    """Import data/*.json weight files (dates DD-MM-YYYY) into the DB.

    Idempotent: existing dates are skipped. Returns the number of rows added.
    """
    files = glob.glob("data/*_weights.json")
    added = 0
    for path in files:
        with open(path, "r", encoding="utf-8-sig") as f:
            entries = json.load(f)
        for entry in entries:
            date_iso, weight = _parse_entry(entry)
            with _connect() as conn:
                exists = conn.execute(
                    "SELECT 1 FROM weights WHERE date = ?", (date_iso,)
                ).fetchone()
                if exists:
                    continue
                conn.execute(
                    "INSERT INTO weights(date, weight) VALUES (?, ?)",
                    (date_iso, weight),
                )
                added += 1
    return added


def _parse_entry(entry):
    raw_date = entry["date"]
    date_iso = normalize_date(raw_date)
    return date_iso, float(entry["weight"])


def normalize_date(raw_date):
    """Accept ISO (YYYY-MM-DD) or legacy DD-MM-YYYY dates, return ISO."""
    raw_date = raw_date.strip()
    if len(raw_date) == 10 and raw_date[:4].isdigit():
        return raw_date
    return datetime.strptime(raw_date, "%d-%m-%Y").date().isoformat()


def get_weights(period=None):
    where = ""
    params = ()
    if period in PERIOD_DAYS:
        cutoff = (date.today() - timedelta(days=PERIOD_DAYS[period])).isoformat()
        where = "WHERE date >= ?"
        params = (cutoff,)

    with _connect() as conn:
        rows = conn.execute(
            f"SELECT id, date, weight FROM weights {where} ORDER BY date", params
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def upsert_weight(date_iso, weight):
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO weights(date, weight) VALUES (?, ?)
            ON CONFLICT(date) DO UPDATE SET weight = excluded.weight
            """,
            (date_iso, weight),
        )


def update_weight(weight_id, date_iso, weight):
    with _connect() as conn:
        conn.execute(
            "UPDATE weights SET date = ?, weight = ? WHERE id = ?",
            (date_iso, weight, weight_id),
        )


def delete_weight(weight_id):
    with _connect() as conn:
        conn.execute("DELETE FROM weights WHERE id = ?", (weight_id,))


def get_last_weight():
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, date, weight FROM weights ORDER BY date DESC LIMIT 1"
        ).fetchone()
    return _row_to_dict(row) if row else None


def export_weights_json():
    with _connect() as conn:
        rows = conn.execute(
            "SELECT date, weight FROM weights ORDER BY date"
        ).fetchall()
    return [{"date": row["date"], "weight": row["weight"]} for row in rows]


def export_weights_to_file(path):
    """Dump all weighings as JSON to `path`; returns the same path."""
    data = export_weights_json()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    return path
