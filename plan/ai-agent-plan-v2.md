# Plan v2 — Fundamentals First, Then n8n

Replaces the pacing of `ai-agent-learning-plan.md`. Same project (Jadwal), same
end goal, but n8n is now explicitly in the plan instead of silently skipped, and
the fundamentals block is compressed from 6 weeks to 4.

**Start date:** Tuesday 2026-09-15
**Rule for this whole document:** if a step doesn't make sense, stop and ask me.
Every session below has an **"Ask me"** list — those are the questions worth
asking. Don't go searching the internet for them; the answers depend on what
*your* code is doing, and I can see your code.

---

## Why fundamentals before n8n (the short version)


| Moves fast — don't memorise | Hasn't moved since 2023 — learn once |
| --------------------------- | ------------------------------------ |
| Model names, prices         | The agent loop                       |
| Framework APIs              | Tools as JSON schema                 |
| n8n's node library          | Model is stateless, you hold history |
| "Best model this month"     | Context is the bottleneck            |
|                             | Evals are the only proof it works    |


n8n's AI Agent node *is* the loop in the right-hand column, with a UI over it.
Four weeks of the left column and you can read any n8n workflow at a glance.

**Use n8n for:** SaaS connectors, cron triggers, webhooks, glue.
**Write code for:** custom tools with business rules, anything you must debug,
anything you must measure, anything where cost at volume matters.

---



## The reshaped arc


| Weeks | Block                          | What you end up with                                                            |
| ----- | ------------------------------ | ------------------------------------------------------------------------------- |
| 1–2   | **The loop, by hand**          | Jadwal CLI, fake calendar, 4 tools, you can explain every byte                  |
| 3     | **Context + data** *(compressed — you already know SQL)* | SQLite-backed, conflict detection, answers questions about data it had to fetch. Skips SQL basics; focuses on tool-function design over queries, schema-for-reasoning, token budgeting. |
| 4     | **n8n, deliberately**          | The same agent rebuilt in n8n. A written comparison: what it saved, what it hid |
| 5     | **MCP + real Google Calendar** *(compressed — FastAPI already proven in Week 4, MCP is thin)* | OAuth, refresh tokens, your tools as an MCP server in Claude Desktop, backed by your real calendar |
| 6–7   | **Evals**                      | 25 test phrases, a score you can state as a number                              |
| 8–9   | **Ship**                       | FastAPI (already de-risked) or Telegram front end, deployed, logged, cost-tracked |
| 10–11 | **Company pilot**              | One narrow process against the real in-house Postgres system, measured against the manual version |

*(Updated 2026-09-16: Week 3-4 compressed to Week 3 alone since Johanes already
knows SQL. n8n lands Week 4.)*
*(Updated 2026-09-18: Weeks 5-6 (MCP + OAuth) compressed to Week 5 alone —
FastAPI groundwork already done in Week 4's `jadwal_api.py`, and MCP itself is
mostly decorators over existing functions. OAuth remains the one real risk to
this compression, flagged in `plan/week-5-mcp.md` — if it runs long, let it,
rather than force the rest of the week. 11 weeks total now, not 12.)*


Two weeks longer than v1, because v1's Phase 5 was overloaded and would have
been skipped anyway.

**Weekly rhythm:** 2 weekday evenings × 1.5h + 1 weekend block × 4h.
**Friday, 15 minutes:** write down what broke and what you didn't understand.
That list is the actual curriculum — bring it to me.

---



# WEEK 1 — In full detail

Goal by Sunday: `jadwal_week1.py` runs, you've added a tool yourself, and you
can explain the loop out loud without looking.

## Session 1 — Tuesday evening (1.5h): Get it running



### Step 1.1 — Install uv (5 min)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen your terminal, then check:

```bash
uv --version
```

*Why uv and not pip: it manages the Python version and the packages together,
so "works on my machine" stops being a problem when you deploy in week 10.*

### Step 1.2 — Make it a project (10 min)

```bash
cd "/Users/johanes/Documents/AI/Learning Agent"
uv init --python 3.12
uv add anthropic python-dotenv
git init
```



### Step 1.3 — Your API key (10 min)

Get one at console.anthropic.com. Then:

```bash
echo 'ANTHROPIC_API_KEY=sk-ant-your-key-here' > .env
echo '.env' > .gitignore
echo '.venv/' >> .gitignore
```

**Check** `.gitignore` **exists before your first commit.** A key committed to git is
a key you must revoke, even in a private repo.

### Step 1.4 — First commit (5 min)

```bash
git add -A
git commit -m "Week 1: project setup"
git status   # should show nothing untracked except maybe .venv
```



### Step 1.5 — One message to a model (20 min)

Before the agent loop, prove the plumbing works. Create `hello.py`:

```python
from dotenv import load_dotenv
import anthropic

load_dotenv()
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=200,
    messages=[{"role": "user", "content": "Say hello in Bahasa Indonesia."}],
)
print(response.content[0].text)
print("---")
print(f"tokens in: {response.usage.input_tokens}, out: {response.usage.output_tokens}")
```

