# WEEK 3 — Real Data (SQLite)

Builds on `jadwal_week3.py` (a copy of your finished `jadwal_week2.py`).
`jadwal_week1.py` and `jadwal_week2.py` stay untouched as checkpoints.

**Compressed on purpose:** you already know SQL and databases, so this skips
teaching SQL itself. It's one week instead of the original two, and focuses
only on what's specific to *agents* — which SQL knowledge alone doesn't cover.
See [ai-agent-plan-v2.md](ai-agent-plan-v2.md) for the updated 12-week arc
(n8n now lands Week 4).

**Goal by Sunday:** the fake in-memory list is gone. A real SQLite file backs
every tool, a 4th tool (`find_free_slot`) does real gap-finding, and you can
answer a hard scheduling question correctly using data the model never saw
directly — plus close out the week with a short, honest answer to "why not a
vector DB for this."

**The rule stands:** ask me when something's unclear, don't go search it.
Each session still has an **"Ask me"** list.

---

## Why this week matters, stated plainly

Everything in Weeks 1–2 lived in a Python list that reset to one hardcoded
"Team standup" event every time you ran the script. That was fine for learning
the loop — but it's not a real assistant. This week, the calendar becomes
something that actually persists, and the tools become real queries instead of
list comprehensions.

**What does NOT change:** the agent loop, the chef/kitchen model, the
confirm-before-write gate, the Pydantic validation. The model still never
touches the database — it still only asks, and your Python still runs
everything. Swapping the storage layer underneath the tools is the whole
lesson: **tools can be backed by anything, and the agent never knows the
difference.**

---

## Session 1 — Tuesday evening (1.5h): The list becomes a database

### Step 3.1 — Design the schema (15 min)
You know how to do this. Fields: `id, title, start, end, tz, attendees, notes`.

One decision worth making deliberately, not by habit: **store `start`/`end` as
ISO 8601 text with the `+07:00` offset** (`"2026-09-16T09:00:00+07:00"`), not as
a Unix epoch integer. Reasoning: this is what the model already produces and
consumes everywhere else in your tool schemas — keeping the storage format
identical to the wire format means zero conversion logic between "what the
model says" and "what's in the row." As long as every timestamp is written with
the same fixed offset, ISO 8601 text still sorts correctly with a plain
`ORDER BY start` — SQLite compares it lexicographically, and that happens to
match chronological order for a fixed-format, fixed-offset string.

**Ask me:** "When would epoch integers actually be the better choice over ISO
text — what am I giving up here?"

### Step 3.2 — Create the database (20 min)
Add near your `TZ`/`client` setup in `jadwal_week3.py`:
```python
import sqlite3

DB_PATH = "jadwal.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            start TEXT NOT NULL,
            end TEXT NOT NULL,
            tz TEXT NOT NULL DEFAULT 'Asia/Jakarta',
            attendees TEXT,
            notes TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_start ON events(start)")
    conn.commit()
    conn.close()

init_db()
```
Delete the `fake_calendar = [...]` list entirely — you don't need it anymore.

Run once, then check the file actually got created:
```bash
uv run python3 -c "from jadwal_week3 import init_db; init_db()"
ls -la jadwal.db
```

**Add `jadwal.db` to `.gitignore`** — it's local runtime data, not source:
```bash
echo "jadwal.db" >> .gitignore
```

**Ask me:** "Why an index on `start`? What would break — or just be slow —
without it?"

