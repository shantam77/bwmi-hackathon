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

### Page didn't reliably scroll to the bottom of the thread on load/refresh
**File:** `frontend/app/page.tsx`
Noticed in both Phase 2 and Phase 3 E2E screenshots: a hard refresh restored
the full thread correctly (content was right), but the view reset to the top
instead of showing the latest message -- likely `scrollIntoView` computing
against a not-yet-painted page right after rehydration mounts the whole
thread at once. Applied a fix (`requestAnimationFrame` + `behavior: "auto"`
instead of `"smooth"`) but haven't re-run a dedicated E2E check for it yet --
verify this during Phase 4/5's longer-thread E2E passes rather than trusting
it blind.

---

*(Phase 4+ entries added below as they come up.)*
