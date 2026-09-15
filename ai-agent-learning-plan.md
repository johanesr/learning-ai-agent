# From AI User → AI Engineer: A 12-Week Plan

**Assumptions:** ~8 hours/week (two weekday evenings + one weekend block). Python basics present, backend in progress. Adjust the calendar, not the order — the sequence matters more than the pace.

**The goal at the end of 12 weeks:** you can take a repetitive process in your business, wrap it in an agent that uses real tools against real data, measure whether it actually works, deploy it, and keep it running without it quietly breaking.

---

## The core idea

Everything below is built on one pattern:

```
loop:
    response = model(conversation, tools)
    if response wants a tool:
        result = your_code(tool_name, tool_args)
        conversation.append(result)
    else:
        done
```

That's an agent. The intelligence is in the model. **The engineering is in everything around it** — the tools you expose, the context you feed it, the guardrails on what it can destroy, and the evals that tell you whether it works. That surrounding work is backend engineering. This is why your two goals are actually one goal.

---

## One project, grown over 12 weeks

Don't do twelve disconnected exercises. Build **one thing** and keep adding to it.

### The project: "Jadwal" — a natural-language scheduling assistant

You type (or eventually speak) something like "besok sore ketemu vendor jam 3, 1 jam" and it proposes a structured calendar event, confirms with you, then writes it to Google Calendar.

**Why this one:**
- It has a **clear success condition** — you know the exact event JSON you expect, so evals write themselves
- It touches a **real external API with real consequences** — you learn OAuth, timezones, and write-safety early, which every future agent needs
- It's **low-risk once gated** — a confirm-before-write step means a bad parse costs you a click, not a real mess
- It's something you'll **actually use every day**, so you'll notice when it's wrong

**Two things to get right from the start:**
- **Timezone-aware from line one.** Asia/Jakarta, UTC+7, everywhere. An assistant that books an hour off is worse than no assistant.
- **Confirm before write, always.** The agent proposes the parsed event (title, start, end, tz); you approve; only then does it call the API. This isn't training wheels — keep this gate permanently, even in the finished version.

**How it grows:**

| Phase | What it becomes |
|---|---|
| Weeks 1–2 | CLI script against a fake calendar (a Python dict or local SQLite table shaped like a Google event). Text in, structured event out. |
| Weeks 3–4 | Real logic: free-slot finding, conflict detection, reading back existing events to reason about them. |
| Weeks 5–6 | Swap the fake calendar for the real Google Calendar API (OAuth, refresh tokens) behind an MCP server. |
| Weeks 7–8 | Has an eval suite: ~25 phrases you'd actually type, each with the exact event JSON expected. You know its accuracy as a number. |
| Weeks 9–10 | Small FastAPI service (or a Telegram/WhatsApp front end), deployed, logged, cost-tracked. |
| Weeks 11–12 | Runs for real, daily, on your own calendar — the pilot. The *company* pilot in Phase 6 targets a separate business process (see note there). |

---

## Phase 0 — Setup (Week 0, ~3 hours)

- Python 3.12+, `uv` for environments and packaging
- API key (Anthropic and/or OpenAI), stored in `.env`, **never** committed
- Git repo from day one. Commit every session.
- A running Odoo dev instance via Docker — you'll need it by Week 11, get it working now while there's no pressure

**Checkpoint:** you can run a script that sends one message to a model and prints the reply.

---

## Phase 1 — The loop, from scratch (Weeks 1–2)

No frameworks. This is deliberate and non-negotiable.

**Learn:**
- Tool use / function calling: how you describe a tool via JSON schema, how the model returns a tool-call block, how you return the result
- Multi-turn conversation state — the model is stateless, *you* hold the history
- Structured output: getting reliable JSON back instead of prose
- Vision input: passing a PDF page or image as base64

**Build:**
- The agent loop in one file, under 150 lines
- Three tools against a **fake** calendar (dict or SQLite, not the real API yet): `list_events(start, end)`, `find_free_slot(duration, constraints)`, `create_event(title, start, end, tz)`
- Handle: model returns malformed JSON, tool raises an exception, loop runs forever, ambiguous dates ("next Friday") get resolved and echoed back before anything is written

**Checkpoint:** you can explain, without notes, exactly what bytes go over the wire on a tool call and what comes back.

---

## Phase 2 — Context engineering (Weeks 3–4)

The highest-leverage skill, and the most underrated. What you put in the context window determines output quality far more than how you phrase the request.

**Learn:**
- Prompt structure: role, constraints, examples, output format. Few-shot with 3–5 real examples beats paragraphs of instruction.
- **Structured retrieval before vector search.** For business data, a SQL query is usually better than embeddings. Don't reach for a vector DB yet.
- Token budgeting: what a long conversation costs, and what to drop
- Schema design: how you model an invoice determines how well the agent can reason about it

**Build:**
- SQLite schema for events (title, start, end, tz, attendees, notes)
- Conflict detection: does this new event overlap something that exists?
- Recurring "next available slot" logic — skip RRULE for now, just gap-finding between existing events
- Ask it real questions: "what's my Tuesday afternoon looking like?"

**Checkpoint:** it answers questions correctly about data it never saw in the prompt — it had to go get it.

**Parallel backend track:** SQL properly. Joins, indexes, transactions, `EXPLAIN`. Non-optional for what comes later.

---

## Phase 3 — MCP (Weeks 5–6)

Model Context Protocol is the standard interface between models and your tools. Learn it because it's where your ERP work and your AI work converge.

