# WEEK 4 — n8n, Deliberately

**The whole point of this week, stated up front:** you're not learning n8n
because it's new. You're rebuilding the exact thing you already built by hand
in `jadwal_week3.py`, in n8n, so you can point at any box on the canvas and say
*"I know exactly what that's doing, because I wrote it in Python three weeks
ago."* That's a completely different relationship with the tool than starting
here cold would give you.

**Rule stands:** ask me when something's unclear. Each session has an
**"Ask me"** list.

**Checkpoint for the week:** a written, specific answer to *"what did n8n save
me, and what did it hide from me?"* — not vibes, actual specifics you can point
to.

---

## Before Step 4.1 — what n8n actually is (you've never opened it)

**n8n is a workflow automation tool.** You build on a visual canvas: boxes
("nodes") connected by lines, where each node does one job — "when this webhook
fires," "fetch this from an API," "insert this row into a database." You wire
them together instead of writing glue code by hand. Its well-known cousins are
Zapier and Make — same idea, "connect app A to app B without a custom backend."
n8n's differences: open source, **self-hostable** (why Step 4.1 uses Docker
instead of a sign-up page), and technical enough to drop into real JavaScript
or Python inside a node when the visual pieces aren't enough.

Most of n8n is **ordinary workflow automation** — fixed sequence, no model
involved, same steps every run (a recipe, in Week 1's terms). Useful on its
own for business glue work, no AI required. The **AI Agent node** is the one
piece that's different — n8n's version of everything you've built by hand
since Week 1: the model, the tools, the loop. Everything else on the canvas
around it is the recipe; that one node is the cook.

The "account" in Step 4.3 isn't n8n.cloud or anything tied to a company — once
you open `localhost:5678` for the first time, n8n asks you to set an
email+password stored only in that local container, purely to lock the UI
behind a login on your own machine. Nothing leaves your laptop.

---

## Why rebuild instead of learn n8n fresh

Recall the split from the very start of this plan:

| Moves fast — don't memorise | Hasn't moved since 2023 — learn once |
|---|---|
| n8n's node library, UI | The agent loop |
| | Tools as JSON schema |
| | Model is stateless, you hold history |
| | Confirm-before-write gate |

n8n's **AI Agent node** is a UI wrapped around `run_agent_loop` — the exact
`while True` you've read line by line since Week 1. Its **Tool** sub-nodes are
your `TOOLS` schema entries. Its execution log is your `[tool call]` /
`[tool result]` print statements, dressed up. None of the concepts are new.
What's new is: n8n does the wiring for you, and hides the wiring while it does
it. This week's job is finding exactly what's hidden.

---

## Session 1 — Tuesday evening (1.5h): Install and get oriented

### Step 4.1 — Run n8n locally via Docker (15 min)
```bash
docker run -it --rm --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
```
Open [http://localhost:5678](http://localhost:5678) and create a local account
(stored only on your machine — nothing goes to n8n's cloud with this setup).

**Ask me:** "Why `-v n8n_data:/home/node/.n8n` — what happens if I leave that
out and restart the container?"

### Step 4.2 — Tour the interface before building anything (20 min)
Don't build yet. Just look. Find and click through:
- **Canvas** — where nodes go, connected by lines. This is the part that *does*
  look like a fixed sequence, and for most nodes, it is.
- **Credentials** — where API keys live (you'll add your Anthropic key here in
  a minute). Compare mentally to your `.env` — same purpose, different storage.
- **Executions** — a log of every past run, each step's input/output. This is
  your `print(f"[tool call] ...")` line, but persisted and clickable instead of
  scrolling past in a terminal.

### Step 4.3 — Add your Anthropic credential (10 min)
Search for "Anthropic" when adding a credential, paste your API key (the same
one from `.env` — get a fresh one from the console if you'd rather not reuse
it). **Do not paste your key into a chat node's text field or anywhere visible
on the canvas** — credentials belong in the credential store, which n8n keeps
separate and encrypted, same principle as `.gitignore`-ing `.env`.

### Step 4.4 — Place a bare AI Agent node, no tools yet (25 min)
Add: **Chat Trigger → AI Agent**. Connect your Anthropic credential, pick
`claude-sonnet-5` as the model. Don't add any tools yet — just get a plain
conversation working, same as your very first `hello.py`.

Open the chat panel, say hello, confirm you get a reply. Then click into
**Executions** and find that run. Open it up.

**This is the exercise:** find the raw request n8n sent to the API. It should
look recognizably like your own `client.messages.create(...)` call — a
`messages` array, a `system` prompt field, a `model` string. **You should be
able to point at it and say "that's the exact same shape as my Python code."**

**Ask me:**
- "I can't find where n8n exposes the raw API request/response — where should
  I be looking?"
- "What's n8n's AI Agent node using under the hood — is this a `while True`
  loop like mine, and can I actually see the turns happen one by one?"

### Commit / save
n8n saves workflows in its own UI, not to your git repo — no `git commit` this
session. Just make sure you've saved the workflow with a name like
`jadwal-n8n`.

---

## Session 2 — Thursday evening (1.5h): Wire it to your real tools

### Step 4.5 — Bridge n8n to your data via a tiny API (done)

**The original plan:** point n8n's tools directly at `jadwal.db` via a SQLite
node, so every tool has a direct, line-by-line Python equivalent to compare
against.

**What actually happened:** n8n doesn't bundle a SQLite node, and searching
for one in the Tool picker returns nothing. Real gap in what n8n ships with,
not something you did wrong.

**The fix — a tiny HTTP API in front of the same functions.** `jadwal_api.py`
wraps your existing Week 3 functions (`list_events`, `create_event`,
`delete_event`, `find_free_slot`) — **imported unchanged, no logic
duplicated** — behind four FastAPI endpoints. n8n talks to this API over HTTP
instead of touching the file directly. This is arguably *more* realistic than
the original plan: real n8n setups commonly sit in front of a small backend
API for custom business logic, rather than reaching into a database file
directly.

Already running:
```bash
uv run uvicorn jadwal_api:app --host 0.0.0.0 --port 8000
```
Confirmed working — `curl http://localhost:8000/health` returns `{"status":"ok"}`,
and `list_events` returns real rows from `jadwal.db`.

**One networking detail that matters and is worth understanding, not just
accepting:** from *inside* the n8n container, `localhost:8000` does **not**
reach this API — inside a container, `localhost` means "this container,"
never your Mac. Docker Desktop provides a special hostname for exactly this
situation: **`host.docker.internal`**. So every URL you type into n8n's HTTP
Request Tool nodes this session uses `http://host.docker.internal:8000/...`,
never `http://localhost:8000/...`. Already verified this resolves correctly
from inside the container.

**Ask me:** "Why doesn't `localhost` just work the same way inside a container
as it does on my Mac — what's actually different?"

### Step 4.6 — Add `list_events` as a Tool node (25 min)
`jadwal_api.py`'s endpoints follow normal REST convention — reads are `GET`
with query parameters, writes are `POST`/`DELETE` with a body. Match that in
n8n, don't default everything to POST.

Under the AI Agent node's **Tool** connector, search for **"HTTP Request
Tool"** and add one. Configure:
- **Method:** GET
- **URL:** `http://host.docker.internal:8000/list_events`
- **Query parameters:** add `start` and `end`. For each field's value, use
  the **"Let model define this parameter"** toggle — don't hand-type
  `{{ $fromAI("start") }}` into the value box. Typing it manually can look
  right but fail to actually register the parameter with the model, causing
  a confusing `"$fromAI(...) is undefined"` error at runtime. The toggle is
  the reliable path; it wires up `$fromAI` correctly under the hood.

This toggle is n8n's version of your `input_schema` in `TOOLS` — it tells the
model "you can supply this parameter," and n8n auto-generates the JSON schema
from it instead of you hand-writing the `properties` dict.

**Set BOTH a tool-level description and per-parameter descriptions — this is
not optional polish, it's the single most common failure point this week:**

The **Description** field on the node itself defaults to n8n's generic
placeholder — *"Makes an HTTP request and returns the response data."* That
default tells the model nothing. Replace it:
```
List calendar events between two ISO 8601 datetimes (with timezone offset). Use this to check what's already scheduled before proposing a new event, or when the user asks what's on their calendar.
```

Then, next to each parameter's "Let model define this parameter" toggle,
there's usually a small description field too (sometimes needs expanding) —
fill these in with the exact expected format, same as your Python
`input_schema` already specifies per field:

| Field | Description to use |
|---|---|
| `start` | `ISO 8601 datetime with +07:00 offset, e.g. 2026-09-16T00:00:00+07:00` |
| `end` | `ISO 8601 datetime with +07:00 offset, e.g. 2026-09-16T23:59:59+07:00` |

Without this, the model can send garbage like the literal word `"tomorrow"`
as a date — which doesn't error, it just silently returns zero rows, since
nothing validates the format on the way in. Precise per-field descriptions
are the cheapest fix for that.

### Step 4.7 — Add `create_event`, `delete_event`, `find_free_slot` (35 min)
Same pattern, three more HTTP Request Tool nodes — mind the verb on each:
- `GET http://host.docker.internal:8000/find_free_slot` — query params:
  `duration_minutes`, `after`, `before` (read-only, same reasoning as
  `list_events`)
- `POST http://host.docker.internal:8000/create_event` — JSON body: `title`,
  `start`, `end`, each via the "Let model define this parameter" toggle
  (creates something → POST)
- `DELETE http://host.docker.internal:8000/delete_event` — query params:
  `title`, `start` (removes something → DELETE, params in the URL like GET,
  not a body)

**Tool and parameter descriptions for these three** — again, replace the
generic default on each node, and fill in every parameter description:

| Tool | Description |
|---|---|
| `create_event` | `Create a calendar event. Only call this AFTER the user has explicitly confirmed the exact title, start, and end time in this conversation. Use this when the user has said yes/confirmed to a proposed event — this is what actually books it.` |
| `delete_event` | `Delete a calendar event. Only call this AFTER the user has confirmed the exact title and start time.` |
| `find_free_slot` | `Find open time windows of at least the given duration between two datetimes. Use this when the user asks when they're free, or asks you to find a time for something.` |

| Tool | Field | Parameter description |
|---|---|---|
| `create_event` | `title` | `The event title` |
| | `start` / `end` | Same ISO 8601 format as `list_events` above |
| `delete_event` | `title` | `The exact title of the event to delete` |
| | `start` | Same ISO 8601 format |
| `find_free_slot` | `duration_minutes` | `Duration in minutes, e.g. 60 for one hour` |
| | `after` / `before` | Same ISO 8601 format |

**This exact gap is what will most likely bite you if you skip it:** a vague
or default tool description doesn't cause an error — it causes the model to
quietly avoid the tool it should be using and fall back to a different one
(e.g. calling `list_events` instead of `create_event` after the user
confirms). No crash, no red X, just wrong behavior that looks like a
reasoning bug but is actually a labeling bug. Diagnosed by literally opening
the node and reading what it currently says — if it still reads "Makes an
HTTP request and returns the response data," that's the bug.

**Notice what did NOT need porting:** the conflict-check logic inside
`create_event`, and the whole gap-finding algorithm inside `find_free_slot` —
both are still just Python, running exactly as you wrote them in Week 3,
completely untouched by anything happening in n8n. This is actually a cleaner
demonstration of "tools can be backed by anything" than the original SQLite
plan would have been: the *entire* Week 3 codebase is reused as-is, and n8n
only had to learn how to make one HTTP call per tool.

**Ask me:** "If all my real logic still lives in Python, what did I actually
gain by using n8n here at all?" — genuinely worth asking once you've done this,
not a rhetorical question.

### Step 4.7b — Add Memory, or multi-turn confirmation will silently break (15 min)
Without a Memory node, every message is a brand-new, context-free execution —
by design, since n8n has no long-running process the way your Python
`while True` loop does (see Step 4.5's note on this). Under the AI Agent's
**Memory** connector, add **"Simple Memory"**. Set **Context Window Length**
to something like `15` — not the default `5`, which can be too short: a
multi-turn exchange (clarifying questions, then a proposal, then your "yes")
can easily exceed 5 messages, and if the original proposal falls outside the
window by the time you confirm, the model loses the exact details it needs
and may substitute a different tool call entirely (e.g. `list_events` instead
of `create_event`) rather than admit it forgot.

Check the node's **Session ID** field too — it should read the incoming
session automatically; if it's empty or static, every message looks like an
unrelated new conversation.

### Step 4.8 — Confirm-before-write, in n8n (20 min)
Your Week 1 rule — *"only call create_event after the user has explicitly
confirmed"* — has to exist here too, or you've rebuilt something less safe than
what you already had. Put the same instruction directly in the AI Agent node's
**System Prompt** field — as an *expression* (toggle the field to Expression
mode, or it won't evaluate), so it can inject the real date the same way your
Python `SYSTEM_PROMPT` does with `datetime.now(TZ)`:
```
You are a scheduling assistant. Today is {{ $now.setZone('Asia/Jakarta').toFormat('cccc, yyyy-MM-dd HH:mm') }} in Asia/Jakarta (+07:00).

Rules:
- Always resolve relative dates ("besok", "next Friday") to an exact ISO datetime yourself before calling any tool.
- Before calling create_event or delete_event, state the exact event details back to the user in plain language and ask them to confirm.
- Only call create_event or delete_event after the user has explicitly confirmed in this conversation.
- If the user's request is missing information you need (a day, a time, a duration), ASK — never guess or assume a default.
- All times are Asia/Jakarta (+07:00) unless the user says otherwise.
```
Without the date expression here, the model will plainly tell you it has no
access to today's date — it has no internal sense of "now," same as every
model call since Week 1; it only knows what you explicitly tell it, every
single time.

Test it: ask it to book something, verify it asks you to confirm before the
`create_event` HTTP call actually fires (check **Executions**, or watch your
`jadwal_api.py` terminal log directly — you want to see nothing hit
`/create_event` until after you've said yes).

**Ask me:** "Is the confirm-gate here exactly as reliable as my Python version,
or is there a difference I should worry about?"

---

## Weekend block (4h): The hard parts, and the actual comparison

### Step 4.9 — Confirm `find_free_slot` actually works end to end (30 min)
Because the gap-finding logic stayed in Python this time (Step 4.7), this step
looks different from the original plan — there's no Code-node port needed.
Instead, this is where you actually **test** it properly: ask the n8n agent a
real "when am I free" question, and compare its answer against running the
same question through your Week 3 Python CLI directly. They should match
exactly, since it's the literal same function underneath both.

If you want the deeper "no-code isn't code-free" lesson the original plan was
reaching for, there's still a good version of it available: try building
`find_free_slot`'s gap-walking logic *natively* in n8n, with only a Code node
and no call back to Python, as an optional stretch. You'll likely find it's
awkward compared to just calling your existing function — which is itself the
finding.

### Step 4.10 — Break something on purpose (30 min)
Same instinct as Week 1 Step 2.2 — predict, then check:
- Make a tool node's description vague or wrong. Does the agent misuse it?
- Feed it a malformed date on purpose. Where does the error surface — in the
  chat, in Executions, somewhere else?
- Compare: in Python, a bad tool call became a `{"error": ...}` dict via your
  `try/except`, and the model saw it and reacted. Does n8n's failure reach the
  model the same way, or does it just show a red X on the canvas that only
  *you* see?

This directly answers "what does n8n hide" — a canvas failure that never
reaches the model as a recoverable error is a real, meaningful gap versus what
you built by hand.

### Step 4.11 — Write the comparison (45 min)
This is the actual deliverable for the week. In `retro.md`, answer these
concretely — not in general terms, but pointing at specific things you just
did:

- **What did n8n save you?** (Probably: the loop itself, the JSON schema
  boilerplate, a UI for watching executions instead of print statements. Note
  what it did *not* save you, this time: your actual tool logic stayed 100%
  in Python — n8n only ever called it over HTTP.)
- **What did n8n hide?** (Probably: exactly how errors propagate back to the
  model vs. just failing silently on the canvas; what the actual raw API
  request looks like unless you dig for it — remember it's mediated through
  LangChain, not a direct call; that it doesn't ship a SQLite node at all,
  which you only discovered by hitting the wall.)
- **Where would you use n8n for real work, and where would you still write
  code?** Tie this back to the plan's original framing: *SaaS connectors, cron
  triggers, webhooks, glue* vs. *custom business logic, anything you must
  debug, anything you must measure.* Does that framing still hold up now that
  you've actually built both versions?

### Friday retro
```bash
echo "# Week 4

## Broke:

## Didn't understand:

## n8n comparison (the real deliverable):
### What it saved:
### What it hid:
### Where I'd use each, going forward:
" > retro.md
```

---

## Week 4 checkpoint

You're done when all of these are true:
- [ ] The n8n AI Agent has all 4 tools (`list_events`, `create_event`,
      `delete_event`, `find_free_slot`) working, via `jadwal_api.py`, against
      the same `jadwal.db`
- [ ] Confirm-before-write works in n8n, verified via Executions, not just
      assumed
- [ ] You've found and can point to the raw API request n8n sends, and can
      say "this is the same shape as my `client.messages.create` call"
- [ ] You deliberately broke something and traced exactly how (or whether) the
      error reaches the model
- [ ] `retro.md` has a specific, concrete answer to "what did it save me, what
      did it hide" — not a vague impression
- [ ] Your Python `jadwal_week3.py` is untouched — n8n work lives in n8n

---

## What's next: Week 5–6 — MCP + real Google Calendar

Now the fake/SQLite calendar becomes the real Google Calendar API — OAuth,
refresh tokens, your tools refactored into an MCP server, connected to Claude
Desktop. This is where the n8n Google Calendar node you deliberately skipped
this week gets its code-side counterpart, done properly. We'll write that plan
once Week 4 is actually done.
