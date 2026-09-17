# Jadwal

A natural-language scheduling assistant. Talk to your real Google Calendar in
plain language (Bahasa Indonesia or English) — check what's on it, find free
time, create events, delete events — through an MCP server that plugs
straight into Claude Desktop.

Built as a learning project, one week at a time: a hand-written agent loop
(`jadwal_week1.py`–`jadwal_week3.py`), an n8n workflow calling the same logic
over HTTP (`jadwal_api.py`), and now this — an MCP server so Claude Desktop
can use the same tools directly, against a real calendar instead of a local
database.

## What it can do

- **List events** — "apa jadwal saya minggu ini?"
- **Find free time** — "kapan saya bisa ketemu 1 jam besok?"
- **Create an event** — "buatkan meeting jam 3 sore besok, 1 jam" (always
  proposes the exact details and asks you to confirm before writing anything)
- **Delete an event** — "hapus meeting besok jam 3"

## Setup

### 1. Install dependencies
```bash
uv sync
```

### 2. Google Cloud OAuth setup
1. Go to [console.cloud.google.com](https://console.cloud.google.com), create
   a project
2. Enable the **Google Calendar API** (APIs & Services → Library)
3. Configure OAuth via **Google Auth Platform**:
   - Audience: **External**
   - Add your own email as a **test user** (required — without this you'll
     hit an "Access blocked" error)
4. Create credentials: APIs & Services → Credentials → Create Credentials →
   OAuth client ID → **Desktop app**
5. Download the resulting JSON, save it as `client_secret.json` in this
   project's root folder — **never commit this file** (already in
   `.gitignore`)

### 3. Authorize once
```bash
uv run google_auth_setup.py
```
This opens your browser, you log in and approve calendar access, and it
saves `token.pickle` — also gitignored, also sensitive, treat it like an API
key.

**Known limitation:** while the Google app stays in Testing mode (fine for
personal/single-user use, no formal verification needed), the refresh token
in `token.pickle` expires after **7 days**. When it stops working, just rerun
`google_auth_setup.py` to log in again. Full Google verification would avoid
this, but that requires a hosted privacy policy and a review process that
isn't worth it for one user.

### 4. Connect to Claude Desktop
Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "jadwal": {
      "command": "/path/to/your/uv",
      "args": ["--directory", "/path/to/this/project", "run", "jadwal_mcp.py"]
    }
  }
}
```
Use the **full absolute path** to `uv` (find yours with `which uv`) — GUI
apps like Claude Desktop often don't inherit your shell's full `PATH`, so
just `"uv"` alone can silently fail to launch.

Fully quit and reopen Claude Desktop (`Cmd+Q`, not just close the window).
Check Claude menu → Settings → Developer/Extensions — `jadwal` should show
status **"Running."**

## How it's built

| File | What it is |
|---|---|
| `jadwal_mcp.py` | The MCP server — 4 tools, exposed to Claude Desktop via `stdio` transport |
| `jadwal_calendar.py` | The real Google Calendar backend — `list_events`, `create_event`, `delete_event`, `find_free_slot`, using the OAuth token from `token.pickle`. Self-contained: has its own copy of the `EventCreate` Pydantic validator, deliberately not imported from `jadwal_week3.py`, so this file has zero SQLite dependency |
| `google_auth_setup.py` | One-time (well, weekly, in Testing mode) OAuth login script |
| `jadwal_week3.py` | Earlier SQLite-backed version — kept as a working checkpoint |

**Note on duplication:** `EventCreate` exists in both `jadwal_week3.py` and
`jadwal_calendar.py` — a deliberate tradeoff of duplication for
independence. If the validation rules ever change, both copies need
updating by hand.

**Nothing about `jadwal_mcp.py` or the tool logic changed when the backend
swapped from SQLite to the real Google Calendar API** — same 4 function
names, same return shapes. Only `jadwal_calendar.py`'s internals changed.
That's deliberate: the tools' *interface* is stable regardless of what's
actually storing the data underneath.

## Known limitations — stated honestly, not hidden

- **The confirm-before-write gate is advisory, not enforced.** Unlike the
  hand-written Python version (which has a real `while True` loop that
  waits for your explicit input before ever calling `create_event`), this
  MCP version relies on the tool's *description* telling the model to ask
  first. Claude Desktop's system prompt isn't something this project
  controls. In practice it reliably asks before writing — but it's a
  request, not a hard guarantee the way the Python CLI's loop is.
- **No permission scoping.** Any MCP client that can launch this script
  (i.e., anyone with access to this machine and this config) has full
  read/write access to the connected calendar. There's no per-user or
  per-operation access control.
- **`create_event`'s conflict check is a plain overlap query, not atomic.**
  In the small gap between checking for conflicts and actually inserting,
  a race condition is theoretically possible (though very unlikely for a
  single personal user booking one thing at a time).
- **Testing-mode 7-day token expiry** (see Setup, above) — a real recurring
  chore, not a one-time setup cost.

## Project origin

Built as part of a 11-week self-directed plan to go from AI user to AI
engineer — one project, grown week by week, rather than disconnected
tutorials. See `plan/ai-agent-plan-v2.md` for the full arc.