### Step 3.3 — Rewrite `list_events` as a real query (20 min)
```python
def list_events(start: str, end: str) -> list:
    """Return events between two ISO datetimes."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT title, start, end FROM events WHERE start >= ? AND end <= ? ORDER BY start",
        (start, end),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

**The one thing worth flagging that's not just "normal SQL":** the `?`
placeholders here aren't optional style — `start` and `end` are values the
**model chose**, not a form field a known user typed. Parameterized queries
protect you from SQL injection the same way regardless of source, but the risk
model is different: a typical web form has a narrow, predictable set of bad
inputs; an LLM's output is far less predictable, and a bug in your prompt or a
weird edge case could make the model emit almost anything as an argument.
Never string-format a query with model-supplied values.

**Ask me:** "Is there ever a case where I'd need to trust model input MORE than
user input, or is it always less?"

### Step 3.4 — Rewrite `create_event` and `delete_event` (35 min)
Conflict detection becomes a real query instead of a Python loop:
```python
def create_event(title: str, start: str, end: str) -> dict:
    event = EventCreate(title=title, start=start, end=end)  # unchanged — same gate
    conn = sqlite3.connect(DB_PATH)
    conflict = conn.execute(
        "SELECT title, start, end FROM events WHERE start < ? AND end > ?",
        (event.end.isoformat(), event.start.isoformat()),
    ).fetchone()
    if conflict:
        conn.close()
        return {"error": f"Conflicts with existing event: {conflict[0]} ({conflict[1]}–{conflict[2]})"}
    conn.execute(
        "INSERT INTO events (title, start, end) VALUES (?, ?, ?)",
        (event.title, event.start.isoformat(), event.end.isoformat()),
    )
    conn.commit()
    conn.close()
    return {"success": True, "event": {"title": event.title, "start": event.start.isoformat(), "end": event.end.isoformat()}}


