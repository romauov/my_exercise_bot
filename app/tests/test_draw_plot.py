import pytest

from app import db
from app.draw_weight_plot import draw_plot

from datetime import date, timedelta


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_draw_plot_uses_db_and_draws_png(workspace):
    today = date.today()
    db.init_db()
    db.upsert_weight((today - timedelta(days=2)).isoformat(), 70.0)
    db.upsert_weight((today - timedelta(days=1)).isoformat(), 70.5)

    result = draw_plot(user_id=1)

    assert result is None
    assert (workspace / "data" / "plot.png").exists()


def test_draw_plot_empty_db_returns_message(workspace):
    db.init_db()

    result = draw_plot(user_id=1, period="all")

    assert isinstance(result, str) and result
