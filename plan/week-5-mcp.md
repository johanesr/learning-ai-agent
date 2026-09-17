# WEEK 5 — MCP + Real Google Calendar

**Combined from the original two-week split (MCP protocol, then OAuth) into
one week.** Justification: FastAPI is already de-risked from Week 4's
`jadwal_api.py`, MCP itself is thin (decorators over functions you already
wrote three times), and your pace through Weeks 1–4 has run well ahead of the
plan's 8h/week assumption.

**One honest caveat, stated once:** OAuth is the piece most likely to not
compress cleanly. It's an external service (Google Cloud Console, consent
screens, scopes, redirect URIs) — the same class of friction that cost real
time with Docker and n8n's node ecosystem this session, despite everything
else moving fast. If OAuth eats more than its share of time, let it — don't
force the rest of the week to fit around a deadline. The structure below
front-loads the parts most likely to go fast, so OAuth gets whatever time it
needs.

**The shift this week, stated up front:** every previous week, **you** wrote
the agent loop. This week, for the first time, **you write zero agent loop.**
Claude Desktop already has one, built by Anthropic. Your job is purely
building the kitchen — exposing your tools through MCP so *someone else's*
chef can use them.

**Rule stands:** ask me when something's unclear. Each session has an
**"Ask me"** list.

**Goal by Sunday:** Claude Desktop, talking to your **real** Google
Calendar, through tools that are — structurally — the exact same
`list_events`, `create_event`, `delete_event`, `find_free_slot` you've built
three times already.

---



## Why MCP, conceptually

Recall Week 4: n8n's AI Agent called your tools over HTTP, through
`jadwal_api.py`. That worked, but you invented your own request/response
shape — nothing forced n8n and your API to agree on anything beyond "it's
JSON over HTTP." **MCP is a standard shape for exactly this handoff.**
Instead of every tool-providing service inventing its own API style, MCP
defines how a server *advertises* tools (name, description, input schema —
your `TOOLS` list from Week 1, formalized into a spec), how a client *calls*
one, and how results come back. Any MCP-speaking client (Claude Desktop,
Cursor, your own code) can talk to any MCP-speaking server, zero custom glue.

---



## Session 1 — Tuesday evening (1.5h): First MCP server, against SQLite

Deliberately still on `jadwal.db` this session — proving the protocol works
before adding OAuth on top, so if something breaks later you know which
layer it's in.

### Step 5.1 — Install the MCP Python SDK (10 min)

```bash
cd "/Users/johanes/Documents/AI/Learning Agent"
uv add "mcp[cli]"
```



### Step 5.2 — Build the smallest possible server (25 min)

New file, `jadwal_mcp.py`. Notice what's missing compared to every file so
far: no `import anthropic`, no `client = anthropic.Anthropic()`, no
`SYSTEM_PROMPT`, no loop. None of that is your job this week.

**Version note:** `pyproject.toml` already has `mcp[cli]>=2.2.0` installed.
Most MCP tutorials/docs online still show the older `FastMCP` class from
`mcp.server.fastmcp` — that got renamed to `MCPServer` in `mcp.server .mcpserver` in the SDK's v2 release. Same decorator usage (`@mcp.tool()`),
just a different import path. If a guide you're reading elsewhere uses
`FastMCP`, mentally substitute `MCPServer`.

```python
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("jadwal")

@mcp.tool()
def list_events(start: str, end: str) -> list:
    """List calendar events between two ISO 8601 datetimes (with timezone offset)."""
    from jadwal_week3 import list_events as _list_events
    return _list_events(start, end)

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

`@mcp.tool()` reads the function's type hints and docstring, and
auto-generates the exact JSON schema block you used to hand-write in `TOOLS`.
**The docstring is the tool description now** — same "label on the drawer"
lesson, auto-extracted instead of typed separately.

**Ask me:** "How does `@mcp.tool()` know the input schema just from type
hints — what if I don't type-hint a parameter?"

### Step 5.3 — Understand `transport="stdio"` (10 min)

`stdio` means this server talks to its client over standard input/output —
not a network port. Claude Desktop *launches your script as a subprocess*
and pipes MCP messages through stdin/stdout. Different model than
`jadwal_api.py`'s HTTP server, which anyone on the network could reach —
`stdio` is local-only, one client, by construction.

### Step 5.4 — Connect it to Claude Desktop (25 min)

Install Claude Desktop if needed: [claude.ai/download](https://claude.ai/download).
Edit its config:

```bash
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

```json
{
  "mcpServers": {
    "jadwal": {
      "command": "/Users/johanes/.local/bin/uv",
      "args": ["--directory", "/Users/johanes/Documents/AI/Learning Agent", "run", "jadwal_mcp.py"]
    }
  }
}
```

