import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles

from app.db import (
    delete_weight,
    get_last_weight,
    get_weights,
    normalize_date,
    update_weight,
    upsert_weight,
    init_db,
    migrate_from_json,
)

app = FastAPI(title="Weight control")


def _authorized(x_auth_token: str | None) -> str:
    expected = os.environ.get("WEB_TOKEN", "")
    if not expected or x_auth_token != expected:
        raise HTTPException(status_code=401, detail="unauthorized")
    return expected


@app.on_event("startup")
def startup():
    init_db()
    migrate_from_json()


@app.get("/api/check")
def check(x_auth_token: str | None = Header(default=None)):
    _authorized(x_auth_token)
    return {"ok": True}


@app.get("/api/weights")
def list_weights(x_auth_token: str | None = Header(default=None), period: str | None = None):
    _authorized(x_auth_token)
    return get_weights(period)


@app.get("/api/summary")
def summary(x_auth_token: str | None = Header(default=None)):
    _authorized(x_auth_token)
    return get_last_weight()


@app.post("/api/weights")
def add_weight(payload: dict, x_auth_token: str | None = Header(default=None)):
    _authorized(x_auth_token)
    date_iso = normalize_date(str(payload["date"]))
    upsert_weight(date_iso, float(payload["weight"]))
    return {"ok": True, "date": date_iso}


@app.patch("/api/weights/{weight_id}")
def edit_weight(
    weight_id: int,
    payload: dict,
    x_auth_token: str | None = Header(default=None),
):
    _authorized(x_auth_token)
    rows = get_weights("all")
    current = next((r for r in rows if r["id"] == weight_id), None)
    if current is None:
        raise HTTPException(status_code=404, detail="not found")
    date_iso = normalize_date(str(payload["date"])) if "date" in payload else current["date"]
    weight = float(payload["weight"]) if "weight" in payload else current["weight"]
    update_weight(weight_id, date_iso, weight)
    return {"ok": True}


@app.delete("/api/weights/{weight_id}")
def remove_weight(weight_id: int, x_auth_token: str | None = Header(default=None)):
    _authorized(x_auth_token)
    rows = get_weights("all")
    if not any(r["id"] == weight_id for r in rows):
        raise HTTPException(status_code=404, detail="not found")
    delete_weight(weight_id)
    return {"ok": True}


static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
