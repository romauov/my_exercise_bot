import json

import pytest

from datetime import date


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("tg_token", raising=False)
    monkeypatch.delenv("my_tg_id", raising=False)

    # app.settings validates Telegram secrets on import; provide dummies.
    monkeypatch.setenv("tg_token", "test-token")
    monkeypatch.setenv("my_tg_id", "1")
    import importlib

    import app.utils as utils

    importlib.reload(utils)
    return tmp_path, utils


def test_save_weight_db_stores_iso_date_and_redraws(workspace):
    from app import db

    workspace, utils = workspace
    db.init_db()

    today_str = date.today().strftime("%d-%m-%Y")
    utils.save_weight_db(70.5, today_str)

    rows = db.get_weights("all")
    assert [(r["date"], r["weight"]) for r in rows] == [
        (date.today().isoformat(), 70.5)
    ]
    assert (workspace / "data" / "plot.png").exists()
