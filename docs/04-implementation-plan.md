# IRCTC Agent â Implementation Plan (Python + Next.js)

**Project:** Build What Moves India hackathon submission
**Owner:** Shantam (solo)
**Deadline:** 28 August 2026, 8:00 PM IST â **5 days**
**Supersedes:** the earlier Next.js-only plan
**Companion docs:** `01-research-context-log.md` Â· `02-build-plan.md` Â· `03-product-design-document.md`

> **How to use this.** Paste one task at a time into Claude Code. Keep all four docs in `/docs` so they can be read directly. Do not paste a whole day at once.

---

## 0. Two things that changed

### â The Codex/OpenAI requirement is now satisfied
The brief requires the prototype to be **built with Codex or powered by an OpenAI model**. Buying API credits closes this cleanly â the agent runs on OpenAI, so the requirement is met on the "powered by" clause. If you also drive part of the build with the Codex CLI, you satisfy both clauses and get a stronger answer for minute two of the video. This was the largest open risk in the submission and it's now closed.

### â Positioning correction (carried forward â read if you haven't)
**AskDISHA**, IRCTC's conversational assistant, has existed since 2018 and already does conversational booking, PNR lookup, cancellation, refund status, and confirmation probability, in English/Hindi/Hinglish, at ~150k queries/day. **RailOne** consolidated five apps in July 2025.

| Feature | Novel? | Role |
|---|---|---|
| Conversational booking | â | Table stakes |
| Confirmation probability | â | Supporting |
| **Proactive alerts on state change** | â | **The product** |
| **TDR detection, deadline, filing** | â | **Flagship** |
| **Connected-journey reasoning** | â | **Standout** |
| **Cross-system gating** | â | Depth |

Pitch: *"IRCTC has had a conversational booking bot since 2018. It has never once spoken first."*

---

## 1. Persistence â the design

Reference data, conversation history and journey state have different needs. Treating them as one decision was the mistake in the first draft of this plan.

| Data | Store | Why |
|---|---|---|
| **Reference data** â stations, trains, schedules, waitlist model, catering, retiring rooms, TDR rules | **JSON, loaded at startup** | Read-only. Version-controlled, hand-editable, diffable in a PR. A database buys nothing. |
| **Conversation history** | **Agents SDK Sessions** | The framework handles it. Not your code. |
| **Journey state** â JourneyPlan, PNRs, passengers, TDR claims, fired alerts, clock offset | **Postgres via SQLAlchemy** | Survives refresh, container restarts and redeploys. |

### â Postgres, â Alembic â these are separate decisions

The cost that made migrations look unattractive is **schema churn**: your domain model will move fifteen or twenty times this week as the TDR rules and `JourneyPlan` shape settle, and each move would become edit â autogenerate â review diff â apply. That is friction at exactly the wrong moment.

But that cost belongs to Alembic, not to Postgres.

- **Skip Alembic.** You are not preserving data across schema changes during development. Use `Base.metadata.create_all()`, and drop-and-recreate when the model changes. Alembic solves a problem you do not have this week.
- **Take Postgres.** On Railway it is one click in the same project, with `DATABASE_URL` injected as an environment variable. Roughly two hours all-in with SQLAlchemy models.

**What Postgres actually buys here:** durability across restarts. You will redeploy constantly over five days, and free-tier containers spin down on idle. Without a store, every redeploy silently wipes any session a reviewer or mentor had open â and you would lose your own test state on every push.

**Note for the write-up:** the ORM models *are* your schema definition â `create_all()` does the job a migration would. What you give up is versioning, reversibility, and incremental diffs against existing data, none of which matter when you're free to drop and recreate. Frame this in the video as a deliberate POC choice, not an omission.

### Session identity and rehydration

Storage alone does not survive a page refresh. Two pieces are required:

1. **Session ID in an HTTP-only cookie**, issued on first request.
2. **`GET /api/session`** â returns the full journey state and message history so the frontend can rebuild the thread on load.

Without the second, a refresh shows an empty chat even with Postgres behind it. Build both on Day 1.

### Session isolation â independent of storage

Your public link will be opened by several reviewers at once. Every row is keyed by `session_id`, and **the simulated clock is per-session too** â one reviewer jumping to `Delay 3h+` must not affect anyone else. This is a correctness requirement regardless of storage engine, and it is the single bug most likely to silently ruin Stage 1 review.

### Nothing lives in the browser

