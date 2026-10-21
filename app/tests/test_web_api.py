import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WEB_TOKEN", "secret-token")
    os.environ["WEB_TOKEN"] = "secret-token"
    yield tmp_path
    monkeypatch.delenv("WEB_TOKEN", raising=False)
    if os.environ.get("WEB_TOKEN") == "secret-token":
        del os.environ["WEB_TOKEN"]


@pytest.fixture
def client(workspace):
    from app import db
    from web.main import app

    db.init_db()
    return TestClient(app), "secret-token"


def h(token):
    return {"X-Auth-Token": token}


def test_api_requires_token(client):
    client, token = client

    assert client.get("/api/weights").status_code == 401
    assert client.get("/api/weights", headers=h("wrong")).status_code == 401


def test_check_endpoint(client):
    client, token = client

    assert client.get("/api/check", headers=h(token)).status_code == 200
    assert client.get("/api/check", headers=h("bad")).status_code == 401


def test_list_weights_empty(client):
    client, token = client

    r = client.get("/api/weights", headers=h(token))

    assert r.status_code == 200
    assert r.json() == []


def test_post_weight_upserts(client, workspace):
    client, token = client

    r = client.post(
        "/api/weights", headers=h(token), json={"date": "10-01-2025", "weight": 70.5}
    )

    assert r.status_code == 200
    rows = client.get("/api/weights", headers=h(token)).json()
    assert rows == [{"id": 1, "date": "2025-01-10", "weight": 70.5}]

    client.post("/api/weights", headers=h(token), json={"date": "2025-01-10", "weight": 71.0})
    rows = client.get("/api/weights", headers=h(token)).json()
    assert rows == [{"id": 1, "date": "2025-01-10", "weight": 71.0}]


def test_patch_weight(client, workspace):
    client, token = client
    db = pytest.importorskip("app.db")
    db.init_db()
    db.upsert_weight("2025-01-10", 70.0)
    weight_id = db.get_weights("all")[0]["id"]

    r = client.patch(f"/api/weights/{weight_id}", headers=h(token), json={"weight": 70.3})

    assert r.status_code == 200
    rows = client.get("/api/weights", headers=h(token)).json()
    assert rows == [{"id": weight_id, "date": "2025-01-10", "weight": 70.3}]


def test_patch_missing_weight_404(client, workspace):
    client, token = client

    r = client.patch("/api/weights/999", headers=h(token), json={"weight": 70.3})

    assert r.status_code == 404


def test_delete_weight(client, workspace):
    client, token = client
    db = pytest.importorskip("app.db")
    db.init_db()
    db.upsert_weight("2025-01-10", 70.0)
    weight_id = db.get_weights("all")[0]["id"]

    r = client.delete(f"/api/weights/{weight_id}", headers=h(token))

    assert r.status_code == 200
    assert client.get("/api/weights", headers=h(token)).json() == []


def test_summary_returns_last(client, workspace):
    client, token = client

    client.post("/api/weights", headers=h(token), json={"date": "2025-01-10", "weight": 70.5})
    client.post("/api/weights", headers=h(token), json={"date": "2025-01-11", "weight": 71.0})

    r = client.get("/api/summary", headers=h(token))

    assert r.status_code == 200
    assert r.json() == {"id": 2, "date": "2025-01-11", "weight": 71.0}


def test_summary_empty_is_null(client, workspace):
    client, token = client

    r = client.get("/api/summary", headers=h(token))

    assert r.json() is None


def test_static_files_revalidate_on_every_load(client, workspace):
    """Pages must revalidate cached CSS/JS, otherwise UI updates look stale."""
    client, token = client
    (workspace / "web").mkdir()  # empty static dir is enough for a request test
    r = client.get("/style.css")

    assert r.status_code in (200, 404)
    assert r.headers.get("cache-control") == "no-cache"