Run it:

```bash
uv run hello.py
```

**Checkpoint:** you see a reply and a token count. If you see an auth error, the
`.env` isn't loading — check you're in the right directory.

### Step 1.6 — Run Jadwal (30 min)

```bash
uv run jadwal_week1.py
```

Type exactly this:

```
besok jam 3 sore ketemu vendor, 1 jam
```

Watch the `[tool call]` and `[tool result]` lines. Then say `ya` to confirm.
Then type:

```
apa jadwal saya besok?
```

**Ask me:**

- "Why did it call `list_events` before `create_event` there?"
- "What is `stop_reason` and why does the loop check it?"
- "Why does the tool result get appended with `role: user` and not something else?"



### Commit

```bash
git add -A && git commit -m "Week 1: first agent run working"
```

---



## Session 2 — Thursday evening (1.5h): Read it, then break it



### Step 2.1 — Read `run_agent_loop` line by line (30 min)

Open `jadwal_week1.py` at the `run_agent_loop` function. Read it slowly. It is
about 30 lines and it is the entire concept. For each line, answer out loud:
*what would go wrong if this line weren't here?*

The shape you're looking for:

```
1. send conversation + tool definitions to the model
2. model replies with either TEXT (done) or a TOOL_USE block (wants something)
3. if tool_use: you run the function, append the result, go to 1
4. if text: return, wait for the human
```



### Step 2.2 — Break it on purpose (45 min)

Run it and try each of these. **Write down what happens before you run each one
— predict first, then check.**


| Input                                    | What you're testing                                           |
| ---------------------------------------- | ------------------------------------------------------------- |
| `asdkjhasd`                              | Nonsense input                                                |
| `book a meeting tomorrow 9am for 30 min` | Overlaps the existing standup — does the conflict check fire? |
| `book something next Ramadan`            | A date it can't resolve                                       |
| `book 3 meetings tomorrow`               | Multiple tool calls in one turn                               |
| `buatkan meeting jam 3` (no day)         | Missing information — does it ask, or guess?                  |


The last one matters most. **An agent that guesses silently is the dangerous
kind.** Note whether it asked you or invented a date.

### Step 2.3 — Friday retro file (15 min)

```bash
echo "# Week 1\n\n## Broke:\n\n## Didn't understand:\n" > retro.md
```

Fill it in. Bring it to me.

**Ask me:**

- "It guessed a date instead of asking — how do I fix that in the system prompt?"
- "What happens if the model calls a tool that doesn't exist in `TOOL_FUNCTIONS`?"
- "The conversation list keeps growing — when does that become a problem?"

---



## Session 3 — Weekend block (4h): Add a tool yourself

This is the session that actually teaches you. Adding a tool means touching all
three places a tool lives, and that's the mental model you need.

### Step 3.1 — Understand the three places (20 min)

Every tool exists in exactly three spots in `jadwal_week1.py`:

1. **The Python function** — `def delete_event(...)`, the real work
2. **The schema in** `TOOLS` — what the *model* sees; it never sees your Python
3. **The entry in** `TOOL_FUNCTIONS` — the name→function wiring

Miss any one of the three and you get a specific, recognisable failure. Learn
what each failure looks like.

### Step 3.2 — Build `delete_event` (1.5h)

Requirements, in order:

- Takes a `title` and a `start` (so it can identify one specific event)
- Returns an error dict if no matching event exists — **never** fail silently
- Returns `{"success": True, "deleted": {...}}` on success
- Schema description tells the model to confirm with the user before calling it

Write the function first, test it directly in Python (no model involved):

```python
# at the bottom of the file, temporarily
print(delete_event("Team standup", "2026-09-16T09:00:00+07:00"))
print(delete_event("Nonexistent", "2026-01-01T00:00:00+07:00"))
```

Only once that works, wire up the schema and `TOOL_FUNCTIONS`.

### Step 3.3 — Deliberately break the wiring (30 min)

Now, one at a time, comment out each of the three pieces and run it:

- Remove the `TOOLS` schema entry → the model doesn't know the tool exists. What does it do instead?
- Remove the `TOOL_FUNCTIONS` entry → the model calls it, your code crashes. What's the traceback?
- Rename the Python function but not the schema → same as above, different line.

**This is the exercise.** You now recognise all three failure modes by sight.

### Step 3.4 — Make the loop survive a crashing tool (1h)

Right now, if a tool raises an exception, the whole program dies. Real agents
can't do that. Wrap the tool call:

```python
try:
    result = TOOL_FUNCTIONS[block.name](block.input)
except Exception as e:
    result = {"error": f"Tool failed: {type(e).__name__}: {e}"}
```

Then test it: make `delete_event` raise on purpose and watch the model *recover*
— it reads the error text and tries something else. That recovery is why you
return errors as tool results instead of crashing.