The frontend holds rendered messages and nothing else. No journey state, no PNRs, no deadlines, no refund amounts in React state or `localStorage`. Every figure the UI displays came from a backend response in that session.

### The scale answer, for the API surface page

> Journey state is a `journeys` table keyed by PNR and session. In production the alert engine would read from it on a scheduled tick rather than on request, so alerts fire whether or not the user has the app open. The domain layer is pure and takes state as an argument, so that change touches no business logic.

## 2. Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | **FastAPI + Python 3.12** | Where your agent/MCP experience lives |
| Agent framework | **OpenAI Agents SDK (`openai-agents`)** | Function tools with auto schema generation, Sessions, semantic streaming events, built-in MCP tool calling, tracing. Uses the Responses API by default. |
| Validation | **Pydantic v2** | The SDK derives tool schemas from Pydantic models |
| Reference data | **JSON in `/data`**, loaded once at startup | Read-only |
| Journey state | **Postgres + SQLAlchemy**, `create_all()`, no Alembic | See Â§1 |
| Conversation history | **Agents SDK Sessions** | Framework-managed |
| Streaming | **SSE via `StreamingResponse`**, fed by SDK stream events | Custom event protocol â see Â§4.3 |
| MCP | **MCP Python SDK targeting the 2026-07-28 spec** â stateless, Streamable HTTP | See Â§4.5. Verify the Agents SDK's MCP client supports this revision. |
| Frontend | **Next.js 15 + TypeScript + Tailwind** | |
| Frontend streaming | **`fetch` + `ReadableStream`, manual parse** | Don't fight the AI SDK's protocol across a language boundary |
| Backend deploy | **Railway or Render** | Always-on container â required, since in-memory state dies on serverless |
| Frontend deploy | **Vercel** | The public link you submit |

### â ï¸ Three constraints this stack imposes

**Provision Postgres alongside the backend.** Railway can host both in one project with `DATABASE_URL` injected automatically. Do this on Day 1 â not because the schema is ready, but because the connection plumbing should be proven before it's on the critical path.

**CORS costs you an hour.** Two origins, and requests must be credentialed so the session cookie travels. Get it working on Day 1 with a hello-world endpoint, not on Day 5.

**Cookie settings across origins.** The session cookie needs `SameSite=None; Secure` to cross from a Vercel frontend to a Railway backend, and the frontend must send `credentials: "include"`. This is a five-minute fix that costs two hours if you meet it on Day 5.

### On the Agents SDK

Verify the current API shape in the docs before Task 2.1 â the SDK moves quickly and this plan specifies intent, not exact call signatures. Two things to look up specifically: how `RunItemStreamEvent`s map onto your SSE event types, and which Session backend to use so history lands in the same Postgres instance as journey state.

**Why not LangGraph**, despite your experience with it: this architecture deliberately keeps the state machine and alert engine *outside* the agent. LangGraph's graph state would sit alongside `engine/state.py` as a second overlapping notion of state. Single agent, ~16 tools, no handoffs, no branching control flow â the Agents SDK is the lighter fit, and being OpenAI-native reinforces the brief requirement.

---

## 3. Repo structure

Monorepo. Two deploy targets.