def delete_event(title: str, start: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT id FROM events WHERE title = ? AND start = ?", (title, start)).fetchone()
    if not row:
        conn.close()
        return {"error": f"Event not found: {title} at {start}"}
    conn.execute("DELETE FROM events WHERE id = ?", (row[0],))
    conn.commit()
    conn.close()
    return {"success": True, "deleted": {"title": title, "start": start}}
```
Notice the Pydantic validation in `create_event` didn't change at all — the
validation layer and the storage layer are genuinely independent, which is the
payoff of having built Week 2's gate as its own thing rather than bolting
checks directly onto list operations.

### Step 3.5 — Prove persistence (10 min)
This is the actual milestone this session is building toward — go see it work:
```bash
uv run jadwal_week3.py
```
Create an event, confirm it, then **quit the program entirely** and run it
again:
```bash
uv run jadwal_week3.py
```
Ask "apa jadwal saya hari ini?" — the event you created in the *previous run*
should still be there. In Weeks 1–2 it would have vanished. This is the
concrete difference a real database makes.

### Commit
```bash
git add -A && git commit -m "Week 3: SQLite-backed tools, real queries, persistence"
```

---

## Session 2 — Thursday evening (1.5h): Free-slot finding, the 4th tool

### Step 3.6 — Why this isn't pure SQL (10 min)
"Find the gaps between these meetings" doesn't map cleanly onto a single SQL
query without window functions (`LAG`/`LEAD`), which is more SQL machinery than
this needs for a handful of events per day. The pragmatic approach: **fetch the
day's events with SQL, ordered by start, then walk the gaps in plain Python.**
Worth naming explicitly: querying and reasoning-over-results are two different
jobs, and it's fine — often better — to split them instead of forcing
everything into one query.

### Step 3.7 — Build `find_free_slot` (40 min)
```python
def find_free_slot(duration_minutes: int, after: str, before: str) -> list:
    """Find open windows of at least `duration_minutes` between `after` and `before`."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT start, end FROM events WHERE start >= ? AND end <= ? ORDER BY start",
        (after, before),
    ).fetchall()
    conn.close()

    events = [dict(r) for r in rows]
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
```
Walk through it yourself before running anything: `cursor` tracks "the earliest
free moment so far." For each event, if there's enough room between `cursor`
and that event's start, that's a free slot — then `cursor` jumps to the end of
that event (or stays put if this event is fully inside a slot you already
passed). After the loop, check if there's room between the last `cursor`
position and the end of the search window.

**Ask me:**
- "Walk me through what happens if two events overlap each other in the data —
  does this still work?"
- "Why `max(cursor, e_end)` instead of just `cursor = e_end`?"

### Step 3.8 — Wire it as a 4th tool (20 min)
Same three places as every tool before it — you've done this twice now, so this
should be fast:
1. The function (done above)
2. `TOOLS` schema entry — `duration_minutes: integer`, `after`/`before`: ISO
   datetime strings
3. `TOOL_FUNCTIONS["find_free_slot"] = lambda args: find_free_slot(**args)`

Test it directly before involving the model:
```bash
uv run python3 -c "from jadwal_week3 import find_free_slot; print(find_free_slot(60, '2026-09-17T08:00:00+07:00', '2026-09-17T18:00:00+07:00'))"
```

### Commit
```bash
git add -A && git commit -m "Week 3: find_free_slot as a real tool"
```

---

## Weekend block (4h): Hard questions, schema reasoning, token budgeting

### Step 3.9 — Ask it something it actually has to work for (30 min)
```bash
uv run jadwal_week3.py
```
Try: `"kapan saya bisa ketemu 2 jam minggu ini?"` — this requires the model to
call `find_free_slot` with a sensible date range (it has to figure out "this
week" itself, and Asia/Jakarta boundaries), read the result, and explain it in
plain language. Watch the `[tool call]` line to see exactly what range it
chose — is it right?

### Step 3.10 — Schema design for reasoning, not just normalization (30 min)
You already know how to design a schema so it's correct and non-redundant.
This is a different lens: **design it so the model can reason about it well.**
Two concrete things to actually do:

- Add a real `attendees` field (comma-separated text is fine for now) and ask
  the model something like *"siapa saja yang ada di meeting saya besok?"* —
  does `list_events` even return `attendees`? Right now it doesn't select that
  column. Fix it, and notice: **a field existing in the schema doesn't mean the
  model can see it** — it has to be in the `SELECT` and in what you hand back
  as the tool result.
- Consider: what happens if `tz` were folded directly into the datetime string
  instead of its own column (which, structurally, it already sort of is, via
  the `+07:00` offset)? When would a *separate* `tz` column actually earn its
  keep — e.g., an attendee in a different timezone?

**Ask me:** "I added a field to the table but the model still doesn't seem to
use it right — what am I missing?"

### Step 3.11 — Token budgeting, hands-on (30 min)
Add a running total after each model call in `run_agent_loop`:
```python
print(f"  [usage] in={response.usage.input_tokens} out={response.usage.output_tokens}")
```
Have a long back-and-forth conversation — ask several things in a row without
quitting. Watch `input_tokens` climb turn over turn. That growth is the entire
conversation history getting resent every single call — the thing we
established back in Week 1 (the model is stateless, you resend everything).

Now the practical question: at what point would you start trimming old turns
out of `messages`, and what would you be safe to drop first? (Hint: tool
results from three turns ago about an event you already resolved are usually
safe to summarize or drop; the user's original request usually isn't.)

You don't need to build trimming logic this week — just observe the cost curve
and form an opinion on where you'd cut.

### Step 3.12 — Why SQL, not a vector database (15 min, write it down)
The main plan explicitly skips vector DBs for this kind of data. You've now
built the SQL version — write 3–4 sentences in `retro.md` in your own words on
*why* a structured query beat a semantic/embedding search here. (Hint: your
data has exact fields with exact meanings — `start`, `end`, `title` — and your
questions are precise — "what's free after 2pm" — not fuzzy — "find me
something like my last vendor meeting." Vector search shines on the second
kind of question, not the first.)

### Friday retro
```bash
echo "# Week 3

## Broke:

## Didn't understand:

## Why SQL, not vector search (in my own words):
" > retro.md
```

---

## Week 3 checkpoint

You're done when all of these are true:
- [ ] `jadwal.db` persists between separate runs of the script — proven, not
      assumed
- [ ] `list_events`, `create_event`, `delete_event` all run real parameterized
      SQL, no Python list left
- [ ] `find_free_slot` exists as a 4th tool, wired through all three places,
      and gives correct answers against real data
- [ ] It correctly answers a "when am I free" question using data it never saw
      directly in the prompt
- [ ] You've watched `input_tokens` grow across a conversation and can say
      where you'd trim
- [ ] `jadwal_week1.py` and `jadwal_week2.py` are untouched

---

## What's next: Week 4 — n8n, deliberately

You rebuild this same agent in n8n — same tools, same SQLite file if you want,
or n8n's own Google Sheets/Postgres node as a stand-in. The point isn't the
rebuild itself; it's finding, in n8n's UI, every piece you just built by hand:
where's the loop, where's the tool schema, where's `stop_reason`, where does a
bad query show up when something goes wrong. We'll write that plan once Week 3
is actually done.
