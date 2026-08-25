# Open issues

Things that work but are deliberately simplified, or that I noticed in passing
and didn't stop to fix because they weren't blocking the phase at hand. Not
bugs unless marked as one. Review this after all phases are done.

---

## From Phase 1/2

### `search()` doesn't actually filter by date
**File:** `backend/app/domain/search.py`
Availability is keyed by `(train_number, travel_class, quota)` only, not by
date -- a deliberate Phase 1 simplification (see `availability.json`'s
`_meta` note). `search()` accepts a `date` parameter but never uses it to
filter results. Every query returns the same snapshot regardless of which
date was asked for.
**Impact:** can't say "no seats on the 5th but plenty on the 6th." Low risk
for the demo (only one date matters for the persona journey), but worth
knowing if a reviewer tries a different date and expects different results.
**Fix if needed:** add a `date` dimension to `availability.json` and filter
on it, or explicitly document that the mock only models a single snapshot
in time.

---

## From Phase 3

### Four of the eleven PDD alerts don't fire in this build
**File:** `backend/app/engine/alerts.py`
The Demo Controls only cover six moments (chart-prep, boarding day, delay
1h/3h, cancelled, reset) -- there's no "currently en route" state, since
alerts only ever get evaluated on an explicit user action (a demo button or
a chat message), not on a scheduled background tick.
- **D5 (halt approaching / catering)** and **D10 (approaching destination)**
  need a live mid-journey position this build has no way to simulate. Their
  rule functions don't exist yet (they need Phase 5's catering domain logic
  too) and, as designed, have no trigger path even once that logic exists,
  unless a background scheduler or a new demo state is added.
- **D7 (connection at risk)** and **D11 (refund status change)** are
  deferred to Phase 4 on purpose -- they need two-leg journey tracking and
  TDR claim records respectively, neither of which exists until Phase 4.
  These should genuinely get wired in then, unlike D5/D10.
**Impact:** demo can't show "8 minutes at Jhansi, order by 13:50" or "TDR
accepted, refund in 45 days" live via a button click. Not a blocker for the
flagship (D2/D3/D6/D8/D9 are all real and reachable), but worth knowing
before claiming "all 11 alerts work" in the pitch.

### D2's coach/berth and D4's platform number are synthesized, not real allocation logic
**File:** `backend/app/engine/alerts.py` (`_synthetic_seat`, `_synthetic_platform`)
There's no real seat/platform allocation system to draw from, so these are
deterministically derived from a hash of the PNR/train number -- stable
per-PNR, but not modeling anything real. Consistent with the rest of the
dataset being disclosed as synthetic, but flagging explicitly since it's
logic (a hash function), not seed data, doing the inventing.

### D1's "waitlist position improved" is a fixed simulation, not real movement
**File:** `backend/app/engine/alerts.py` (`_d1_waitlist_improved`)
There's no time-varying waitlist dataset to trend against (availability.json
is a single snapshot, see the Phase 1 entry above). D1 fires once at
"boarding_day" with a generic message, not an actual improved position
number. Low priority -- it's the lowest-severity, most decorative alert of
the eleven.

### The chart-prep "did this WL PNR clear" outcome is a deterministic threshold, not a real draw
**File:** `backend/app/engine/state.py` (`compute_status`)
A real waitlist either clears or it doesn't -- there's no way to know in
advance. For the demo to be reproducible across every reviewer's session
(not a coin flip that could embarrass a 50/50 case), clearing is decided by
`probability >= 50%`, using the same generic formula from Phase 1 rather
than a new hardcoded fact. Worth knowing this is a deliberate demo-
determinism choice, not a prediction claim.