Also add a loop cap so it can't spin forever:

```python
MAX_TURNS = 10
```



### Step 3.5 — Commit and write it down (30 min)

```bash
git add -A && git commit -m "Week 1: delete_event tool, error handling, loop cap"
```

In `retro.md`, answer in your own words: **what exactly goes over the wire on a
tool call, and what comes back?** If you can't write it, that's the question to
bring me.

---



## Week 1 checkpoint

You're done when all of these are true:

- [x] `uv run jadwal_week1.py` works from a clean terminal
- [ ] You added `delete_event` yourself and it works end to end
- [ ] A crashing tool no longer kills the program
- [ ] You can name the three places a tool lives, without looking
- [ ] You can explain `stop_reason == "tool_use"` out loud
- [ ] `.env` is not in git

---



# WEEK 2 — Medium detail

**Theme:** structured output and making the agent trustworthy.

- **Session 1:** Force JSON output. Instead of the model saying "I'll book that
for 3pm", make it return a strict event object you can validate. Add `pydantic`
and validate every tool's arguments before running it.
- **Session 2:** Fix the guessing problem from Week 1. Rewrite `SYSTEM_PROMPT`
with 3–5 few-shot examples of Indonesian phrases → correct behaviour, including
one example where the correct behaviour is *asking a clarifying question*.
- **Weekend:** Vision input. Pass a screenshot of a meeting invite and have it
extract the event. This is the exact skill Phase 6's invoice work needs.

**Checkpoint:** it never invents a date it wasn't given, and you have a
`parse_event()` that returns validated Pydantic objects.

---



# WEEKS 3–4 — Medium detail

**Theme:** real data, real queries. The fake calendar becomes SQLite.

- **Week 3:** SQLite schema (`title, start, end, tz, attendees, notes`).
Rewrite the three tools to hit the DB. Learn `EXPLAIN`, indexes on `start`.
Add `find_free_slot(duration, after, before)` — pure gap-finding, no RRULE.
- **Week 4:** Conflict detection as a real query, not a Python loop. Ask it hard
questions: *"kapan saya bisa ketemu 2 jam minggu ini?"* Token budgeting — print
the cumulative cost of a long conversation and decide what to drop.

**Checkpoint:** it answers correctly about data that was never in the prompt —
it had to go and fetch it.

---



# WEEK 5 — n8n, deliberately

Now you learn n8n, with the one thing that makes it worth learning properly:
**you already know what it's doing.**

- Install n8n locally (Docker).
- Rebuild Jadwal in n8n using the AI Agent node + a Google Calendar node.
- Find, in the n8n UI, each piece you wrote by hand: where's the loop? where are
the tool schemas? where's the conversation history? where's `stop_reason`?
- Write one page in `retro.md`: **what n8n saved you, and what it hid.**
Specifically: when the agent gets it wrong in n8n, how do you find out why?

**Checkpoint:** you can say, with specifics, which parts of your future work
belong in n8n and which belong in code.

---



# WEEKS 6–13 — Outline

Updated 2026-09-18: Weeks 5-6 (MCP + OAuth) compressed to Week 5 alone, and
**Phase 6's target system corrected — not Odoo.** The company runs a
**custom, in-house, Postgres-backed system**, not Odoo. This is better news
than it sounds: no third-party ERP API/ORM quirks to learn on top of
everything else, and it plays directly to Johanes's existing SQL depth. The
tradeoff: no pre-built open-source MCP server to reference for this one —
Step 5.9's Odoo-MCP-reading exercise becomes general pattern research only,
not something to adapt line-by-line.

- **6–7** Evals — 25 real phrases, expected JSON, a score you run before and
  after every prompt change
- **8–9** Ship — FastAPI (already proven, `jadwal_api.py`), background jobs,
  observability, cost tracking, Docker, VPS deploy, Telegram-first then
  WhatsApp front end
- **10–11** Company pilot: pick one narrow, real process against the
  in-house Postgres system (originally scoped as invoice processing in the
  source plan — confirm this still matches, or pick the actual
  highest-hours-bleeding process once we're there). Build purpose-built
  tools with real validation gates (same pattern as `EventCreate`), not
  raw/generic DB access. Dev/staging copy only, never production directly.
  Two weeks running in parallel with the human process, compared daily.

We'll expand each of these into Week-1-level detail when you get there — no
point writing it now, since what you struggle with in weeks 1–5 changes what
weeks 6+ should emphasise, and Phase 6's exact process/schema needs
confirming closer to the time regardless.

---



## How to use me during this

Bring me:

- Your `retro.md` every Friday
- Any error message, pasted whole
- "I don't understand why X" — especially about code you wrote yourself
- "Is this the right way to do X?" before you build it, not after

Don't bring me:

- Things you haven't tried running yet
- "Write the whole thing for me" — the typing is the learning in weeks 1–4

The one rule that matters: **ship something small every week, even if it's ugly.**