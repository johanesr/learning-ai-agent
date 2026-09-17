# Week 4

## Broke:
- Tried to use n8n's SQLite node to talk to `jadwal.db` directly — n8n
  doesn't bundle a SQLite node at all. Searching for it in the Tool picker
  returned nothing. Fixed by writing `jadwal_api.py`, a small FastAPI wrapper
  around the existing Week 3 functions, and having n8n call that over HTTP
  instead.
- All four HTTP Request Tool nodes defaulted to `POST`. Went back and set the
  correct REST verbs: `GET` for `list_events`/`find_free_slot` (read-only),
  `POST` for `create_event` (creates something), `DELETE` for `delete_event`.
- Typed `{{ $fromAI("title") }}` by hand into a body field — got
  `$fromAI("title") is undefined` at runtime. The parameter needs to be
  registered via n8n's "Let model define this parameter" toggle, not typed
  as a raw expression; hand-typing it looks right but doesn't actually wire
  the parameter to the model correctly.
- The confirm-before-write flow broke silently: after saying "ya" to confirm
  a proposed event, the agent called `list_events` instead of `create_event`
  — meaning nothing was ever actually booked, with no visible error. Root
  cause: `create_event`'s tool Description field was still n8n's generic
  default text ("Makes an HTTP request and returns the response data"),
  never customized. With no real description, the model had almost no signal
  to prefer `create_event` over any other tool, and quietly picked the wrong
  one. Same finding likely applied to all four tools' descriptions, not just
  this one, since they were all built the same way in sequence.
- Multi-turn memory reset on every message at first — no Memory node was
  connected under the AI Agent at all, so every message, including "yes,"
  started from zero context. Fixed by adding a Simple Memory node.
- The AI Agent claimed it had no access to today's date. The System Prompt
  field was static text with no date in it — n8n doesn't inject the current
  date automatically the way the Python `SYSTEM_PROMPT` does with
  `datetime.now(TZ)`. Fixed with a Luxon expression:
  `{{ $now.setZone('Asia/Jakarta').toFormat('cccc, yyyy-MM-dd HH:mm') }}`,
  with the System Prompt field switched to Expression mode.
- Separately, and unrelated to n8n: that same Luxon expression got
  accidentally pasted into `jadwal_week3.py`'s Python `SYSTEM_PROMPT` at some
  point, breaking Python's date resolution and silently deleting the Week 2
  few-shot examples in the process. Caught before committing, reverted to
  `datetime.now(TZ)`, examples restored.

## Didn't understand:
- [fill in — anything from this week that's still fuzzy]

## n8n comparison (the real deliverable):

### What it saved:
- The loop itself — no `while True`, no manual `stop_reason` check, no
  hand-written tool-result plumbing.
- The JSON schema boilerplate for each tool — n8n auto-generates it from the
  "Let model define this parameter" toggles instead of hand-writing
  `input_schema` dicts.
- A UI for watching what happened (Executions), instead of scrolling
  terminal print statements.
- What it did NOT save, worth noting: none of the actual tool logic. The
  conflict-check in `create_event` and the gap-finding in `find_free_slot`
  are still 100% Python, imported unchanged from `jadwal_week3.py`. n8n only
  ever learned to make an HTTP call.

### What it hid:
- The real request to Claude isn't sent directly the way `client.messages
  .create(...)` does it — n8n's AI Agent is built on **LangChain**, which
  sits between n8n and Anthropic. Found this by digging into the Chat
  Model sub-node's execution data: messages showed up as `"Human: hello"`
  style strings, and the response was wrapped in a nested
  `generations: [[ {text: ...} ]]` shape — neither of which is Anthropic's
  actual API format, both are LangChain's.
- That it doesn't ship a SQLite node at all — only discovered by hitting the
  wall, not from any warning up front.
- That a vague/default tool description doesn't produce an error. It
  produces silently wrong behavior — the model substituting a different,
  working tool instead of the one it should have used — which looks exactly
  like a reasoning bug from the outside, but is actually a labeling bug.
- That every chat message is a brand-new, separate workflow execution, not
  one continuous process — very different from the Python agent's single
  long-running `while True` loop. Continuity across messages is entirely
  reconstructed by the Memory node re-supplying prior context into each new
  execution, not by anything staying "alive" between messages.

### Where I'd use each, going forward:
- [fill in — does the plan's original framing (n8n for SaaS
  connectors/cron/webhooks/glue, code for custom logic/debugging/measuring)
  still hold up now that you've built both versions of the same thing?]

---

# Week 5

## Important Notes

- **`stdio` transport cannot be deployed to the cloud as-is.** MCP has three
  transports: `stdio`, `sse`, `streamable-http` (confirmed directly from the
  installed SDK's `MCPServer.run()` signature). `stdio` only works because
  the client (Claude Desktop) launches the server as a **subprocess on the
  same machine** and pipes messages through stdin/stdout — there is no
  "stdio over the internet." To run `jadwal_mcp.py` on Google Cloud/AWS,
  it has to switch to `transport="streamable-http"`, get deployed like a
  normal web server (same shape as `jadwal_api.py` from Week 4 — Docker, a
  VPS, a public port), and Claude Desktop (or any client) has to connect to
  it via a URL instead of a local `command`/`args` config.
- **The moment it's reachable over a public URL, authentication stops being
  optional.** Running locally via `stdio`, the only thing that can ever call
  `jadwal_mcp.py`'s tools is your own Claude Desktop on your own machine.
  Deployed over `streamable-http` with no auth, *anyone* who finds the URL
  could call the calendar tools — read and write. This directly connects to
  Step 5.8's "auth and permission scoping" concern: it's theoretical while
  local, genuinely urgent the moment it's deployed.
- **This is the same deployment problem as Weeks 9–10's WhatsApp work** —
  same VPS, same public-reachability requirement, just MCP-over-HTTP
  instead of (or alongside) a webhook. Confirms the pattern one more time:
  the 4 underlying tool functions never change across `stdio` (Claude
  Desktop), HTTP (n8n via `jadwal_api.py`), or eventually `streamable-http`
  (cloud) — only the transport layered on top changes.
- Also confirmed directly with `ps aux`: the locally-running MCP server uses
  ~0.0% CPU and ~36MB RAM idle — negligible, not a real resource concern for
  local use. (Did notice two duplicate server processes after Claude Desktop
  reloaded the config on edit — harmless at this scale, but a full quit/
  reopen of Claude Desktop clears it to a single clean instance.)

## Broke:
- [fill in]

## Didn't understand:
- [fill in]

## The confirm-gate problem (Step 5.10), in my own words:
- [fill in]

## What auth/scoping is actually granted (Step 5.8), and what I'd tighten before sharing this with anyone:
- [fill in]
