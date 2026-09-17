"""
JADWAL API — Week 4 bridge.

n8n's SQLite node isn't a bundled/tool-compatible node, so instead of n8n
touching jadwal.db directly, this tiny FastAPI wrapper exposes your existing
Week 3 functions over HTTP. n8n calls these endpoints via its HTTP Request
Tool node — the same pattern real n8n setups use for custom business logic.

Nothing new is being taught here algorithmically — list_events, create_event,
delete_event, find_free_slot are imported UNCHANGED from jadwal_week3.py. This
file only adds an HTTP layer in front of them.

HTTP verbs follow normal REST convention:
  GET    — read-only, no side effects. Params go in the URL query string,
           never a body (many HTTP clients strip/ignore a GET body).
  POST   — creates something. Params go in a JSON body.
  DELETE — removes something. Params go in the URL query string, same as GET.

RUN:
  uv run uvicorn jadwal_api:app --reload --port 8000

Then test it's alive:
  curl http://localhost:8000/health
  curl "http://localhost:8000/list_events?start=2026-09-01T00:00:00+07:00&end=2026-12-31T23:59:59+07:00"
"""

from fastapi import FastAPI
from pydantic import BaseModel

from jadwal_week3 import list_events, create_event, delete_event, find_free_slot

app = FastAPI(title="Jadwal API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/list_events")
def api_list_events(start: str, end: str):
    return list_events(start, end)


@app.get("/find_free_slot")
def api_find_free_slot(duration_minutes: int, after: str, before: str):
    return find_free_slot(duration_minutes, after, before)


class CreateEventRequest(BaseModel):
    title: str
    start: str
    end: str


@app.post("/create_event")
def api_create_event(body: CreateEventRequest):
    return create_event(body.title, body.start, body.end)


@app.delete("/delete_event")
def api_delete_event(title: str, start: str):
    return delete_event(title, start)