```
saarthi/
âââ docs/                          â all four planning docs
âââ backend/
â   âââ data/
â   â   âââ stations.json
â   â   âââ trains.json
â   â   âââ schedules.json         â haltMinutes per stop
â   â   âââ availability.json
â   â   âââ waitlist_model.json
â   â   âââ catering.json
â   â   âââ retiring_rooms.json
â   â   âââ tdr_rules.json
â   âââ app/
â   â   âââ main.py                FastAPI app, CORS, routers
â   â   âââ models.py              Pydantic domain models
â   â   âââ db.py                  SQLAlchemy engine, session, create_all
â   â   âââ tables.py              ORM tables â journeys, pnrs, passengers,
â   â   â                          tdr_claims, fired_alerts, clock_offsets
â   â   âââ store.py               repository fns â all keyed by session_id
â   â   âââ domain/                â PURE. No FastAPI, no OpenAI.
â   â   â   âââ stations.py        resolve, alias match, ambiguity
â   â   â   âââ search.py          direct + connecting routes
â   â   â   âââ availability.py
â   â   â   âââ waitlist.py        band + explanation
â   â   â   âââ booking.py
â   â   â   âââ journey.py         JourneyPlan â the key entity
â   â   â   âââ live.py            delay simulation, platform
â   â   â   âââ catering.py        halt-window filtering
â   â   â   âââ retiring.py        eligibility gating
â   â   â   âââ tdr.py             eligibility, deadlines, codes
â   â   â   âââ refund.py          cancellation charges, math
â   â   âââ engine/
â   â   â   âââ clock.py           simulated time
â   â   â   âââ state.py           journey state machine
â   â   â   âââ alerts.py          deterministic trigger rules
â   â   âââ agent/
â   â   â   âââ tools.py           @function_tool wrappers over domain
â   â   â   âââ prompt.py          agent instructions
â   â   â   âââ runner.py          Agent + Runner, stream events â SSE
â   â   âââ mcp_server.py
â   â   âââ routers/
â   â       âââ chat.py            POST /api/chat     (SSE)
â   â       âââ session.py         GET  /api/session  (rehydration)
â   â       âââ clock.py           POST /api/clock
â   â       âââ surface.py         GET  /api/surface
â   âââ tests/
â       âââ test_waitlist.py
â       âââ test_search.py
â       âââ test_tdr.py
âââ frontend/
    âââ app/
    â   âââ page.tsx
    â   âââ api-surface/page.tsx
    âââ components/
    â   âââ Thread.tsx
    â   âââ AgentMessage.tsx
    â   âââ AlertMessage.tsx
    â   âââ OptionCard.tsx
    â   âââ DecisionBlock.tsx      â the Flow H component
    â   âââ JourneyCard.tsx
    â   âââ CountdownChip.tsx
    â   âââ PaymentSheet.tsx
    â   âââ DemoControls.tsx
    â   âââ HonestyPanel.tsx
    âââ lib/
        âââ stream.ts              SSE parser
        âââ types.ts               mirrors backend Pydantic models
```

**Hard rule:** `app/domain/` is pure Python. It imports no FastAPI, no OpenAI, no HTTP. Everything else calls into it. This is what makes the MCP server a two-hour job instead of a rewrite, and it's the architecture point you make in the video.

---

## 4. Three architectural decisions to get right on Day 1

### 4.1 The simulated clock

```python
# app/engine/clock.py â the ONLY source of "now" in the application
def now(session_id: str) -> datetime: ...
def jump_to(session_id: str, state: DemoState) -> None: ...
def reset(session_id: str) -> None: ...
```

**Per-session, and persisted.** The offset lives in the `clock_offsets` table keyed by `session_id`, so a reviewer who jumps to `Delay 3h+` and then refreshes is still in the delayed state â and no other reviewer is affected. Nothing anywhere else may call `datetime.now()` for current time. Retrofitting this on Day 3 means touching every module.

### 4.2 Alerts are deterministic; the LLM only phrases

```
clock change / demo jump
   â state.py recomputes journey state
   â alerts.py evaluates rules â list[Alert]
   â ðµ/ð¡ alerts render from templates, NO model call
   â ð´ alerts needing reasoning pass payload to the model,
     which composes the recommendation from figures it was GIVEN
```

The model never computes a deadline or a rupee amount. This is both a correctness requirement â a hallucinated refund deadline destroys the flagship feature â and the best answer available if a judge asks how you keep the model honest about money.

### 4.3 The streaming contract

Define this once, on Day 1, and don't change it. Newline-delimited JSON over SSE:

```
data: {"type":"token","content":"Your Nagpur train is "}
data: {"type":"tool_call","name":"check_tdr_eligibility"}
data: {"type":"component","component":"DecisionBlock","props":{...}}
data: {"type":"alert","severity":"critical","props":{...}}
data: {"type":"done"}
```

The `component` event is what lets the backend drive rich UI â OptionCard, DecisionBlock, PaymentSheet â rather than the frontend parsing prose. Get this contract fixed before either side is built, or you'll spend Day 3 reconciling two half-finished protocols.

### 4.4 Rehydration

`GET /api/session` returns everything needed to rebuild the page from cold:

```json
{
  "session_id": "...",
  "messages": [ ... ],          // including past component and alert payloads
  "journey": { ... },           // JourneyPlan or null
  "state": "PRE_DEPARTURE",
  "clock_offset_seconds": 11400,
  "active_deadlines": [ ... ]   // so countdowns resume correctly
}
```

The frontend calls this on mount, before any user input. **Persisted component and alert payloads matter** â a refresh mid-demo must restore the DecisionBlock, not just the prose around it. Store each emitted component event alongside the message that carried it.

Deadlines are returned as absolute timestamps, never as remaining seconds, so a countdown resumes accurately after a refresh rather than restarting.

### 4.5 MCP is stateless â target the 2026-07-28 spec