(Full path to `uv` rather than just `"uv"` — GUI apps like Claude Desktop get
a more limited `PATH` than your terminal and may not find `uv` by name
alone.)

Fully quit and reopen Claude Desktop (`Cmd+Q`, not just close the window).
Start a new chat, ask about your calendar. To confirm it's actually
connected, check Claude menu → Settings → Developer/Extensions — `jadwal`
should show status "Running."

### Step 5.5 — Add the remaining 3 tools (20 min)

Same `@mcp.tool()` pattern for `create_event`, `delete_event`,
`find_free_slot`, importing from `jadwal_week3.py` exactly like
`list_events`. **Reuse the exact description wording from**
`plan/week-4-n8n.md`**'s tables** — same failure mode applies here: a vague
docstring means Claude Desktop won't reliably pick the right tool, exactly
like the `create_event`-calling-`list_events` bug from Week 4. Remember: a
`#` comment does NOT work as a tool description — only a triple-quoted
docstring as the function's first line is readable by `@mcp.tool()` at
runtime (`__doc__`); a comment is discarded by Python before anything can
read it.

**Checkpoint for this session:** all 4 tools work in Claude Desktop against
`jadwal.db` — a completely different chat client than anything you've built,
using code you wrote weeks ago, unmodified.

---



## Session 2 — Thursday evening (1.5h): Google Cloud setup + OAuth

This is where the week's real risk lives — budget the full session for it,
and don't be surprised if it spills into the weekend block.

### Step 5.6 — Google Cloud Console setup (30 min)