### A countdown's clock offset can go stale if the demo clock is reset after it fires
**Files:** `backend/app/routers/clock.py`, `frontend/components/CountdownChip.tsx`
Fixed a real bug found by live E2E testing: `CountdownChip` was computing
remaining time against the browser's real wall-clock time, but TDR deadlines
are expressed on the *simulated* clock's timeline (months away from real
"now" for the September persona date) -- the countdown showed 287 hours
instead of ~47 minutes. Fixed by having each alert carry the
`clock_offset_seconds` valid at the moment it fired, and having
`CountdownChip` use `Date.now() + offsetSeconds*1000` as its reference "now".
**Remaining narrow edge case:** each alert's offset is captured once, at fire
time. If the user later clicks "Reset journey" (or another demo state that
doesn't cause that specific alert to refire, e.g. because of dedup) while an
old countdown-bearing alert is still on screen, that countdown will drift
using its stale, no-longer-current offset. In practice the only
countdown-bearing alert is D8, and dedup means a *worse* delay always fires a
fresh D8 with a fresh offset -- so this only bites if the user resets and
doesn't trigger a new delay alert. Low priority; would need a page-level
"current offset" state threaded through Thread/AgentMessage/AlertMessage
instead of a per-alert copy to fully close.

### ~~Page didn't reliably scroll to the bottom of the thread on load/refresh~~ -- fixed and confirmed
**Files:** `frontend/app/page.tsx`, `frontend/components/Thread.tsx`
The real bug, found once actually traced through: `Thread`'s inner div is
the actual scrollable element (`overflow-y-auto`), but `bottomRef` was
rendered as a *sibling* of `<Thread>` in `page.tsx` -- outside the
scrollable container entirely. Calling `scrollIntoView()` on a ref that
isn't inside the scrolling element doesn't do anything useful, no matter how
the timing is tuned. The earlier `requestAnimationFrame` change was treating
a symptom. Fixed by making `Thread` forward the ref down to its own
scrollable div. Confirmed via the Phase 4 Flow H E2E run: page now lands at
the bottom of a long thread after a hard refresh, DecisionBlock and all.

---

## From Phase 4

### Flow H's exact rupee figures won't match the PDD's illustrative copy, on purpose
**File:** `backend/app/domain/refund.py`
The PDD's Flow H example shows "₹1,470 back of ₹1,890" for leg 2's ordinary
cancellation. I did not reverse-engineer a formula to hit that number --
that was narrative flavor text in the design doc, never backed by a JSON
data file the way the flagship waitlist figures were (see the Phase 1
"proved by testing with data it's never seen" discussion). Instead
`ordinary_cancellation_refund` implements a generic, documented,
publicly-sourced tiered cancellation model (48h/12h/4h thresholds), tested
independently at its own boundaries. For the actual flagship scenario this
produces a *different* number (~₹945 back of ₹1,890, per the 4-12h tier at
the demo's timing). This is the more honest choice given the earlier
conversation about not hardcoding to match specific examples -- but it does
mean the video/pitch shouldn't quote the PDD's exact "₹1,470" figure; use
whatever the running app actually shows.

### Most TDR refund_basis values aren't modelled in detail
**File:** `backend/app/domain/refund.py` (`tdr_refund`)
Only `full_fare`, `full_fare_auto`, and `full_fare_minus_service_charge` are
implemented precisely -- the only three reachable by this build's flows
(LATE_3H, TRAIN_CANCELLED, WAITLIST_NOT_CLEARED). `fare_difference`,
`partial_fare_ac_charges`, and `proportionate_fare` (for class-downgrade, AC
failure, and short-termination reason codes -- none of which any flow in
this build actually triggers) fall back to a full-fare placeholder with a
labelled note, rather than fabricated partial-refund math. Fine as long as
those reason codes stay unreachable; would need real modelling if a future
phase adds AC-failure or downgrade flows.

### Two real Flow H bugs found and fixed by live E2E testing
**Files:** `frontend/app/page.tsx`, `backend/app/store.py`, `backend/app/agent/tools.py`
Both only surfaced by actually driving the full booking-through-delay flow in
a real browser against the real model -- neither was caught by unit tests,
since each depends on the live agent's behavior or the frontend/backend
wire contract, not pure domain logic.

1. **Silently dropped DecisionBlock.** `sendClockAction` in `page.tsx` only
   handled SSE `"alert"` events, not `"component"` -- so Flow H's
   DecisionBlock (correctly computed and streamed by the backend, confirmed
   via the `fired_alerts` table) was received and thrown away client-side.
   No error, no crash -- it just never rendered. Fixed by adding the
   missing branch.

2. **Wrong leg treated as "primary."** The live agent booked the connecting
   leg 2 with the *same* date as leg 1 (`2026-09-04` instead of the correct
   `2026-09-05`) -- a real date-arithmetic mistake, not a bug I injected via
   a test script. `primary_pnr()`'s original design sorted PNRs by
   `(date, departure)` string comparison to find "the earlier-departing
   leg," which then picked leg 2 as primary (its wrong same-day 08:40 looked
   earlier than leg 1's 20:00). This applied the demo delay to the wrong
   train and scrambled every downstream figure (train numbers swapped in
   the DecisionBlock's own labels, refund amounts computed against the
   wrong PNR's fare).

   Fixed two ways: `primary_pnr()` now sorts by `created_at` (a fact this
   system controls itself) instead of trusting an externally-supplied date
   string. And `confirm_booking` now *derives* a connecting leg's date from
   the linked leg's own arrival date rather than trusting whatever date
   argument the model passed -- removing the whole class of "the agent got
   the connecting-leg arithmetic wrong" bugs at the system boundary, not
   just papering over this one instance.

**Residual limitation:** the date-derivation fix assumes the connecting leg
departs on the *same calendar day* it arrives at the interchange (true for
this build's persona data). It doesn't handle a train whose departure
clock-time is earlier than the linked leg's arrival clock-time (which would
need one more day added, matching the rollover logic already in
`domain/search.py`'s connecting-route search) -- not reachable by any
route in the current seed data, but worth knowing if new connecting routes
are added later.

---

## From Phase 5

### Real bug found by live E2E: fuzzy station matching over-matched on generic words like "Junction"
**File:** `backend/app/domain/stations.py` (`resolve`)
Found while investigating what first looked like a much scarier bug (see the false-alarm note below): asking for "Ahmedabad Junction" -- which exactly, uniquely names station ADI -- came back `ambiguous=True` with **18** candidate stations (Guntakal Junction, Jhansi Junction, Mysuru Junction, Nagpur Junction, even bare single-letter codes...). Root cause: the fuzzy fallback stage scores every station's `name`/`city`/`aliases` against the query via `SequenceMatcher.ratio()` and keeps anything scoring `>= 0.6`, with no tier above that for an exact match reached via `name`/`city` rather than `code`/`alias`. Since "Junction" is an 8-character shared suffix across dozens of Indian station names, SequenceMatcher's ratio pushed many unrelated stations over threshold. Same failure mode hit "Chennai Egmore" (exactly names MS) getting bundled with Chennai Central (MAS) because "chennai" -- just the city field -- is a substring of the query, triggering `_similarity`'s 0.85 shortcut.

Fixed by adding a fourth resolution tier, mirroring the "exact wins" principle already used for the code/alias tiers: if any fuzzy candidate scores a perfect 1.0 (the query exactly equals a station's name/city/alias), return only the perfect-score matches, dropping the noisy weaker ones. Verified this does **not** affect the flagship "bangalore" -> {SBC, YPR, KJM, BNC} 4-way ambiguity, since that case is already resolved entirely by the earlier exact-alias tier and never reaches the fuzzy stage at all. Added two regression tests (`test_exact_full_name_match_is_not_diluted_by_noisy_fuzzy_matches`, `test_exact_name_match_wins_even_when_sharing_a_city_with_another_station`) -- the original 9-test suite didn't cover a multi-word query containing a common station-name suffix, which is exactly the gap that let this ship. All 150 backend tests plus these 2 new ones pass after the fix.

### False alarm, recorded for the record: apparent "response truncation" was a test-script timing bug, not a product bug
While testing the fix above, live E2E via Playwright twice showed the agent's reply visually cut off mid-sentence ("No direct trains found for Chennai Egmore -> Ahmedabad Junction on 2026-"). Chased this seriously since it looked like a real, reproducible streaming bug -- checked backend logs (clean, no exceptions, 200 OK), replayed the exact request via raw `curl` (full, complete response), and replayed it via a raw `fetch()` executed inside the actual browser page context bypassing React entirely (also full and complete). All three came back clean. Root cause: my own test helper (`waitAndDump`) took its screenshot the instant a regex first matched a *substring* of the streaming response, not after the stream actually finished -- for this query the matched phrase happened to be the first sentence, so the screenshot fired while the rest of the message was still arriving. Confirmed by re-running while waiting for the real completion signal (the Send button re-enabling, which only happens after `sendMessage`'s `finally` block runs) -- full, coherent response every time, zero console errors. No product code changed for this one; noted here only so a future reviewer doesn't re-chase the same ghost from a screenshot that looks alarming out of context.

### Real bug found by live E2E: catering/retiring-room tools rejected station names, only accepted exact codes
**Files:** `backend/app/agent/tools.py` (`get_catering_options`, `get_retiring_room_availability`, `book_retiring_room`)
`_minutes_until_arrival` and `retiring.room_options` both match `station_code` by exact string equality against the schedule/facility data. `search_trains` already resolves free-text station names/aliases via `domain/stations.resolve()` before touching the domain layer, but these three tools never did -- they passed the model's raw `station` argument straight through. Live-tested by literally asking "What food options do I have at Guntakal" (Guntakal *is* a real stop on the booked train, per `schedules.json`): the tool returned "Guntakal isn't a stop on 12295's route" because the code is `GTL`, not `"Guntakal"`.

Fixed by adding `_resolve_station_code()` (best-effort name/alias -> code via `stations.resolve()`, falling back to the raw query if nothing resolves so an unrecognized station still fails with a clear error rather than silently swallowing it) and routing all three tools' `station` argument through it before use. Re-verified live after the fix: "Guntakal" now correctly resolves to GTL and returns real vendor data. Same root cause as the Phase 4 connecting-leg date bug -- don't trust an arbitrary model-supplied string to already be in the exact shape internal lookups need; resolve it at the system boundary instead.

### WL-gated retiring-room denial verified live, not just by unit test
**File:** `backend/app/domain/retiring.py`
While live-testing the fix above, the freshly booked SL ticket on 12295 was GNWL/18 (waitlisted, by the persona's deliberate seed-data calibration) and the retiring-room tool correctly refused it: "not eligible — ticket is WL... retiring rooms need a confirmed or RAC ticket." Re-ran the same flow booking 3A instead (AVAILABLE/CNF per `availability.json`) and got a real eligible=true response with both NGP room options and their real tariffs (₹520 / ₹1,150). Confirms the CNF/RAC gate from `test_retiring.py` holds in the actual conversational flow, not just at the domain-function level.

### `book_retiring_room` doesn't persist the booking
**File:** `backend/app/agent/tools.py` (`book_retiring_room`)
Unlike train PNRs, a booked retiring room isn't written to any table --
it returns a generated reference and tariff, but there's no `retiring_room`
row and no way to look it up again later (no `get_retiring_room_status`
tool exists either). Deliberate scope cut: the PDD's retiring-room flow
(Flow F) only needs to show the booking succeed in the conversation, not
survive a refresh. Documented in the tool's own docstring so the model
never claims otherwise. **Fix if needed:** a `retiring_room_bookings` table
keyed by `session_id` + PNR, same pattern as `TDRClaim`.

### MCP server exposes 5 of 16 tools, by design
**File:** `backend/app/mcp_server.py`
`TOOL_CATALOGUE`/`TOOL_HANDLERS` cover `search_trains`, `resolve_station`,
`get_confirmation_probability`, `get_pnr_status`, and
`check_tdr_eligibility` -- a representative slice proving the stateless
2026-07-28-spec shape (header validation, `-32020`/`-32602` error codes,
`session_id` as an explicit argument, deterministic `tools/list` with
`ttlMs`/`cacheScope`), not a full mirror of the agent's own tool surface.
Booking/mutation tools (`confirm_booking`, `file_tdr`, `book_retiring_room`)
were deliberately left off this externally-facing surface for the demo --
letting a third-party MCP client book real (mock) tickets or file real
(mock) TDR claims through an unauthenticated stateless endpoint wasn't a
decision to make silently. **Fix if needed:** add the remaining read tools
first (`get_catering_options`, `get_retiring_room_availability`,
`get_refund_status`), then decide deliberately on mutation-tool exposure
and what auth story would gate it.

### `/api/surface` and the honesty panel are hand-maintained, not introspected
**Files:** `backend/app/routers/surface.py`, `frontend/components/HonestyPanel.tsx`
The implemented-endpoints list in `surface.py` is a manually written list of
5 routes, not generated from FastAPI's actual route table -- it'll silently
go stale if a route is added or removed without updating it. The MCP half
avoids this (it reads the real `TOOL_CATALOGUE` the server itself serves,
so that part can't drift). Similarly, `HonestyPanel`'s "what's real / what's
mocked" copy is static PDD §10 text, not derived from the codebase --
correct as of this writing, but nothing enforces it staying correct if the
mock data sources change. Low priority for a hackathon submission; would
matter if the project grew past this snapshot.

---

## From Phase 6 (final cross-cutting verification)

No new product bugs found in this pass -- it was a pure verification pass against the fully-assembled app (Phases 0-5 together). Everything below was checked live, not assumed:

- **360px viewport.** Full flagship path (ambiguous search, OptionCard, PaymentSheet, PNRConfirmation, alerts, live TDR countdown, TDR eligibility/filing/tracking) screenshotted at a 360px-wide viewport -- the narrowest realistic phone width. All legible, no horizontal overflow, Demo Controls wrap cleanly. DecisionBlock wasn't re-screenshotted at 360px specifically (its `flex-col sm:flex-row` CSS was verified by reading the source, and it was already live-tested for functional correctness in Phase 4) -- skipped re-running the two-leg booking + delay flow again mainly to conserve the OpenAI budget on a check that source review already answered.
- **No OpenAI key in the frontend bundle.** Grepped the full production `.next` build output for the literal string `OPENAI_API_KEY` and for an OpenAI-shaped secret (`sk-proj-...`). Clean. (One false-positive substring match on "mask-type", an unrelated SVG attribute name -- not a key.)
- **Full path, one session, live:** search (ambiguous "bangalore") -> disambiguate -> book -> chart prepared -> delay 3h+ -> decide (D8 alert with live countdown) -> file TDR -> track status ("accepted"). Zero console errors throughout.
- **Two concurrent sessions fully isolated**, re-verified against the current build (not just assumed from the `session_id`-everywhere design): two independent cookie jars get distinct `session_id`s from `/api/health`; a real chat message and a clock change in session A are both completely invisible to session B's `/api/session` response.
- **Hard refresh mid-demo restores state** -- including, specifically, *after* a TDR claim has been filed (the heaviest state this build produces). Initially looked broken during testing (thread appeared to vanish after refresh) -- turned out to be my own test script screenshotting only ~1.5s after the reload, before the `/api/session` fetch had resolved. A heavier session (booking + demo-state alerts + TDR claim) took ~6s to fully rehydrate and re-render in this local dev environment (uncached Next.js dev server + a real Railway Postgres round-trip) -- re-tested with a proper wait and it restores completely and correctly every time. No product code changed; noted here so this doesn't get re-investigated as a phantom bug later, same as the Phase 5 streaming false alarm.
- **Backend process restart doesn't lose state.** Stopped and restarted the uvicorn process mid-session; `/api/session` for an existing session cookie returned identical data afterward, as expected given all state lives in Postgres and nothing is held in server memory. (Actual Railway/Vercel redeploy was not tested -- out of scope per the earlier decision to keep this build local-only.)

### Real UX gap found while acting as a user: no feedback while a tool call is in flight
**File:** `frontend/app/page.tsx`
Noticed this directly while using the product end-to-end, not from a screenshot: the reply bubble renders `content: ""` from the moment a message is sent until the *first* streamed token arrives -- an empty, invisible box. Measured real gaps of up to ~9 seconds (a fresh search) and up to ~60 seconds (filing a TDR claim) between sending a message and any visible response, with literally nothing on screen in between except a disabled Send button. To a real user this reads as "did this break," not "it's thinking."

Fixed by handling the SSE `tool_call` event client-side (previously silently ignored) and showing a short, friendly per-tool label ("Searching trains…", "Filing your TDR claim…", etc., via a `TOOL_LABELS` map) in the bubble until the first real token arrives, at which point it's replaced outright.

While building this fix, introduced and then caught a real bug in it: the first token's handler read a mutable `receivedFirstToken` flag from *inside* the `setMessages` updater closure, but reassigned that same flag synchronously on the very next line -- since React can defer invoking a functional state updater, the updater sometimes ran after the flag had already flipped, turning "replace the placeholder" into "prepend real content onto the placeholder" (visible as "Searching trains…Found three direct SL options..."). Fixed by capturing `isFirstToken` into a fresh per-iteration `const` before the state update, so each closure captures its own correct snapshot regardless of when React gets around to calling it. Re-verified live across single- and multi-tool-call turns (search, quote, book, TDR eligibility, TDR filing) -- clean every time, zero console errors, zero leftover placeholder text.

### Two more real UX bugs, reported directly by the user with screenshots and fixed live
**Files:** `frontend/components/AgentMessage.tsx`, `frontend/app/page.tsx`, `frontend/lib/types.ts`, `frontend/components/TypingIndicator.tsx`, `frontend/app/globals.css`
The user ran the app themselves for the first time after Phase 6 and reported two concrete problems with screenshots, both real:

1. **The tool-call indicator fix above didn't go far enough.** It only fired on an SSE `tool_call` event -- a plain conversational turn with no tool call still showed a blank bubble for however long the model took to respond, and even the tool-triggered case was plain static text, easy to miss as "loading" rather than "the final answer." Fixed by making the reply bubble show an animated three-dot "Thinking…" indicator (new `TypingIndicator` component, CSS keyframes in `globals.css` guarded by `prefers-reduced-motion`) the *instant* the message is sent, unconditionally -- upgraded to a tool-specific label if a `tool_call` event arrives, then replaced outright by the first real token. Added a `pending` flag to `ChatMessage` to distinguish "this text is a transient status" from real message content.

2. **The component (OptionCard/PaymentSheet/PNRConfirmation) rendered below the narrative text, not above it.** Screenshots showed a user having to scroll past a long, still-growing paragraph of streamed text before reaching the actual option cards -- because the text streams in progressively and sits first in the DOM, it kept growing and pushing the already-arrived, already-complete card further down and out of view. Fixed by reordering `AgentMessage.tsx` so the component renders first (stable, appears once, doesn't move) with the narrative text following below it as commentary -- matches how the data actually arrives too (`component` event fires before most `token` events for the same turn).

Both fixes verified live via a throwaway backend+frontend pair on ports 8001/3001 (kept fully separate from the user's own 8000/3000 instances, per their explicit request not to touch those) -- confirmed the "Thinking…" dots appear within ~500ms of sending, upgrade to "Searching trains…" once the tool call fires, and that the OptionCard now renders at the very top of the reply with the explanatory text below it. Zero console errors.

### Real visual/UX redesign, driven directly by user feedback on the actual running app
**Files:** `frontend/app/globals.css`, `frontend/app/layout.tsx`, `frontend/components/FormattedText.tsx` (new), `frontend/components/AgentMessage.tsx`, `frontend/app/page.tsx`, `frontend/app/api-surface/page.tsx`, `frontend/components/{PaymentSheet,DecisionBlock,DemoControls,HonestyPanel}.tsx`, `backend/app/routers/session.py`, `backend/app/session.py`
The user ran the app themselves and pushed back hard, with a screenshot, on three things: the reply text was an unreadable wall of prose (numbered options ran together with no visual structure), there was no way to start a new conversation, and the color/type system read as generic ("looks like a side project of a Btech first-year student") rather than anything evoking Indian Railways specifically. All three addressed:

1. **Message formatting.** New `FormattedText` component replaces the single `<p className="whitespace-pre-wrap">` with real structure: numbered/bulleted blocks render as actual `<ol>`/`<ul>` lists, a short leading label ("Recommendation:", "What it means —") gets bolded, and literal `**bold**` is honored if the model ever emits it. The model isn't prompted to use markdown syntax (deliberately not touched, to avoid destabilizing a carefully-tuned prompt this late) -- the parser reads the plain-prose structure the four-part turn shape already produces instead.

2. **"New chat."** Added `POST /api/session/new`, which issues a fresh `session_id` cookie (old session's rows left untouched in Postgres, not deleted -- matches "log out and start over," not a wipe). While building this, caught a real latent bug: `SessionMiddleware`'s own "issue a cookie if absent" fallback could overwrite the endpoint's freshly-set cookie with a *different* ID whenever `/api/session/new` was called before any cookie existed at all (only reachable if the very first request to the app is a New Chat click, not the normal flow, but still a real bug) -- fixed by having the middleware check whether the response already carries a `set-cookie` header for this cookie name before adding its own.

3. **Color and type system.** Replaced the generic dark-slate-plus-GitHub-green palette with navy-black neutrals and a saffron/amber `--accent` token (a departure-board LED color that also quietly nods to the tricolor) used for brand and primary actions ONLY -- Send, Simulate Payment, Choose Option, New Chat's hover state, links. `--signal-go/wait/stop` stay reserved for actual journey status and were deliberately left alone everywhere they're genuinely semantic (OptionCard's Confirmed badge, PNRConfirmation's success border, DecisionBlock's Recover-amount text) -- separating "this is interactive" from "this ticket is confirmed" was the core fix, since both had been sharing the same green. Swapped Inter/JetBrains Mono for IBM Plex Sans/Mono (one designer's hand across both faces, more engineering character than the default SaaS pairing). Also added a visible focus ring to the message input, which had none at all.

Verified live: built a production build pointed at a throwaway backend (port 8001), served on port 3001 via `next start` rather than `next dev` -- discovered mid-session that `next dev`'s lock file blocks a second dev-mode instance for the same project directory regardless of port, unlike `next start`, which has no such restriction. Confirmed the formatted reply (numbered list, bolded labels), the card-still-renders-first ordering from the earlier fix, and New Chat surviving a hard refresh (proving it's a real new backend session, not just cleared local state) -- zero console errors. Also this time properly killed the verification processes by PID directly rather than relying on `TaskStop` alone, after the previous round left an orphaned `next dev` process that blocked the user's own server from starting.

### Replaced heuristic text parsing with a real markdown contract, per direct user pushback
**Files:** `backend/app/agent/prompt.py`, `frontend/components/FormattedText.tsx`
The formatting fix above (bold a guessed label, detect numbered lines) was still fundamentally guessing structure out of prose after the fact -- the user pushed back hard, correctly: even well-formatted, a line like "SBC 20:00 → NGP 06:15 (day+1) SL WL GNWL P18" still makes someone parse a run-on sentence to find the departure time. Explicitly named the bar: someone should be able to glance once and know, the way a boarding pass or departure board works, not read a paragraph.

Fixed at the source instead of the symptom. `prompt.py` gained a new "## Formatting" section that commits the model to an exact markdown shape for a train option -- train name bold on its own line, route on the next, **Departs**/**Arrives** each their own bold-labeled line, status and fare pulled out separately -- plus a general principle ("bold the label, give the number its own line") for any other numeric reply. `FormattedText.tsx` was rewritten around `react-markdown` + `remark-gfm` (tables, in case the model ever uses one) + `remark-breaks` (critical detail: CommonMark collapses a single newline into a space by default, which would have silently defeated the entire template -- `remark-breaks` makes a single `\n` a real line break, matching how the model actually writes adjacent facts with no blank line between them).

Verified live against the real model, not just read back: the connecting-journey search rendered exactly the target shape for all three options and both legs each. More importantly, a completely different content type (TDR eligibility -- Reason/Deadline/Refund/Certificate) picked up the *same underlying discipline* without a hardcoded template for it, confirming the general principle in the prompt generalizes rather than only the one worked example. Zero console errors in either case. No new backend tests needed (prompt.py is a string constant, not testable logic); 152/152 existing backend tests unaffected since no backend logic changed.

### Full theme flip to light, approved after a direct mockup comparison
**Files:** `frontend/app/globals.css`, `frontend/app/layout.tsx`, `frontend/components/OptionCard.tsx`
User pushback, again with a screenshot: even with real markdown structure, dark-on-black at small sizes is genuinely harder to read for older eyes than the alternative, and the whole visual identity read as generic rather than considered. Researched IRCTC redesign case studies (converging on light backgrounds + trustworthy blue for accessibility) and Claude's own light theme (warm off-white, soft ink, not stark white/pure black) since IRCTC's live site and AskDISHA both block automated browsers. Built a side-by-side mockup artifact using the user's *exact* screenshot content rendered in both themes before touching any component, to avoid guessing wrong on a second full re-theme -- approved as-is.

Implemented: warm ivory surface (`#faf8f4`), soft charcoal ink (`#2a2723`, not pure black), muted navy accent (`#2c5f86`) for brand/actions only, muted (not saturated) status colors with soft pill backgrounds. Public Sans replaces IBM Plex Sans for body text specifically because it's the U.S. government's own accessibility-first typeface (USWDS) -- built for exactly this brief. `OptionCard.tsx` was restructured, not just recolored, to the boarding-pass shape from the approved mockup: train name bold on its own line, Departs/Arrives as a two-column grid with tabular numerals, a soft-background status pill and the fare in one row. Verified live against the real model and re-screenshotted every flow (search, booking, TDR, alerts) -- zero console errors, matches the mockup closely.

### Text was still re-narrating what the cards already show, just now well-formatted
**File:** `backend/app/agent/prompt.py`
Caught immediately after the theme change, live: the model was applying the new per-option markdown template faithfully, but for a 3-option x 2-leg connecting search that meant six full boarding-pass blocks in the text *underneath* six already-rendered OptionCard blocks showing the identical numbers -- technically well-formatted, still a wall of redundant content. The root problem was never really formatting; the text was trying to be a second, prose copy of data a card already displays perfectly.

Fixed by adding an explicit rule to prompt.py: once `search_trains` (or `quote_booking`/`confirm_booking`) has rendered its card, the text underneath is commentary only -- three or four sentences, no per-option numbers restated at all. The line-per-fact template from the earlier fix is now scoped explicitly to cases with *no* card already on screen (a PNR summary in text, a TDR deadline, etc.), not to search results. Verified live: the same connecting-journey search that previously produced six redundant blocks now produces three short sentences under the cards -- what was found, the recommendation and why, the next action.

**Verification note:** while iterating on this, found (again) that `TaskStop` on a background `npm run dev`/`npm run start` task doesn't reliably kill the underlying Node process tree on Windows -- confirmed this repeatedly by checking `netstat` after `TaskStop` and finding the port still LISTENING. Switched entirely to finding the actual PID via `netstat -ano | grep LISTENING` and killing it directly with `taskkill //PID <pid> //F` for every verification instance from this point forward, and confirmed via `netstat` afterward that the port was actually free -- not just that the harness task said "stopped."

### Bare station codes in prose, reported directly with a screenshot -- fixed at the actual source
**Files:** `backend/app/agent/tools.py`, `backend/app/agent/prompt.py`, `frontend/lib/types.ts`, `frontend/components/OptionCard.tsx`
The user flagged "the agent shouldn't assume I know what the code stands for" against a screenshot reading "I checked SBC, YPR, KJM and BNC" -- correct, and worse than it first looked: `search_trains`' `ambiguous_stations.candidates` only ever sent the model bare codes (`[m.station.code for m in matches]`), never names. A prompt instruction alone ("use names, not codes") wouldn't have actually fixed this -- the model had no name to use, only the code, so any fix that stopped at the prompt would have forced it to either keep saying codes or guess a station's full name from its own general knowledge, which is exactly the kind of unverified guess this build has avoided everywhere else (the same "don't ask the model to reconstruct data a tool should hand it directly" principle as the Phase 4 connecting-leg date fix and the Phase 5 station-resolution fix).

Fixed at the source: `candidates` is now `[{"code": ..., "name": ...}]` instead of a bare code list, so the model has the real name to say. Added an explicit prompt rule ("never say a bare station code in prose") now that there's actually a name available to satisfy it. Updated the frontend type and `OptionCard`'s own disambiguation caption to match (it had the identical bug in the visual component, not just the model's text). Verified live: "I checked SBC, YPR, KJM, BNC" is now "KSR Bengaluru City; Yesvantpur Junction; Krishnarajapuram; Bengaluru Cantonment."

**Known residual gap, not fixed:** every OTHER station reference in the tool surface (a leg's `from_station`/`to_station`, an interchange, a booked PNR's stations) is still a bare code -- `Leg.from_station` etc. carry only the code throughout the whole domain model, not a paired name. The disambiguation list was the concretely reported and now-fixed case; the model *could* still say a bare code elsewhere (e.g. "via NGP" in a recommendation sentence) since that's genuinely all the data it has for that field. Widening the fix to attach a name to every station reference across every tool would touch the `Leg` model, every tool response, and the frontend `Leg` type -- a much larger change than what was actually reported broken. Worth a full pass if this surfaces again in testing.

### Three real UX/correctness issues, found during a live dry-run of the proposed demo script
**Files:** `frontend/components/OptionCard.tsx`, `backend/app/agent/tools.py`, `backend/app/agent/prompt.py`
Running the actual proposed demo flow end to end (not a synthetic test) surfaced three things, all fixed:

1. **A real "[object Object]" bug the user hit live** turned out to be the previous station-names fix running against a stale frontend build -- the currently-committed `OptionCard.tsx` was already correct (`c.name`/`c.code` mapped properly). Not a new bug; confirmed by re-reading the committed source before touching anything. Worth remembering for demo day: a stale `npm run dev` process or a browser tab that hasn't hard-refreshed can resurrect an already-fixed bug.

2. **Option cards had no numbering.** Multiple journey-option cards stacked with no "Option 1/2/3" anchor -- since leg 1 is often the same train across several options (differing only in leg 2), they visually blurred together with nothing to reference back to from the text. Added an explicit `OPTION N` badge to each card in `OptionCard.tsx`.

3. **Discovered while verifying fix #2, not reported by the user: `search_trains` was returning every valid combination unranked and uncapped** -- for a 2-leg connecting search with 3 viable trains on each leg, that's 9 near-duplicate cards, not the "at most three options" the prompt already assumed existed. `domain/search.py` is correctly exhaustive (a pure function has no business deciding what's "worth showing"); the cap belongs at the tool layer, which had no cap at all. Added ranking in `tools.py` -- by each option's *weaker* leg's confirmation odds (a connection is only as reliable as its worst leg), then shortest layover as a tiebreaker -- and capped to 3. The recommendation text also picked up an explicit bolding requirement (short commentary was still landing as an unformatted, unemphasized paragraph -- "short" and "readable" aren't the same thing, brevity alone didn't fix scannability).

152/152 backend tests pass (untouched by the ranking/cap change, since it lives in the agent tool wrapper, not `domain/search.py`, which several tests assert stays exhaustive). Verified live: the same connecting search that produced 9 sprawling cards now produces exactly 3, correctly ranked, each clearly numbered, with a bolded one-line recommendation underneath.

### Every alert and the DecisionBlock named trains and stations by bare number/code, or not at all
**Files:** `backend/app/dataset.py`, `backend/app/engine/alerts.py`, `backend/app/engine/connection.py`, `frontend/components/AlertMessage.tsx`
Found dry-running the actual demo script and immediately called out, correctly and bluntly: "only train number isn't enough -- to and from destination and train name is important for entire context -- remember the intent is to help the user not confuse them." Auditing every deterministic alert message confirmed it was systemic, not one bad string:

- D2 ("Confirmed. S8, berth 65.") and D6 ("Running 3h 20m late.") named no train at all.
- D4 ("Platform 6.") named neither a train nor a station -- the single worst offender.
- D8 ("12295 is running 3h 20m late.") had the train *number* but not its name.
- D9 named the destination *station* but not the train.
- The countdown chip next to the D8 alert had no label at all -- just a bare "43:24" with no indication of what it was counting down to.
- The DecisionBlock (Flow H) referenced every train by bare number in its line items ("Leg 1 refund (12295)", "Cancel 12539", "Rebook 15665") and the recommendation text used a bare station code ("you still reach BSB today").

All of this had the real data sitting right there unused -- `PNRRecord` already carries `train_name`, and station names just needed a lookup by code (added `dataset.station_name()`, backed by the existing `STATIONS_BY_CODE` dict, since this is now needed in both `alerts.py` and `connection.py`). Fixed every message to name both the train (number + name) and any station involved (by name), and added a "File within:" label ahead of the countdown chip so it's clear what it's counting down to. Verified live against the actual flagship flow end to end -- every alert (D2/D4/D6/D8/D9) and every DecisionBlock line item now names its train in full; the recommendation names the destination station, not a code.

152/152 backend tests unaffected -- the handful that check alert/DecisionBlock content use substring assertions ("Leg 1" in label, fare figure in message), not exact-string matches, so none needed updating for the richer wording.

### Demo Controls silently acted on one PNR with zero UI indication of which
**Files:** `backend/app/routers/session.py`, `frontend/lib/types.ts`, `frontend/app/page.tsx`, `frontend/components/DemoControls.tsx`
Raised directly: "for a multi-leg journey, 'chart prepared' for which train?" Traced the actual mechanism precisely before proposing anything -- `/api/clock` always acts on `store.primary_pnr()`, the *first* PNR booked in the session (deliberately leg 1 for a connecting journey, since that's the train whose delay can break the connection). That targeting logic is already correct; the problem was entirely that nothing in the UI said so. Someone handed this app cold would see generic buttons with no indication of which train they touch.

Also found while investigating: `GET /api/session`'s `journey`/`state` fields use `latest_pnr()` (the *most recently* booked PNR) -- a different PNR than Demo Controls acts on, for a connecting journey. Not a live bug today since the frontend doesn't currently render those fields anywhere, but it meant the fix couldn't just reuse that existing data without introducing a *new* mismatch -- had to expose the actual Demo-Controls target specifically.

Fixed with a status line, always visible above the Demo Controls buttons, computed from a new `demo_target` field (backed by `primary_pnr()`, matching the real target exactly) plus a lightweight `GET /api/demo-target` the frontend calls after every booking completes (not a full session re-fetch, which would re-pull the entire message history just to learn one PNR):
- No PNR booked yet: "Book a ticket to activate Demo controls." (closes a second, quieter ambiguity -- clicking a button with nothing booked previously did nothing, silently)
- One ticket: "Acting on 12295 Sanghamitra Express · KSR Bengaluru City → Nagpur Junction"
- A connecting journey: "Acting on your journey's first leg -- 12295 Sanghamitra Express · KSR Bengaluru City → Nagpur Junction. A delay here is what could break your connection." -- states the *why leg 1* answer before anyone has to ask.

152/152 backend tests pass. Verified live across all three states end to end (no booking, single leg, both legs of a connection) -- zero console errors, label updates correctly at each stage without a page refresh.

**Testing-methodology lesson learned twice this project** (Phase 5's streaming false alarm, and the refresh timing above): when an E2E script's *own* screenshot timing races an async operation (a stream still arriving, a rehydration fetch still in flight), the result looks exactly like a real product bug from a screenshot alone. Both times the fix was the same -- wait for an actual, unambiguous completion signal (the `done` SSE event / the Send button re-enabling) instead of "some expected text is now visible," before concluding anything is broken.

---

## From a full thorough dry-run of the actual demo script

Asked explicitly to run the exact demo script end to end, thoroughly, as a judge would, before recording anything. Found five real things, all fixed and re-verified live:

### The empty-state hint text was itself genuinely ambiguous
**File:** `frontend/components/Thread.tsx`
The suggested example ("Try: 'Bengaluru to Varanasi on the 4th, 2 people'") -- typed exactly as shown, the very first thing anyone would do -- triggered a clarification request ("which month and year is 'the 4th'?") instead of a search. Correct agent behavior (a bare day-of-month really is ambiguous, per the same "never guess" discipline used everywhere else in this build), but it meant the single most likely first interaction breaks the "prove competence fast" beat before it starts. Tested several phrasings directly rather than guessing: adding a month name alone ("4 September" or "September 4th"), even with no year, resolves cleanly every time -- the model correctly infers the nearest future occurrence. Fixed the hint text to "Bengaluru to Varanasi on 4 September, 2 people."

### Flow H's "Abandon both": leg 2's delay state leaked from leg 1, corrupting its TDR filing
**Files:** `backend/app/engine/state.py`, `backend/tests/test_state.py`
The most serious finding. Clicked "Choose Abandon both" live and the response showed BOTH PNRs' TDR filed under reason LATE_3H for full fare -- but leg 2's own train (12539) was never delayed; only leg 1 (12295) was. Traced to `compute_status()`: the demo clock's `delay_minutes`/`is_cancelled` were applied unconditionally to *whichever* PNR was passed in, not gated to the PNR the Demo Controls click was actually "about" (`store.primary_pnr()`). Querying leg 2's status independently (which is exactly what happens when the agent later calls `check_tdr_eligibility` on it) silently inherited leg 1's artificial delay.

Fixed by gating both the demo-state delay and the demo-state cancellation to only apply when the PNR being queried IS the session's primary PNR; any other PNR falls through to genuine elapsed-time computation. Added two regression tests (`test_demo_delay_does_not_leak_onto_a_different_pnr_in_the_same_session`, `test_demo_cancellation_does_not_leak_onto_a_different_pnr_in_the_same_session`) -- the first iteration of the delay test used a same-day-earlier fixture for leg 2 and passed for the wrong reason (elapsed-time fallback happened to also read 0 differently than expected), caught by reasoning through the actual numbers rather than trusting a green test, then corrected to use a realistic next-day leg 2 fixture matching the real flagship connection.

### No tool existed for leg 2's actual refund mechanism
**File:** `backend/app/agent/tools.py`
Direct consequence of the above, but a real gap even once `compute_status` was fixed: `check_tdr_eligibility` would now correctly say leg 2 isn't TDR-eligible, but the agent had no other tool to actually process its refund -- `file_tdr` is the only refund-filing tool that existed. Added `cancel_booking`, a thin wrapper over `domain/refund.ordinary_cancellation_refund()`, and told the prompt explicitly: leg 1 (genuinely delayed) is `file_tdr`, leg 2 (running fine, just unusable) is `cancel_booking`, never the other way round.

### The agent had no way to know which train the DecisionBlock actually named
**File:** `backend/app/agent/tools.py`
Testing "Travel late, rebook leg 2" surfaced a deeper structural gap: the DecisionBlock is rendered directly by the backend (`/api/clock`), never produced by a tool call -- the model has *no* programmatic access to which specific replacement train it displayed. First attempt at fixing this via prompt wording alone ("book the DecisionBlock's own named train") failed exactly as it should have: the agent honestly replied "I don't have the DecisionBlock details," rather than guessing. Fixed properly with `get_flow_h_rebooking_option`, which reuses `engine.connection.find_rebooking_option()` -- the *identical* selection logic the DecisionBlock itself used -- guaranteeing the agent always books the exact train the user was actually shown, never an independently-searched substitute that might differ.

### Choosing an option stopped halfway and asked "shall I proceed?"
**File:** `backend/app/agent/prompt.py`
"Abandon both" completed in one click; "Travel late, rebook leg 2" cancelled the old ticket then stopped to ask permission before rebooking -- an inconsistent, extra step for an action the DecisionBlock button click had already fully specified (train, fare, everything) and the user had already explicitly chosen. Added an explicit prompt rule: a DecisionBlock choice is carried out completely in one turn, no intermediate confirmation, since the button click itself already was the confirmation. Re-verified live: leg 2 is now cancelled and the replacement is booked in a single response, using the exact train and fare the DecisionBlock named.

### The honesty panel's "learn more" link navigated away from the live session
**File:** `frontend/components/HonestyPanel.tsx`
"See the proposed API surface" had no `target="_blank"`, so clicking it from mid-conversation navigated the whole tab away from the chat -- found while testing it back-to-back with a hard refresh and New Chat check, where it silently broke the rest of the test script's assumptions about which page it was on. A judge doing the same thing loses their place with no easy way back except the browser's own back button. Added `target="_blank" rel="noopener noreferrer"` so it opens alongside the live session instead of replacing it.

**Also explicitly re-verified as correct, not bugs:** hard refresh mid-DecisionBlock restores both the DecisionBlock and the Demo Controls target label correctly (an earlier check that seemed to show the label missing was the test script's own mistake -- it checked the label's text while the Demo Controls panel was still collapsed, where it's correctly not in the DOM at all); New Chat correctly resets the Demo Controls label back to "Book a ticket to activate Demo controls."

154/154 backend tests pass throughout (152 existing + 2 new regression tests for the delay-leak fix). Every fix in this section was verified live against the real model, not assumed from the code.