â ï¸ **The MCP specification changed substantially on 28 July 2026.** Anything written against the older model is out of date. Target the current revision.

**What changed:**

| Removed | Replaced by |
|---|---|
| `initialize` / `notifications/initialized` handshake | Protocol version and client capabilities travel in `_meta` on every request |
| `Mcp-Session-Id` header, protocol-level sessions | **Explicit, server-minted handles passed as ordinary tool arguments** (SEP-2567) |
| SSE stream resumability, `Last-Event-ID` | Broken stream â client re-issues as a new request with a new request ID |
| Per-connection list variance | `tools/list` deterministic order, with required `ttlMs` and `cacheScope` |

Also now required on Streamable HTTP POSTs: `Mcp-Method`, plus `Mcp-Name` on calls that target something (`tools/call`, `resources/read`, `prompts/get`), and `MCP-Protocol-Version` matching the value in `_meta`. A server that processes the body must reject a header disagreeing with it â 400, JSON-RPC error `-32020` HeaderMismatch.

**What this means for us â and it's good news.**

MCP never holds application state, and the spec now says so explicitly. Session state, conversation history and journey state live in **our Postgres**, exactly as designed in Â§1. The MCP server is a stateless facade over `app/domain`.

Our `session_id` becomes a **server-minted handle passed as an ordinary tool argument** â which is precisely the pattern SEP-2567 prescribes. We are not working around the protocol; we are building the sanctioned shape.

**Implementation notes:**
- Every MCP tool takes `session_id` as an explicit parameter. No ambient state, no connection affinity.
- The server must be safe to run behind a round-robin load balancer with no sticky sessions. Since all state is in Postgres, it already is.
- Return `tools/list` in deterministic order with `ttlMs` and `cacheScope` set.
- Do not use the legacy HTTP+SSE transport. It's deprecated.

**Worth one line in the video:** *"The MCP server is stateless, per the July 2026 spec â session identity is an explicit server-minted handle, not transport state. All journey state lives in Postgres, so the server scales behind an ordinary load balancer."*

**Roadmap line, don't build:** MRTR (Multi Round-Trip Requests) â a server returns `resultType: "input_required"` with the questions it needs answered, and the client retries with `inputResponses` attached. That is the clean protocol-level way to do our station-disambiguation turn. Mention it; don't implement it this week.

---

## 5. Day-by-day

### DAY 1 â Foundation and the seam

**Goal:** both services running, talking to each other, deployed once, domain layer callable.

#### Task 1.1 â Scaffold both services

```
Create a monorepo with /backend and /frontend.

Backend: FastAPI + Python 3.12, uv, Pydantic v2, pytest, SQLAlchemy,
psycopg, and the OpenAI Agents SDK (`openai-agents`).
Folder structure exactly per docs/04-implementation-plan.md section 3.
Create module stubs with correct signatures so imports resolve.
Configure CORS for the frontend origin with allow_credentials=True.
Add GET /api/health.

Session identity: middleware that reads a session_id cookie, issuing one if
absent. Cookie must be HttpOnly, Secure, SameSite=None so it crosses from the
Vercel frontend to the Railway backend. Frontend fetches must use
credentials: "include".

Frontend: Next.js 15 App Router, TypeScript, Tailwind.
Configure Tailwind with the design tokens from
docs/03-product-design-document.md section 11 as CSS custom properties:
surface, raised, ink, ink-dim, signal-go, signal-wait, signal-stop, rail.
JetBrains Mono with tabular numerals for figures, Inter for body.
Dark theme only.

Add a page that calls /api/health and renders the result, to prove the seam works.
```

#### Task 1.2 â Deploy both plus Postgres, today

```
Deploy the backend to Railway as a container, and provision a Postgres instance
in the same Railway project so DATABASE_URL is injected automatically.
Deploy the frontend to Vercel.

Implement app/db.py: SQLAlchemy engine from DATABASE_URL, a session factory,
and an init_db() that calls Base.metadata.create_all() on startup.
Do NOT add Alembic. Drop and recreate when the schema changes.

Verify end to end:
- the deployed frontend reaches /api/health with CORS and credentials working
- the session_id cookie is set and persists across a page refresh
- the backend can read and write a trivial row in Postgres

This must all work on Day 1. Every one of these is a two-hour problem if first
encountered on Day 5.
```

#### Task 1.3 â Mock data

