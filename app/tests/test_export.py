import json

import pytest

from app import db


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_export_weights_to_file(workspace):
    db.init_db()
    db.upsert_weight("2025-01-10", 70.0)
    db.upsert_weight("2025-02-01", 71.0)

    path = db.export_weights_to_file("data/weights.json")

    rows = json.loads(
        (workspace / "data" / "weights.json").read_text(encoding="utf-8")
    )
    assert rows == [
        {"date": "2025-01-10", "weight": 70.0},
        {"date": "2025-02-01", "weight": 71.0},
    ]
    assert path.endswith("weights.json")
