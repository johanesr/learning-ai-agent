"""
JADWAL CALENDAR — Week 5, Step 5.9: real Google Calendar backend.

Same 4 functions, same return shapes as jadwal_week3.py's SQLite versions —
on purpose, so jadwal_mcp.py (or anything else calling these) doesn't need
to change at all, just which file it imports from. The kitchen changed;
nothing that calls the kitchen needs to know.

Still uses EventCreate from jadwal_week3.py for validation — the validation
layer and the storage layer have been independent since Week 2, and that
independence is exactly what makes this swap this clean.

Answering Step 5.9's "Ask me": Google's API does NOT prevent double-booking
on its own — it will happily create overlapping events if you let it. The
conflict check below is still necessary, same as it was for SQLite.
"""

import pickle
from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pydantic import BaseModel, field_validator


class EventCreate(BaseModel):
    title: str
    start: datetime
    end: datetime

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v):
        if not v.strip():
            raise ValueError("title cannot be empty")
        return v

    @field_validator("end")
    @classmethod
    def end_after_start(cls, v, info):
        if "start" in info.data and v <= info.data["start"]:
            raise ValueError("end must be after start")
        return v
        
with open("token.pickle", "rb") as f:
    creds: Credentials = pickle.load(f)

service = build("calendar", "v3", credentials=creds)


def list_events(start: str, end: str) -> list:
    """List calendar events between two ISO 8601 datetimes (with timezone offset)."""
    result = service.events().list(
        calendarId="primary",
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    return [
        {
            "title": e.get("summary", "(no title)"),
            "start": e["start"].get("dateTime", e["start"].get("date")),
            "end": e["end"].get("dateTime", e["end"].get("date")),
        }
        for e in result.get("items", [])
    ]


def create_event(title: str, start: str, end: str) -> dict:
    """Create a calendar event. Checks for overlap first — a real tool should
    never silently create a conflict."""
    event = EventCreate(title=title, start=start, end=end)  # raises if invalid

    # Google doesn't block double-booking on its own — same conflict check
    # as Week 3's SQL version, just querying the real calendar instead.
    existing = list_events(event.start.isoformat(), event.end.isoformat())
    for e in existing:
        if event.start.isoformat() < e["end"] and event.end.isoformat() > e["start"]:
            return {"error": f"Conflicts with existing event: {e['title']} ({e['start']}–{e['end']})"}

    body = {
        "summary": event.title,
        "start": {"dateTime": event.start.isoformat()},
        "end": {"dateTime": event.end.isoformat()},
    }
    created = service.events().insert(calendarId="primary", body=body).execute()
    return {
        "success": True,
        "event": {"title": created["summary"], "start": created["start"]["dateTime"], "end": created["end"]["dateTime"]},
    }


def delete_event(title: str, start: str) -> dict:
    """Delete a calendar event. Never fails silently — reports if nothing matched."""
    # Google identifies events by an internal ID, not title+start — so we
    # first have to find the matching event's ID before we can delete it.
    day_start = start[:10] + "T00:00:00" + start[19:]
    day_end = start[:10] + "T23:59:59" + start[19:]
    candidates = service.events().list(
        calendarId="primary", timeMin=day_start, timeMax=day_end, singleEvents=True,
    ).execute().get("items", [])

    for e in candidates:
        if e.get("summary") == title and e["start"].get("dateTime") == start:
            service.events().delete(calendarId="primary", eventId=e["id"]).execute()
            return {"success": True, "deleted": {"title": title, "start": start}}

    return {"error": f"Event not found: {title} at {start}"}


def find_free_slot(duration_minutes: int, after: str, before: str) -> list:
    """Find open windows of at least `duration_minutes` between `after` and `before`."""
    # Same gap-walking algorithm as Week 3 — unchanged. Only the data feeding
    # it is different: real calendar events instead of a SQLite query.
    from datetime import timedelta

    events = list_events(after, before)
    duration = timedelta(minutes=duration_minutes)
    cursor = datetime.fromisoformat(after)
    window_end = datetime.fromisoformat(before)
    free_slots = []

    for e in events:
        e_start = datetime.fromisoformat(e["start"])
        e_end = datetime.fromisoformat(e["end"])
        if e_start - cursor >= duration:
            free_slots.append({"start": cursor.isoformat(), "end": e_start.isoformat()})
        cursor = max(cursor, e_end)

    if window_end - cursor >= duration:
        free_slots.append({"start": cursor.isoformat(), "end": window_end.isoformat()})

    return free_slots