```
Read docs/03-product-design-document.md section 12 for the data model.

Generate seed JSON in backend/data for this journey:
Bengaluru (SBC) â Nagpur (NGP) â Varanasi (BSB), 4 September.

- stations.json: ~40 real Indian stations, codes, names, city, aliases.
  Include all four Bengaluru long-distance stations (SBC, YPR, KJM, BNC) so the
  disambiguation flow in PDD Flow A1 works.
- trains.json + schedules.json: ~15 trains, at least 3 on each leg. Schedules
  MUST carry realistic haltMinutes per stop (2-10 typical, 15-20 at junctions).
  The catering feature depends on this being real data.
- availability.json: 12295 Sanghamitra SBCâNGP must show SL at GNWL/18 so it
  lands in the Probable band.
- waitlist_model.json: per train/class/quota, clearance ceiling and seasonal
  modifier, calibrated so GNWL clears well, RLWL poorly, TQWL worst â matching
  docs/01-research-context-log.md section 4.
- catering.json: vendors per station with cutoff_minutes.
- retiring_rooms.json: Nagpur available; non-AC double ~â¹520/12h, AC ~â¹1150/12h.
- tdr_rules.json: reason codes with label, deadline rule, refund basis, whether
  a TTE certificate is needed. Source from research log section 5.

Use real train numbers and names where known. Add a header comment in each file
stating all availability and timing data is synthetic.
```

#### Task 1.4 â Clock, store, domain core

```
Implement app/engine/clock.py, app/store.py, and the first domain modules.

tables.py: SQLAlchemy ORM tables â journeys, pnrs, passengers, tdr_claims,
fired_alerts, messages, clock_offsets. EVERY table has a session_id column
and every query filters on it. No cross-session reads, ever.

clock.py: per-session simulated time, offset persisted in clock_offsets.
now(session_id), jump_to(session_id, state), reset(session_id).
DemoState = chart | boarding_day | delay_1h | delay_3h | cancelled.
This is the ONLY source of current time in the app.

store.py: repository functions over the ORM â get_journey(session_id),
save_journey(...), append_message(...), record_alert(...), etc. The domain
layer never touches the ORM; it receives plain Pydantic models.

domain/stations.py: fuzzy resolve, alias match, ambiguity detection.
domain/search.py: direct routes AND connecting routes via an interchange,
returning a JourneyPlan with legs, interchange, layover_minutes.
domain/waitlist.py: returns band ('confirm'|'probable'|'low'), probability
range, and a plain-language explanation naming waitlist type, position and
seasonal factor. Thresholds >70 / 30-70 / <30. RAC counts as confirmed.

Pure Python. No FastAPI imports, no OpenAI imports.

Write pytest tests for waitlist and search â these two carry the most logic.
```

**End of Day 1:** two deployed services talking to each other, seed data in place, tests passing on the two hardest domain modules.

---

### DAY 2 â Agent and booking

#### Task 2.1 â Streaming contract and Agents SDK runner

```
FIRST: read the current OpenAI Agents SDK docs at
https://openai.github.io/openai-agents-python/ â specifically the streaming and
sessions pages. This plan specifies intent, not exact call signatures, and the
SDK changes quickly. Confirm the current shape before writing code.

Implement the SSE contract from docs/04-implementation-plan.md section 4.3
exactly, in both backend/app/routers/chat.py and frontend/lib/stream.ts.

Backend: POST /api/chat returns StreamingResponse emitting newline-delimited
JSON events: token, tool_call, component, alert, done.

app/agent/runner.py: construct an Agent with instructions and tools, run it
via Runner with streaming, and map the SDK's stream events onto our SSE event
types â raw token deltas to `token`, RunItemStreamEvent tool_called to
`tool_call`.

Sessions: use the SDK's session support for conversation history, backed by the
same Postgres instance rather than a separate SQLite file. Journey state stays
in our own tables â do not conflate the two.

Persist every emitted component and alert payload alongside its message, so
GET /api/session can restore them on refresh.
```

#### Task 2.1b â Rehydration

```
Implement GET /api/session per docs/04-implementation-plan.md section 4.4.

Returns session_id, messages (including stored component and alert payloads),
journey, derived state, clock_offset_seconds, and active_deadlines as ABSOLUTE
timestamps so countdowns resume accurately rather than restarting.

Frontend calls this on mount, before accepting input, and rebuilds the thread â
including any DecisionBlock or alert that was on screen before the refresh.

Test explicitly: book a journey, jump to Delay 3h+, hard-refresh the page. The
decision block and the running countdown must both come back.
```

#### Task 2.2 â Tools

