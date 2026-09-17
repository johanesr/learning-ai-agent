# WEEK 2 — Structured Output & Trustworthiness

Builds on `jadwal_week2.py` (a copy of your finished `jadwal_week1.py`).
`jadwal_week1.py` stays untouched as your Week 1 checkpoint — don't edit it again.

**Goal by Sunday:** the agent (1) validates every tool argument before running it,
so bad data never reaches your fake calendar, (2) stops guessing dates it wasn't
given, and (3) can read a screenshot of an invite and extract the event from it.

**Recap of the rule:** don't search the internet for these — if a step doesn't
make sense, ask me. Each session has an **"Ask me"** list of the questions worth
bringing.

---

## Why this week, in one sentence

Right now the model can say anything, and your tools will happily *try* to run
it. This week you stop trusting the model's output and start **checking** it —
which is the actual difference between a demo and something safe to run daily.

---

## Session 1 — Tuesday evening (1.5h): Validate before you trust

### Step 2.1 — Install Pydantic (5 min)
```bash
cd "/Users/johanes/Documents/AI/Learning Agent"
uv add pydantic
```

### Step 2.2 — See the actual problem first (15 min)
Open `jadwal_week2.py` and look at [line ~118](jadwal_week2.py):
```python
TOOL_FUNCTIONS = {
    "list_events": lambda args: list_events(**args),
    "create_event": lambda args: create_event(**args),
    "delete_event": lambda args: delete_event(**args),
}
```
`args` here is *whatever the model said* — a plain dict, straight from the API,
with zero checking. The JSON schema in `TOOLS` is a hint to the model about what
shape to send, but **nothing on your side enforces it.** The model could send
`start: "tomorrow"` instead of an ISO datetime, or leave `title` empty, and
`create_event` would just... try to work with it.

Prove it to yourself — temporarily run this in a scratch Python shell:
```bash
uv run python3
>>> from jadwal_week2 import create_event
>>> create_event(title="", start="not a date", end="also not a date")
```
Watch what happens. It probably "succeeds" and appends garbage to
`fake_calendar`, because nothing checks the shape of the input. **That's the bug
this session fixes.**

### Step 2.3 — Define what a valid event actually looks like (30 min)
Add near the top of `jadwal_week2.py`, after your imports:
```python
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
```
This is a **schema you enforce in code**, separate from the JSON schema you show
the model. The model's schema is a request. This is the gate.

**Ask me:** "Why do we need both the JSON schema in `TOOLS` *and* this Pydantic
model — isn't that duplicating the same fields twice?"

### Step 2.4 — Wire validation into the tool call (30 min)
You already have a `try/except` around the tool call from Week 1 Step 3.4. That's
exactly where this plugs in — validation failures are just another kind of tool
failure. Change `create_event` to validate first:
```python
def create_event(title: str, start: str, end: str) -> dict:
    event = EventCreate(title=title, start=start, end=end)  # raises if invalid
    for e in fake_calendar:
        if event.start.isoformat() < e["end"] and event.end.isoformat() > e["start"]:
            return {"error": f"Conflicts with existing event: {e['title']}"}
    new_event = {"title": event.title, "start": event.start.isoformat(), "end": event.end.isoformat()}
    fake_calendar.append(new_event)
    return {"success": True, "event": new_event}
```
Notice: no new try/except needed here. `EventCreate(...)` raises `ValidationError`
if the data is bad, and your existing wrapper in `run_agent_loop` already catches
`Exception` and turns it into a clean `{"error": ...}` tool result instead of a
crash. **Week 1's safety net is what makes this safe to add.**

### Step 2.5 — Re-run your Step 2.2 test (10 min)
Same broken call as before:
```bash
uv run python3
>>> from jadwal_week2 import create_event
>>> create_event(title="", start="not a date", end="also not a date")
```
It should now raise a clear `ValidationError` instead of silently creating
garbage. That's the fix, proven.

### Commit
```bash
git add -A && git commit -m "Week 2: Pydantic validation on create_event"
```

**Ask me:**
- "What's the difference between a `ValidationError` and the `KeyError` we saw in
  Week 1 — why does the same `except Exception` catch both?"
- "Should I validate `delete_event` too? What would that Pydantic model look like?"

---

## Session 2 — Thursday evening (1.5h): Stop it from guessing

### Step 2.6 — Find your Week 1 evidence (10 min)
Open `retro.md` from Week 1. You tested `buatkan meeting jam 3` (no day given) —
what did it actually do? If you don't remember, run it again against
`jadwal_week2.py` right now and watch closely. **This is the bug you're fixing
today.**

### Step 2.7 — Understand why few-shot examples work (10 min)
Telling the model "don't guess" in a rule is weak — it's abstract. Showing it a
worked example of *exactly* the situation, with the *exactly right* response, is
much stronger. This is called **few-shot prompting**: a handful of example
exchanges embedded in the system prompt, so the model can pattern-match against
something concrete instead of interpreting an instruction.

