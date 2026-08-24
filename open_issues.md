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

*(Phase 5+ entries added below as they come up.)*