```
Implement app/agent/tools.py using the Agents SDK's @function_tool decorator,
which generates the schema from type hints and Pydantic models automatically.
Each tool is a thin function that calls into app/domain.

Every tool takes session_id from context and passes it through to the store â
no tool may read or write another session's data.

Tools: search_trains, check_availability, get_confirmation_probability,
plan_journey, add_passengers, create_booking, get_pnr_status, get_live_status,
get_halt_schedule, get_catering_options, get_retiring_room_availability,
book_retiring_room, check_tdr_eligibility, file_tdr, get_refund_status,
cancel_ticket.

No business logic in this layer. Validate, delegate, return structured JSON.
```

#### Task 2.3 â System prompt

```
Write app/agent/prompt.py.

Encode docs/03-product-design-document.md sections 3 and 5. The voice table in
5.1 and the four-part turn structure in 5.2 are binding.

Must include:
- Never render a form. Collect passenger details conversationally.
- Always state figures: â¹ amounts, minutes, positions, percentages.
- Never present options without an attached recommendation.
- Explain a rule in at most one clause, then move on.
- Mirror the user's language (English / Hinglish / Hindi). Never announce
  language support.
- Never claim to be official or affiliated with Indian Railways.
- One emoji maximum per message, only as a severity marker.
- Deadlines and money figures come ONLY from tool results. Never compute or
  estimate one.

That last rule is load-bearing.
```

#### Task 2.4 â Chat UI and booking flow

```
Build Thread, AgentMessage, OptionCard, and the empty state from PDD Flow A
("Where are you going?" with a worked example).

Layout per PDD section 11: single column, max 520px, agent left on --raised,
user right with no bubble fill.

Then complete PDD Flows A, B, C end to end: search â disambiguation â options
with waitlist bands â conversational passenger entry â mock payment â PNR.

Include the senior-citizen lower-berth detection from Flow C (age >= 60).
PaymentSheet: mock UPI QR, "Simulate payment", permanent "Demo payment â no
money moves" label.
```

**End of Day 2:** â Stages 1â2 done. Already submittable.

---

### DAY 3 â The proactive engine

#### Task 3.1 â State machine

```
Implement app/engine/state.py per the diagram in PDD section 8.

Enforce every gate in the gate table: retiring room requires CNF/RAC; TDR
requires delay >= 3h or cancellation; catering requires remaining time >
cutoff; auto-refund cases suppress the TDR offer entirely.

State is derived from JourneyPlan + session clock. Never stored independently.
Recompute on every clock change.
```

#### Task 3.2 â Alert engine

```
Implement app/engine/alerts.py.

Implement all 11 triggers from PDD Flow D (D1-D11) as rules:
{id, condition(state, clock), severity, template, action, requires_reasoning}.

Rules:
- Deterministic. The model never decides whether to alert.
- ðµ/ð¡ render from templates with no model call.
- requires_reasoning=True alerts pass their payload to the model to compose a
  recommendation (D8 / Flow H).
- Never two alerts consecutively without user input â batch.
- Every ð´ alert carries a live countdown.
- Deduplicate: fire once per journey unless the underlying value changes
  materially.
```

#### Task 3.3 â Demo controls

```
Build POST /api/clock and components/DemoControls.tsx per PDD section 7.

Collapsed strip labelled "Demo controls", expanding to: Chart prepared /
Boarding day / Delay 1h / Delay 3h+ / Cancelled / Reset journey.

Mark "Delay 3h+" as recommended with a subtle star â a reviewer with 90 seconds
must find the flagship moment unprompted.

Clicking advances that session's clock, recomputes state, evaluates alerts, and
pushes fired alerts into the thread via the SSE stream.
```

#### Task 3.4 â Alert UI

```
Build AlertMessage and CountdownChip.

AlertMessage: full width, 3px left border in the severity colour, visually
distinct from ordinary replies.
CountdownChip: live tick, tabular mono numerals so it doesn't jitter. ð´ only.

Respect prefers-reduced-motion. The only motion in the app is the countdown and
a ~200ms fade on the decision block.
```

**End of Day 3:** â Stage 3 done. **The money shot works. Strong submission exists from here.**

---

### DAY 4 â TDR and the broken connection

#### Task 4.1 â TDR domain logic