### Step 2.8 — Rewrite `SYSTEM_PROMPT` with examples (45 min)
Replace your current `SYSTEM_PROMPT` in `jadwal_week2.py` with a version that
includes 3–5 example exchanges. Structure:
```python
SYSTEM_PROMPT = f"""You are a scheduling assistant. Today is {datetime.now(TZ).strftime('%A, %Y-%m-%d %H:%M')} in Asia/Jakarta (+07:00).

Rules:
- Always resolve relative dates ("besok", "next Friday") to an exact ISO datetime yourself before calling any tool.
- Before calling create_event or delete_event, state the exact event details back to the user in plain language and ask them to confirm.
- Only call create_event or delete_event after the user has explicitly confirmed in this conversation.
- If the user's request is missing information you need (a day, a time, a duration), ASK — never guess or assume a default.
- All times are Asia/Jakarta (+07:00) unless the user says otherwise.

Examples of correct behavior:

User: "besok jam 3 sore ketemu vendor, 1 jam"
Assistant: [checks tomorrow's calendar, then] "Besok (Rabu, 16 Sep) jam 15:00–16:00, 'Ketemu vendor' — konfirmasi?"

User: "buatkan meeting jam 3"
Assistant: "Meeting jam 3 di hari apa? Dan berapa lama durasinya?"
[This is the important one: no day was given, so the assistant asks instead of guessing "today" or "tomorrow".]

User: "hapus semua meeting besok"
Assistant: "Besok Anda punya 2 meeting: 'Team standup' (09:00) dan 'Ketemu vendor' (15:00). Hapus keduanya?"
"""
```
Write your own 3–5 examples — the one above showing a **clarifying question** is
the one that matters most; keep that pattern, adapt the rest to phrases you
actually expect to type.

### Step 2.9 — Re-test the exact failure from Step 2.6 (15 min)
```bash
uv run jadwal_week2.py
```
Type the same ambiguous phrase that made it guess in Week 1. **It should now ask
a clarifying question instead of inventing a time.** If it still guesses, the
example isn't concrete enough — sharpen it and try again.

### Commit
```bash
git add -A && git commit -m "Week 2: few-shot examples, stop guessing on missing info"
```

**Ask me:**
- "My example didn't fix the guessing — what makes a few-shot example weak vs.
  strong?"
- "How many examples is too many? At what point does the system prompt get
  bloated?"

---

## Weekend block (4h): Vision input

This is the exact skill Phase 6 needs for invoice extraction — you're learning
it now, on a low-stakes calendar invite instead of a real invoice.

### Step 2.10 — Get a test image (10 min)
Take a screenshot of any meeting invite — an email, a WhatsApp message, a Google
Calendar invite screenshot, even a photo of a sticky note with a meeting written
on it. Save it as `test_invite.png` in your project folder. If you don't have a
real one, create a simple one: open any text editor, type something like "Rapat
tim marketing, Jumat 18 Sep, jam 10 pagi, 1 jam", screenshot it.

### Step 2.11 — Understand how images reach the model (20 min)
The model can't "see" a file path. You have to read the image bytes, encode them
as base64 text, and put that text inside the message content — the same
`messages` list you've been using all along, just with a different block type.

```python
import base64

def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")
```

### Step 2.12 — Build `parse_event_from_image` (1h)
This is a **separate, single-shot call** — not the agent loop. You're asking the
model to look at an image and return structured data, once, not have a
back-and-forth conversation.
```python
def parse_event_from_image(image_path: str) -> EventCreate:
    image_b64 = encode_image(image_path)
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=500,
        system=f"Today is {datetime.now(TZ).strftime('%Y-%m-%d')} in Asia/Jakarta (+07:00). Extract the event from this image. Respond with ONLY a JSON object: {{\"title\": str, \"start\": ISO8601 datetime with +07:00, \"end\": ISO8601 datetime with +07:00}}. No other text.",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_b64}},
                {"type": "text", "text": "Extract the event from this image."},
            ],
        }],
    )
    raw = response.content[0].text
    data = json.loads(raw)
    return EventCreate(**data)  # validated, same Pydantic model as before
```
Notice this reuses `EventCreate` from Session 1 — the same validation gate
applies whether the event came from typed text or from a picture. **That's the
payoff of building the validation layer first.**

### Step 2.13 — Test it (30 min)
```python
if __name__ == "__main__":
    event = parse_event_from_image("test_invite.png")
    print(event)
```
Run it, check the extracted title/start/end against what's actually in your
image. If it's wrong, that's real signal — which field did it get wrong, and
why? (Wrong timezone? Misread the date? Guessed a duration that wasn't there?)

### Step 2.14 — Reconnect it to real Jadwal (optional, if time remains)
Once `parse_event_from_image` returns a validated `EventCreate`, you could feed
its fields into the normal `create_event` flow — same confirm-before-write gate
applies. Not required this week, just note it as the natural next step.

### Friday retro
```bash
echo "# Week 2

## Broke:

## Didn't understand:
" > retro.md
```

**Ask me:**
- "The model returned text before the JSON and `json.loads` crashed — how do I
  make it return ONLY JSON, reliably?"
- "What's the difference between what I built here and the tool-use loop from
  Week 1 — why is this a single call instead of a loop?"

---

## Week 2 checkpoint

You're done when all of these are true:
- [ ] `create_event` rejects a bad title / bad dates with a clean error, not a
      crash and not silent garbage
- [ ] The same ambiguous phrase that made Week 1 guess now makes Week 2 ask a
      clarifying question
- [ ] `parse_event_from_image` returns a validated `EventCreate` from a real
      screenshot
- [ ] You can explain: why does validating once (`EventCreate`) cover both the
      text path and the image path?
- [ ] `jadwal_week1.py` is untouched; all this week's work is in `jadwal_week2.py`

---

## What changes in Week 3

Next week the fake in-memory list becomes a real SQLite database, and
`find_free_slot` becomes a real query instead of a Python loop. We'll write that
plan once Week 2 is done — what you struggle with here will shape what Week 3
needs to emphasize.
