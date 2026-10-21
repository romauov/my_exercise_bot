import json
import os
import sqlite3

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.db import (
    delete_weight,
    get_last_weight,
    get_weights,
    normalize_date,
    update_weight,
    upsert_weight,
    export_weights_json,
    init_db,
    migrate_from_json,
)

app = FastAPI(title="Weight control")


class WeightPayload(BaseModel):
    date: str
    weight: float


class WeightPatchPayload(BaseModel):
    date: str | None = None
    weight: float | None = None


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


@app.get("/api/backup")
def backup(x_auth_token: str | None = Header(default=None)):
    _authorized(x_auth_token)
    data = export_weights_json()
    return Response(
        content=json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="weights_backup.json"'
        },
    )


@app.post("/api/weights")
def add_weight(payload: WeightPayload, x_auth_token: str | None = Header(default=None)):
    _authorized(x_auth_token)
    try:
        date_iso = normalize_date(payload.date)
    except ValueError:
        raise HTTPException(status_code=422, detail="bad date")
    upsert_weight(date_iso, payload.weight)
    return {"ok": True, "date": date_iso}


@app.patch("/api/weights/{weight_id}")
def edit_weight(
    weight_id: int,
    payload: WeightPatchPayload,
    x_auth_token: str | None = Header(default=None),
):
    _authorized(x_auth_token)
    rows = get_weights("all")
    current = next((r for r in rows if r["id"] == weight_id), None)
    if current is None:
        raise HTTPException(status_code=404, detail="not found")
    if payload.date is None and payload.weight is None:
        raise HTTPException(status_code=422, detail="nothing to update")
    date_iso = normalize_date(payload.date) if payload.date is not None else current["date"]
    weight = payload.weight if payload.weight is not None else current["weight"]
    try:
        update_weight(weight_id, date_iso, weight)
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="another weighing already exists on that date",
        )
    except ValueError:
        raise HTTPException(status_code=422, detail="bad date")
    return {"ok": True}


@app.delete("/api/weights/{weight_id}")
def remove_weight(weight_id: int, x_auth_token: str | None = Header(default=None)):
    _authorized(x_auth_token)
    rows = get_weights("all")
    if not any(r["id"] == weight_id for r in rows):
        raise HTTPException(status_code=404, detail="not found")
    delete_weight(weight_id)
    return {"ok": True}


class NoCacheStaticFiles(StaticFiles):
    """Serve static assets with `Cache-Control: no-cache`.

    Browsers then revalidate ETags on every load: unchanged files answer
    304, updated ones answer 200 — UI changes are never stuck behind a
    heuristic cache.
    """

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", NoCacheStaticFiles(directory=static_dir, html=True), name="static")