1. Go to [console.cloud.google.com](https://console.cloud.google.com), create
  a new project (or reuse one)
2. Enable the **Google Calendar API** (APIs & Services → Library → search
  "Google Calendar API" → Enable)
3. Configure OAuth via **Google Auth Platform** (Google's current setup
  flow — replaces the older "OAuth consent screen" page):
  - **App Information:** App name → `Jadwal`; User support email → your own
  - **Audience:** choose **External** (Internal only works on a Google
  Workspace org account, not a personal Gmail). This does NOT mean
  "anyone can use it" — while in **Testing** mode, only email addresses
  you explicitly add as test users can ever complete the login. Add your
  own email as a test user. No formal Google verification needed, as
  long as you stay under 100 test users (you're 1).
  **Real limitation, not glossed over:** Testing mode's refresh tokens
  expire after **7 days** — `token.pickle` from Step 5.7 will need
  regenerating roughly weekly (redo the browser login) unless you go
  through full verification later, which is disproportionate effort for
  one user and not worth chasing just for personal use. Plan on either
  re-running the OAuth script weekly, or (stretch, optional) writing a
  small check that detects an expired token and re-prompts
  automatically. Document this limitation honestly in the Step 5.12
  README rather than letting it surprise you later.
  - **Contact Information / Finish:** your email, agree to the terms
4. Create **credentials** (APIs & Services → Credentials → Create
  Credentials → OAuth client ID → Desktop app). Name it something
   recognizable like `Jadwal Desktop` — this label is just for your own
   reference in the console, never shown to anyone else. Download the
   resulting JSON — this is your `client_secret.json`. **Add it to**
   `.gitignore` **immediately, before it touches disk in this project
   folder** — same discipline as `.env`, same reason.

**Ask me:** "What's actually the difference between Testing mode and
Production/Verified — do I need to ever leave Testing mode for personal
use?"

### Step 5.7 — The OAuth flow itself (30 min)

```bash
uv add google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

Write a small standalone script, `google_auth_setup.py`, that runs the
consent flow once and saves a refresh token:

```python
from google_auth_oauthlib.flow import InstalledAppFlow
import pickle

SCOPES = ["https://www.googleapis.com/auth/calendar"]

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(port=0)

with open("token.pickle", "wb") as f:
    pickle.dump(creds, f)

print("Saved token.pickle — you won't need to log in again.")
```

Running this opens your browser, you log into Google, approve the scope, and
it saves a **refresh token** locally. **Add** `token.pickle` **to** `.gitignore`
**too** — it's as sensitive as an API key, since it grants ongoing access to
your real calendar.

**Ask me:** "What's a refresh token actually for — why not just save the
access token directly?"

### Step 5.8 — Understand what you just granted (15 min)

Note the scope: `https://www.googleapis.com/auth/calendar` is **full
read/write** access to your calendar. Google offers narrower scopes (e.g.
`calendar.readonly`, `calendar.events` only). Worth a deliberate choice, not
a default: for this project you do need write access eventually
(`create_event`/`delete_event`), so the full scope is reasonable — but this
is the moment to actually notice you're granting it, not scroll past it.

---



## Weekend block (4h): Swap the backend, test for real, wrap up



### Step 5.9 — Swap all 4 tool functions to the real API (1.5h)

This is the actual payoff of the week. Rewrite `list_events`, `create_event`,
`delete_event`, `find_free_slot` (either directly in `jadwal_week3.py` or a
new `jadwal_calendar.py` — your call) to call the Google Calendar API instead
of SQLite, using the saved `token.pickle`:

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import pickle

with open("token.pickle", "rb") as f:
    creds = pickle.load(f)

service = build("calendar", "v3", credentials=creds)

def list_events(start: str, end: str) -> list:
    result = service.events().list(
        calendarId="primary", timeMin=start, timeMax=end,
        singleEvents=True, orderBy="startTime",
    ).execute()
    return [
        {"title": e["summary"], "start": e["start"]["dateTime"], "end": e["end"]["dateTime"]}
        for e in result.get("items", [])
    ]
```

Notice the **return shape stays identical** — `{"title", "start", "end"}` —
on purpose, so nothing calling this function needs to change, MCP layer
included. This is the kitchen/chef lesson at its most concrete yet: the
entire backend changed (SQLite → real Google API) and the chef (Claude
Desktop) never needs to know.

`create_event`, `delete_event`, `find_free_slot` follow the same pattern —
port the logic, keep the interface. `find_free_slot`'s gap-walking algorithm
doesn't need to change at all, only what feeds it real event data.

**Ask me:** "Do I still need my own conflict-check logic in `create_event`,
or does Google's API already prevent double-booking on its own?"

### Step 5.10 — The confirm-gate problem (30 min)

Real design question this week surfaces that n8n didn't: **there's no system
prompt field you control** — Claude Desktop's system prompt is Anthropic's,
not yours. Where does the confirm-gate live now?

- **Tool description text** — e.g. *"Only call this after the user has
explicitly confirmed the exact details in this conversation."* A request,
not an enforced rule the way your Python `while True` loop enforced it.
- **Server-side confirmation state** — genuinely enforce it in code: track
whether a matching event was already proposed and echoed back, reject the
call if not.

For this week, the description approach is enough to observe the gap — but
**write it into** `retro.md` **as a real, unsolved limitation**, not a solved
problem.

### Step 5.11 — Test against your real calendar, deliberately (30 min)

Same rigor as Week 4's test table. Ask it to check your real schedule
(read-only, safe). Then ask it to create something small and low-stakes —
watch whether it actually asks to confirm before calling the tool. Then
**check your actual Google Calendar** (phone, browser) to confirm what
landed is correct — this is the first week where a mistake writes somewhere
that matters, so verify for real, don't just trust the chat reply.

### Step 5.12 — README + optional stretch (30 min, stretch is optional)

Write a README for `jadwal_mcp.py` — setup (`uv add`, the Claude Desktop
config, the OAuth setup script), what each tool does, the known
confirm-gate limitation from Step 5.10.

**Optional, only if time remains:** read the source of an existing
open-source Odoo MCP server on GitHub — don't run it. **Note: the company's
actual system is a custom in-house Postgres-backed system, not Odoo — no
pre-built MCP server exists for it.** This exercise is now general
architecture-pattern research only (how they structure tools per data
model, how they gate writes), not something to adapt directly. If the week
already ran long because of OAuth, skip this without guilt.

### Friday/weekend retro

```bash
echo "# Week 5

## Broke:

## Didn't understand:

## The confirm-gate problem (Step 5.10), in my own words:

## What auth/scoping is actually granted (Step 5.8), and what I'd tighten before sharing this with anyone:
" > retro.md
```

---



## Week 5 checkpoint

You're done when all of these are true:

- [x] All 4 tools work in Claude Desktop against `jadwal.db` (Session 1)
- [x] OAuth flow completed, `token.pickle` saved, **gitignored**
- [ ] All 4 tools swapped to the real Google Calendar API, same interface,
  ```
  tested against your actual calendar and verified in the real Google
  Calendar app/site, not just trusted from the chat reply
  ```
- [x] You can explain why this week has no `SYSTEM_PROMPT`/`run_agent_loop`
  ```
  — who owns the loop now, and why
  ```
- [ ] You've identified, concretely, that the confirm-gate is weaker here
  ```
  than in your Python/n8n versions, and written down what a real fix
  would look like
  ```
- [ ] `client_secret.json` and `token.pickle` — confirmed never committed

---



## What's next: Weeks 6–7 — Evals

25 real phrases, expected outputs, a script that scores your agent's
accuracy as a number. This is the phase most people skip, and it's the one
that separates a demo from something you'd trust near real data — which,
after this week, your calendar now genuinely is.