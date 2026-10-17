import json
import sqlite3
from datetime import date, timedelta

import pytest

from app import db


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Isolated cwd with an empty data/ dir so relative paths resolve there."""
    (tmp_path / "data").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


def write_weights_file(workspace, rows):
    workspace.joinpath("data", "123_weights.json").write_text(
        json.dumps(rows), encoding="utf-8"
    )


def read_rows(workspace):
    conn = sqlite3.connect(workspace / "data" / "app.db")
    try:
        return sorted(conn.execute("SELECT date, weight FROM weights"))
    finally:
        conn.close()


def test_migrate_from_json_creates_rows(workspace):
    write_weights_file(
        workspace,
        [
            {"weight": 70.0, "date": "10-01-2025"},
            {"weight": 71.2, "date": "11-01-2025"},
        ],
    )

    db.init_db()
    db.migrate_from_json()

    assert read_rows(workspace) == [
        ("2025-01-10", 70.0),
        ("2025-01-11", 71.2),
    ]


def test_migrate_is_idempotent(workspace):
    write_weights_file(workspace, [{"weight": 70.0, "date": "10-01-2025"}])

    db.init_db()
    db.migrate_from_json()
    db.migrate_from_json()

    assert read_rows(workspace) == [("2025-01-10", 70.0)]


def test_migrate_without_file_is_silent(workspace):
    db.init_db()

    assert db.migrate_from_json() == 0


def test_migrate_reads_utf8_bom_file(workspace):
    workspace.joinpath("data", "777_weights.json").write_text(
        json.dumps([{"weight": 68.1, "date": "05-03-2025"}]),
        encoding="utf-8-sig",
    )

    db.init_db()

    assert db.migrate_from_json() == 1
    assert read_rows(workspace) == [("2025-03-05", 68.1)]


def test_upsert_overwrites_same_date(workspace):
    db.init_db()
    db.upsert_weight("2025-01-10", 70.0)
    db.upsert_weight("2025-01-10", 71.5)

    assert read_rows(workspace) == [("2025-01-10", 71.5)]


def test_migrate_keeps_existing_rows_untouched(workspace):
    """A row already in the DB (e.g. written by the bot while another
    container already migrated) must never be clobbered by the migration."""
    write_weights_file(workspace, [{"weight": 60.0, "date": "10-01-2025"}])
    db.init_db()
    db.upsert_weight("2025-01-10", 70.0)

    added = db.migrate_from_json()

    assert added == 0
    assert read_rows(workspace) == [("2025-01-10", 70.0)]


def test_get_weights_period_filter(workspace):
    today = date.today()
    db.init_db()
    for offset, weight in [(0, 70.0), (10, 72.0), (100, 80.0)]:
        db.upsert_weight((today - timedelta(days=offset)).isoformat(), weight)

    month = db.get_weights("month")

    assert [(r["date"], r["weight"]) for r in month] == [
        ((today - timedelta(days=10)).isoformat(), 72.0),
        (today.isoformat(), 70.0),
    ]


def test_get_weights_all_returns_sorted(workspace):
    db.init_db()
    db.upsert_weight("2025-02-01", 71.0)
    db.upsert_weight("2025-01-01", 70.0)

    rows = db.get_weights("all")

    assert [(r["date"], r["weight"]) for r in rows] == [
        ("2025-01-01", 70.0),
        ("2025-02-01", 71.0),
    ]


def test_update_weight_changes_row(workspace):
    db.init_db()
    db.upsert_weight("2025-01-10", 70.0)
    row = db.get_weights("all")[0]

    db.update_weight(row["id"], "2025-01-11", 70.3)

    assert read_rows(workspace) == [("2025-01-11", 70.3)]


def test_delete_weight_removes_row(workspace):
    db.init_db()
    db.upsert_weight("2025-01-10", 70.0)
    row = db.get_weights("all")[0]

    db.delete_weight(row["id"])

    assert read_rows(workspace) == []


def test_get_last_weight_returns_latest(workspace):
    db.init_db()
    db.upsert_weight("2025-01-10", 70.0)
    db.upsert_weight("2025-02-01", 71.0)

    last = db.get_last_weight()

    assert (last["date"], last["weight"]) == ("2025-02-01", 71.0)