```
Implement app/domain/tdr.py and app/domain/refund.py.

Source every rule from docs/01-research-context-log.md section 5:
- eligibility per reason code
- deadline computation (delay >3h = before actual departure; downgrade = within
  3h of actual departure; general = 72h from scheduled arrival)
- correct reason code selection
- the NOT-eligible cases: fully cancelled trains and unconfirmed waitlist
  tickets auto-refund, so the agent says "you don't need to file anything"
- refund math including cancellation charges

Module docstring must note that sources disagree on some windows and this
implements one consistent set. That honesty carries into the UI.

pytest coverage on deadline computation specifically.
```

#### Task 4.2 â Single-leg TDR flow

```
Wire PDD Flow G: delay crosses 3h â ð´ alert â eligibility, amount, live
countdown â one-tap file â confirmation naming the reason code chosen â
tracking.

Also the "don't file" variant for cancelled trains.

"TDR â Ticket Deposit Receipt. Terrible name; it just means refund claim."
appears on first encounter.
```

#### Task 4.3 â Broken connection â­ flagship

```
Implement PDD Flow H. This is the submission's centrepiece.

When a delay makes a connection unmakeable, reason across four rule systems and
produce ONE recommendation:
  1. Leg 1 â TDR eligible, deadline before actual departure
  2. Leg 2 â NOT TDR eligible (IRCTC has no concept of a connected journey);
     ordinary cancellation charges, different deadline
  3. Retiring room â auto-cancels with the ticket, own refund rule
  4. Rebooking â is there a later leg-2 train, at what cost

Emit a DecisionBlock component event: two named options, each itemised with its
own deadline, then an explicit recommendation with reasoning.

Implement the "Explain the leg 2 rule" expansion. That text is the pitch
delivered inside the product â match the PDD wording closely.

The domain layer computes every amount and deadline. The model composes the
recommendation only. It never produces a figure.
```

#### Task 4.4 â DecisionBlock

```
Build components/DecisionBlock.tsx â the most designed element in the product.

Two option panels: name, itemised amounts, own deadline, bottom-line total.
Recommendation line beneath. Two primary buttons, one tertiary "Explain".

Legible at 360px with no horizontal scroll.
```

**End of Day 4:** â Stage 4 done.

---

### DAY 5 â Completion, honesty, deploy, video

#### Task 5.1 â Retiring room and catering

```
Implement PDD Flows E and F.

Catering: filter to ONLY vendors that can deliver within the halt window, and
show the count of hidden options. The filtering is the product.

Retiring room: strict eligibility gate. WL PNR â offer never appears; asking
returns the "needs a confirmed or RAC ticket" response from Flow F.
```

#### Task 5.2 â MCP server and API surface page

```
FIRST: read the current MCP spec at
https://modelcontextprotocol.io/specification/2026-07-28/ and its changelog.
The protocol changed substantially on 28 July 2026 â it is now stateless.
Do not write this from prior knowledge.

Implement backend/app/mcp_server.py as a STATELESS Streamable HTTP MCP server
exposing app/domain functions as tools. Thin wrapper â duplicate nothing.

Requirements per docs/04-implementation-plan.md section 4.5:
- No initialize handshake, no Mcp-Session-Id, no protocol-level session
- session_id is an explicit server-minted handle passed as an ordinary tool
  argument on every stateful tool (SEP-2567)
- Handle the required Mcp-Method / Mcp-Name / MCP-Protocol-Version headers,
  and reject header/body mismatch with 400 and JSON-RPC -32020
- tools/list returns deterministic order with ttlMs and cacheScope
- Must be safe behind a round-robin load balancer with no sticky sessions

Also check whether the Agents SDK's MCP client supports this revision; if it
lags, the MCP server still stands alone as the architectural artifact and the
agent can keep calling domain functions directly.

Build frontend/app/api-surface/page.tsx: a readable page listing every proposed
endpoint with signature and one-line purpose, headed by the framing from
docs/02-build-plan.md.

Include the persistence-boundary paragraph from section 1 of this plan â the
"in production this is a journeys table, the domain layer is pure so the swap
doesn't touch business logic" note. That paragraph is your scale answer.
```

#### Task 5.3 â Honesty panel and error states

```
Build HonestyPanel with the exact content from PDD section 10, opened from a
persistent quiet header element reading "Demo â synthetic data".

Implement every failure state in PDD section 9. Errors say what happened and
what to do. Never apologise, never vague.
```

#### Task 5.4 â Deploy and verify

```
Redeploy both services. Verify:
- frontend URL opens with no login wall, no access request
- works at 360px
- full path runs: book â Delay 3h+ â decision block â file â track
- OPENAI_API_KEY in backend env only, never committed, never in frontend
- two concurrent browser sessions do NOT share state (incognito + normal)
- hard refresh mid-demo restores the thread, the decision block AND the
  running countdown
- redeploy the backend mid-session, then refresh â state must survive
- no console errors on the happy path
```

