import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WEB_TOKEN", "secret-token")
    os = __import__("os")
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


def test_log_request_stamps_row(workspace):
    from app import db

    db.init_db()
    db.log_request("1.2.3.4", "/api/weights", 200, mine=True)

    rows = db.get_request_log()

    assert len(rows) == 1
    row = rows[0]
    assert row["ip"] == "1.2.3.4"
    assert row["path"] == "/api/weights"
    assert row["status"] == 200
    assert row["mine"] == 1
    assert len(row["ts"]) >= len("2026-10-25T12:00:00")


def test_stats_exclude_mine_by_default(workspace):
    from app import db

    db.init_db()
    db.log_request("5.6.7.8", "/", 200, mine=False)
    db.log_request("testclient", "/", 200, mine=True)

    outside = db.get_request_stats()

    assert outside["total"] == 1
    assert outside["per_ip"][0]["ip"] == "5.6.7.8"

    everything = db.get_request_stats(include_mine=True)

    assert everything["total"] == 2
    assert everything["per_day"][0]["count"] == 2
    assert {"path": "/", "count": 2} in everything["per_path"]


def test_stats_grouped_by_day_path_ip(workspace):
    from app import db

    db.init_db()
    db.log_request("8.8.8.8", "/api/check", 401, mine=False)
    db.log_request("8.8.8.8", "/api/check", 401, mine=False)

    stats = db.get_request_stats()

    assert stats["total"] == 2
    assert stats["per_ip"] == [{"ip": "8.8.8.8", "count": 2}]
    assert stats["per_path"] == [{"path": "/api/check", "count": 2}]
    assert stats["per_day"][0]["count"] == 2


def test_stats_endpoints_require_token(client):
    client, token = client

    assert client.get("/api/stats").status_code == 401
    assert client.get("/api/stats/log").status_code == 401


def test_middleware_logs_requests_and_marks_mine(client):
    client, token = client

    client.get("/api/weights", headers=h(token))  # 200, valid token -> mine
    client.get("/api/weights")  # 401, no token -> outside

    outside = client.get("/api/stats", headers=h(token)).json()
    assert outside["total"] == 1  # own traffic hidden by default
    assert outside["per_path"] == [{"path": "/api/weights", "count": 1}]

    everything = client.get(
        "/api/stats", headers=h(token), params={"include_mine": 1}
    ).json()
    assert everything["total"] == 2  # both requests to /api/weights


def test_middleware_skips_stats_and_static_paths(client):
    client, token = client

    client.get("/stats", headers=h(token))  # the page itself
    client.get("/api/stats", headers=h(token))  # own polling
    client.get("/api/stats/log", headers=h(token))

    assert client.get("/api/stats/log", headers=h(token)).json() == []


def test_request_log_endpoint_returns_recent_rows(client):
    client, token = client

    client.get("/api/weights")  # outside request
    client.get("/api/goal")  # another outside request

    rows = client.get("/api/stats/log", headers=h(token)).json()

    assert [r["path"] for r in rows] == ["/api/goal", "/api/weights"]  # newest first
    assert all(r["mine"] == 0 for r in rows)
    assert all(r["status"] == 401 for r in rows)


def test_request_log_limit(client):
    client, token = client

    for _ in range(3):
        client.get("/api/summary")

    rows = client.get(
        "/api/stats/log", headers=h(token), params={"limit": 2}
    ).json()

    assert len(rows) == 2
    assert [r["path"] for r in rows] == ["/api/summary", "/api/summary"]
