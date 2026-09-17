"""
JADWAL — Week 1 starter.

This is the entire agent loop, deliberately small, so you can see
every moving part. No frameworks. Fake calendar (a Python list) so
you're not fighting OAuth yet.

WHAT TO DO WITH THIS FILE:
1. Run it as-is. Type: "besok jam 3 sore ketemu vendor, 1 jam"
2. Read every line of `run_agent_loop`. That IS the agent.
3. Break it on purpose: type nonsense, ask it to book two overlapping
   events, ask about a date far in the future. See what happens.
4. Add a 4th tool yourself (e.g. `delete_event`). That's the real exercise.

SETUP:
  pip install anthropic --break-system-packages
  export ANTHROPIC_API_KEY=your_key_here
  python jadwal_week1.py
"""

import json
import anthropic
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
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

load_dotenv()
TZ = ZoneInfo("Asia/Jakarta")
client = anthropic.Anthropic()

# ---------------------------------------------------------------------
# THE "FAKE CALENDAR" — just a list in memory. This is your Week 1
# stand-in for the real Google Calendar API. Same shape as a real
# event, so swapping it out later is a small change, not a rewrite.
# ---------------------------------------------------------------------
fake_calendar = [
    {"title": "Team standup", "start": "2026-09-16T09:00:00+07:00", "end": "2026-09-16T09:30:00+07:00"},
]


# ---------------------------------------------------------------------
# TOOLS — plain Python functions. The model never runs these itself;
# it asks YOU to run them by name, with arguments. You run them and
# hand back the result. That round trip is the whole pattern.
# ---------------------------------------------------------------------

def list_events(start: str, end: str) -> list:
    """Return events between two ISO datetimes."""
    return [
        e for e in fake_calendar
        if e["start"] >= start and e["end"] <= end
    ]


def create_event(title: str, start: str, end: str) -> dict:
    """Add an event. Checks for overlap first — a real tool should
    never silently create a conflict."""
    for e in fake_calendar:
        if start < e["end"] and end > e["start"]:
            return {"error": f"Conflicts with existing event: {e['title']} ({e['start']}–{e['end']})"}
    event = {"title": title, "start": start, "end": end}
    fake_calendar.append(event)
    return {"success": True, "event": event}

def delete_event(title: str, start: str) -> dict:
    """Delete an event. Never fails silently — reports if nothing matched."""
    for e in fake_calendar:
        if e["title"] == title and e["start"] == start:
            fake_calendar.remove(e)
            return {"success": True, "deleted": e}
    return {"error": f"Event not found: {title} at {start}"}


# Tool schemas — this is what the model actually sees. Get these
# descriptions right; the model's behavior is only as good as this.
TOOLS = [
    {
        "name": "list_events",
        "description": "List calendar events between two ISO 8601 datetimes (with timezone offset).",
        "input_schema": {
            "type": "object",
            "properties": {
                "start": {"type": "string", "description": "ISO 8601 datetime, e.g. 2026-09-16T00:00:00+07:00"},
                "end": {"type": "string", "description": "ISO 8601 datetime, e.g. 2026-09-16T23:59:59+07:00"},
            },
            "required": ["start", "end"],
        },
    },
    {
        "name": "create_event",
        "description": "Create a calendar event. Only call this AFTER the user has confirmed the exact title, start, and end time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "start": {"type": "string", "description": "ISO 8601 datetime with +07:00 offset"},
                "end": {"type": "string", "description": "ISO 8601 datetime with +07:00 offset"},
            },
            "required": ["title", "start", "end"],
        },
    },
    {
        "name": "delete_event",
        "description": "Delete a calendar event. Only call this AFTER the user has confirmed the exact title and start time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "start": {"type": "string", "description": "ISO 8601 datetime with +07:00 offset"},
            },
            "required": ["title", "start"],
        },
    },
]

TOOL_FUNCTIONS = {
    "list_events": lambda args: list_events(**args),
    "create_event": lambda args: create_event(**args),
    "delete_event": lambda args: delete_event(**args),
}

SYSTEM_PROMPT = f"""You are a scheduling assistant. Today is {datetime.now(TZ).strftime('%A, %Y-%m-%d %H:%M')} in Asia/Jakarta (+07:00).

Rules:
- Always resolve relative dates ("besok", "next Friday") to an exact ISO datetime yourself before calling any tool.
- Before calling create_event or delete_event, state the exact event details back to the user in plain language and ask them to confirm.
- Only call create_event or delete_event after the user has explicitly confirmed in this conversation.
- All times are Asia/Jakarta (+07:00) unless the user says otherwise."""


# ---------------------------------------------------------------------
# THE LOOP — this is the part worth reading slowly.
# ---------------------------------------------------------------------
def run_agent_loop(messages: list) -> list:
    MAX_TURNS = 10
    turns = 0
    while True:
        turns += 1
        if turns > MAX_TURNS:
            print("Hit max turns — stopping to avoid an infinite loop.")
            return messages

        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Print any text the model wants to say to the user
        for block in response.content:
            if block.type == "text":
                print(f"\nAssistant: {block.text}")

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            # Model is done — no more tools to call, waiting on the user
            return messages

        # Model wants to call one or more tools. Run them, collect results.
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"  [tool call] {block.name}({json.dumps(block.input)})")
                try:
                    result = TOOL_FUNCTIONS[block.name](block.input)
                except Exception as e:
                    result = {"error": f"Tool failed: {type(e).__name__}: {e}"}
                print(f"  [tool result] {json.dumps(result)}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

        messages.append({"role": "user", "content": tool_results})
        # loop again — model sees the tool result and decides what's next


if __name__ == "__main__":
    conversation = []
    print("Jadwal Week 1 — type your scheduling request, or 'quit'.")
    while True:
        user_input = input("\nYou: ")
        if user_input.strip().lower() == "quit":
            break
        conversation.append({"role": "user", "content": user_input})
        conversation = run_agent_loop(conversation)