**Learn:**
- MCP architecture: server exposes tools/resources, client (Claude Desktop, Cursor, your own code) consumes them
- Build a server with the Python SDK — it's mostly decorators over functions you already wrote
- Transport: stdio for local, HTTP for remote
- **Auth and permission scoping** — which models can be touched, which operations are allowed

**Build:**
- Refactor Phase 2's tools into an MCP server
- Swap the fake calendar for the real Google Calendar API: OAuth consent screen, scopes, refresh token storage
- Connect it to Claude Desktop. Talk to your real calendar in plain language, read-only first.
- Separately: read the source of an existing open-source Odoo MCP server (don't run it against anything real yet) — you'll use this pattern in Phase 6

**Checkpoint:** someone else could install your MCP server from your README and have it work.

**Parallel backend track:** HTTP properly. Status codes, idempotency, retries with backoff, timeouts.

---

## Phase 4 — Evals and reliability (Weeks 7–8)

This is the phase most people skip, and it's the one that separates a demo from something you'd let near a client's books.

**Learn:**
- Building an eval set: 20–30 real inputs with known-correct outputs
- Metrics that mean something: field-level extraction accuracy, not vibes
- Regression testing — did last week's prompt change break anything?
- Failure taxonomy: hallucinated fields, wrong tool chosen, silent partial success (the dangerous one)
- **Human-in-the-loop on anything irreversible.** Write operations get an approval gate. Always.

**Build:**
- `evals/` directory: 25 real phrases you'd actually type ("besok sore ketemu vendor jam 3, 1 jam") + the exact expected event JSON
- A script that runs the whole set and prints a score
- Run it before and after every prompt change

**Checkpoint:** you can state your agent's accuracy as a number, and explain its three most common failure modes.

---

## Phase 5 — Ship it (Weeks 9–10)

**Learn:**
- FastAPI: endpoints, Pydantic validation, async, dependency injection
- Background jobs — agent runs take 30+ seconds, they don't belong in a request cycle
- Observability: log every tool call, every token count, every cost. You cannot debug an agent you cannot see.
- Cost control: model selection per task (cheap model for extraction, strong model for reasoning), caching, context trimming
- Deploy: Docker, one small VPS, environment secrets

**Build:**
- `POST /schedule` (or a small Telegram/WhatsApp bot front end) → parsed → confirmed → written to Calendar
- A trace view: for any run, see every step the agent took
- A daily cost report emailed to yourself

**Checkpoint:** it's running on a server, you can see what it did yesterday, and you know what it cost.

**Parallel backend track:** this *is* the backend track. Queues, workers, idempotency, observability — same skills, real stakes.

---

## Phase 6 — The company pilot (Weeks 11–12)

**Note:** your learning project (Jadwal, the scheduling assistant) doesn't map onto a company process by itself — it's a personal tool. That's fine; its job was to teach you the loop, MCP, auth, and evals in a low-stakes setting. For Phase 6, apply those same skills to a *different* target: the highest-hours-bleeding repetitive process in your PT — likely still document/invoice processing into Odoo, per the original plan. You're not starting from zero; you're reusing the architecture (tool design, confirm-before-write gate, eval suite pattern), just pointed at new tools and new data.

Now, and only now, point it at the business.

**Rules for the pilot:**
1. **Pick one narrow process.** Not "automate accounting." Something like: vendor invoices arriving by email → extracted → draft bill created in Odoo → human approves.
2. **Dev Odoo instance first.** A restored copy of production. Never the live DB.
3. **Read-only until you trust it**, then writes as drafts, then writes with approval. Never silent writes.
4. **Measure against the manual process.** Time saved per document, error rate vs. your staff's error rate. If it's not clearly better, don't deploy it.
5. **Run in parallel for two weeks.** Human does the work, agent does it too, compare daily.

**Checkpoint:** one real process is measurably faster and no less accurate, and you have the numbers to show a client.

---

## Deliberately skipped

Things that will tempt you and waste your time at this stage:

- **Multi-agent orchestration.** Start single-agent. Simplicity scales better than complexity, and most "multi-agent" problems are actually one agent with better tools.
- **Vector databases / RAG.** For structured business data, SQL wins. Add embeddings only when you hit an actual problem they solve.
- **Framework-hopping.** LangGraph, CrewAI, and the rest are real tools, but evaluate them *after* Week 6, when you can judge what they're hiding. Many production teams skip heavy frameworks entirely.
- **Fine-tuning.** Almost never the answer. Fix the context first.
- **No-code agent builders.** Fine for a quick demo, dead end for the skill you're building.

---

## What the 12 weeks actually give you

| Skill | Where it showed up |
|---|---|
| Agent loop, tool design | Phase 1 |
| Context engineering, schema design | Phase 2 |
| MCP, API integration, auth scoping | Phase 3 |
| Evals, reliability engineering | Phase 4 |
| FastAPI, queues, observability, cost ops | Phase 5 |
| Deploying into a real business | Phase 6 |

That's a backend engineer's skillset and an AI engineer's skillset, learned as one thing, with a working product at the end.

---

## Weekly rhythm that makes this survivable

You run two companies. The plan fails if it depends on long uninterrupted blocks.

- **2 weekday evenings × 1.5h:** learning + small commits
- **1 weekend block × 4h:** the real build session
- **Friday, 15 minutes:** write down what broke this week and what you didn't understand. That list is your actual curriculum.

Ship something small every single week, even if it's ugly. Momentum beats perfection, and an agent you can run is worth ten tutorials you've read.