**The last three are not optional.** Concurrency leakage would silently ruin Stage 1 review, and a refresh that empties the chat is the first thing a curious reviewer will trigger.

#### Task 5.5 â Submission assets (yours, not Claude Code's)

- **Video, 2:00 hard.** Minute 1: the journey as Shantam, ending on the broken-connection decision. Minute 2: the domain/engine/agent separation, why alerts are deterministic and only recommendations are model-composed, the MCP surface, real vs mocked, and your OpenAI/Codex usage.
- **Summary under 250 words.** Lead with the AskDISHA/RailOne positioning.
- **Test in incognito on a phone** before submitting.
- **Record early on Day 5.** More submissions die on the video than on the build.

---

## 6. Risk register

| Risk | Mitigation |
|---|---|
| Two-service split eats Day 1 | Deploy both on Day 1 with a health endpoint. CORS and the SSE contract are the only real seams â fix both before any feature work. |
| Concurrent reviewers share state | Every table keyed by `session_id`, per-session clock, from Day 1. Verify explicitly in Task 5.4. |
| Refresh empties the chat | `GET /api/session` rehydration built on Day 2, not retrofitted. Component and alert payloads persisted, deadlines stored absolute. |
| Redeploy wipes reviewer state | Postgres, provisioned Day 1. |
| Cross-origin cookie silently dropped | `SameSite=None; Secure` plus `credentials: "include"`, proven on Day 1. |
| Agents SDK API differs from this plan | Plan states intent, not signatures. Read the docs at the start of Task 2.1. |
| MCP built against the old stateful model | Target the 2026-07-28 spec. Read the changelog before Task 5.2 â sessions, the handshake and SSE resumability are all gone. |
| Day 4 overruns | Stages 1â3 are submittable. Ship, then add the connection flow during mentorship week. |
| Model invents a deadline or amount | Deterministic engine; prompt forbids computing figures; all numbers from tool results. |
| SSE protocol drift between services | Fix the contract on Day 1 (Â§4.3) and don't change it. |
| API key leak | `.env` gitignored from commit one. Key lives on the backend only â never expose it to the frontend. |
| OpenAI spend | Set a hard usage limit in the OpenAI dashboard on day one. |

---

## 7. Definition of done

- [ ] Public URL opens with no access request, works at 360px
- [ ] Full path: search â disambiguate â book â chart â delay â decide â file â track
- [ ] **Two concurrent sessions are fully isolated**
- [ ] **Hard refresh restores thread, decision block and countdown**
- [ ] **Backend redeploy mid-session does not lose state**
- [ ] No journey state, PNRs or deadlines held in React state or localStorage
- [ ] Every â¹ amount and deadline traces to a domain function, not a prompt
- [ ] Retiring room gated on CNF/RAC
- [ ] Catering filters on halt window
- [ ] "You don't need to file anything" works for cancelled trains
- [ ] Honesty panel reachable everywhere
- [ ] API surface page live, including the persistence-boundary note
- [ ] MCP server responds
- [ ] No Indian Railways logos or implied endorsement
- [ ] Video under 2:00, summary under 250 words
- [ ] Tested in incognito on a phone

---

## Appendix â first prompt to paste

```
I'm building a hackathon submission â a conversational agent for Indian Railways
that proactively watches a journey and acts before deadlines pass.

Backend is Python/FastAPI with the OpenAI Agents SDK and Postgres.
Frontend is Next.js. Models are OpenAI.

Read these in full before doing anything:
  docs/01-research-context-log.md    â evidence and rules
  docs/02-build-plan.md              â scope and positioning
  docs/03-product-design-document.md â behaviour, copy, states (the spec)
  docs/04-implementation-plan.md     â this build plan

Then confirm you understand:
  1. why app/domain must stay pure Python â no FastAPI, no OpenAI, no ORM
  2. why alerts are deterministic and never model-decided
  3. why the clock is per-session and persisted, and nothing may call
     datetime.now()
  4. the SSE event contract in section 4.3 and rehydration in 4.4
  5. why every table is keyed by session_id
  6. why we use Postgres but NOT Alembic
  7. why the MCP server is stateless and session_id is an explicit tool
     argument, per the 2026-07-28 spec

Then execute Task 1.1 only. Stop and wait.
```
