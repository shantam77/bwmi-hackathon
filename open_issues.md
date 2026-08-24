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

*(Phase 6 entries added below as they come up.)*