def test_get_goal_empty_is_null(client, workspace):
    client, token = client
    db = pytest.importorskip("app.db")
    db.init_db()

    assert (
        client.get("/api/goal", headers=h(token)).status_code,
        client.get("/api/goal", headers=h(token)).json(),
    ) == (200, None)


def test_put_and_get_goal(client, workspace):
    client, token = client
    db = pytest.importorskip("app.db")
    db.init_db()

    r = client.put("/api/goal", headers=h(token), json={"weight": 90.0})

    assert r.status_code == 200
    resp = client.get("/api/goal", headers=h(token))
    assert resp.json() == {"weight": 90.0}


def test_put_goal_overwrites(client, workspace):
    client, token = client
    db = pytest.importorskip("app.db")
    db.init_db()
    client.put("/api/goal", headers=h(token), json={"weight": 90.0})

    client.put("/api/goal", headers=h(token), json={"weight": 91.2})

    assert client.get("/api/goal", headers=h(token)).json() == {"weight": 91.2}


def test_goal_requires_token(client, workspace):
    client, token = client

    assert client.get("/api/goal").status_code == 401
    assert client.put("/api/goal", json={"weight": 90.0}).status_code == 401


def test_put_goal_invalid_body_returns_422(client, workspace):
    client, token = client

    r = client.put("/api/goal", headers=h(token), json={"weight": "abc"})

    assert r.status_code == 422


def test_export_weights_endpoint(client, workspace):
    client, token = client
    db = pytest.importorskip("app.db")
    db.init_db()
    db.upsert_weight("2025-01-10", 70.0)
    db.upsert_weight("2025-01-15", 70.5)

    r = client.get("/api/backup", headers=h(token))

    assert r.status_code == 200
    assert r.json() == [
        {"date": "2025-01-10", "weight": 70.0},
        {"date": "2025-01-15", "weight": 70.5},
    ]
    assert "attachment" in r.headers["content-disposition"]
    assert ".json" in r.headers["content-disposition"]


def test_patch_date_collision_returns_409(client, workspace):
    client, token = client
    db = pytest.importorskip("app.db")
    db.init_db()
    db.upsert_weight("2025-01-10", 70.0)
    db.upsert_weight("2025-01-11", 71.0)
    first_id = db.get_weights("all")[0]["id"]

    r = client.patch(
        f"/api/weights/{first_id}", headers=h(token), json={"date": "2025-01-11"}
    )

    assert r.status_code == 409


def test_patch_weight_collision_returns_409(client, workspace):
    client, token = client
    db = pytest.importorskip("app.db")
    db.init_db()
    db.upsert_weight("2025-01-10", 70.0)
    db.upsert_weight("2025-01-11", 71.0)
    rows = db.get_weights("all")

    r = client.patch(
        f"/api/weights/{rows[1]['id']}?x=1",
        headers=h(token),
        json={"date": "2025-01-10", "weight": 71.5},
    )

    assert r.status_code == 409


def test_post_missing_fields_returns_422(client, workspace):
    client, token = client

    assert client.post("/api/weights", headers=h(token), json={"date": "2025-01-10"}).status_code == 422
    assert client.post("/api/weights", headers=h(token), json={"weight": 70.0}).status_code == 422
    assert client.post("/api/weights", headers=h(token), json={"date": "2025-01-10", "weight": "abc"}).status_code == 422


def test_post_invalid_date_returns_422(client, workspace):
    client, token = client

    r = client.post(
        "/api/weights", headers=h(token), json={"date": "31-02-2025", "weight": 70.0}
    )

    assert r.status_code == 422


def test_patch_invalid_weight_returns_422(client, workspace):
    client, token = client
    db = pytest.importorskip("app.db")
    db.init_db()
    db.upsert_weight("2025-01-10", 70.0)
    weight_id = db.get_weights("all")[0]["id"]

    r = client.patch(
        f"/api/weights/{weight_id}", headers=h(token), json={"weight": "abc"}
    )

    assert r.status_code == 422
