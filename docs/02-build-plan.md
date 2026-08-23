# IRCTC Agent â Build Plan

**Project:** Build What Moves India hackathon submission
**Status:** Idea locked, scope in progress. Technical implementation deliberately deferred.
**Deadline:** 28 August 2026, 8:00 PM IST
**Companion doc:** `01-research-context-log.md` (all supporting evidence)

---

## 1. The thesis

> **Indian Railways already knows. It just never tells you in time.**

Every major failure in the IRCTC journey is a case where the system holds the data but never volunteers it:

| The system knows | But it never |
|---|---|
| Your train is 3h 20m late | Tells you a refund deadline is running out |
| Your halt at Jhansi is 8 minutes | Tells you when to order food by |
| Your PNR is now confirmed | Tells you a retiring room just became bookable |
| Your waitlist is GNWL/12 | Tells you what that actually means for your odds |
| Chart preparation just happened | Tells you your platform and coach position |

The interface is built for **pull** â the user must know a feature exists, know its name, find it, and act before an invisible deadline. Our product is built for **push** â the system watches state changes and speaks first.

### Why this thesis survives scrutiny
Indian Railways has attempted app consolidation at least three times (Rail Saarthi 2022, SwaRail, RailOne 2025), and has run a conversational assistant â AskDISHA â since 2018. RailOne now merges five apps with 2 crore+ downloads, yet public reviews describe it as hard to use with basic functions buried.

**Two decades of fixes, neither of which touched the actual problem.** Consolidation changed *where* things live. Conversational input changed *how* you ask. Neither changed the fact that **you still have to know to ask.** A refund deadline you've never heard of expires in silence whether the interface is five apps, one app, or a chatbot.

That's the gap: the system is entirely **pull**. Nothing in it is designed to initiate.

---

## 2. Positioning against the incumbents

There are **two** incumbents, and both must be named â because between them they have already claimed the two most obvious pitches.

| Incumbent | What it already did | Pitch it closes off |
|---|---|---|
| **RailOne** (Jul 2025) | Merged five apps into one super-app; 2 crore+ downloads; UTS shut down Mar 2026 | â "The apps are fragmented" |
| **AskDISHA** (Oct 2018) | Conversational ticket booking by voice/chat, English + Hindi + Hinglish, ~150k queries/day â *including confirmation probability* | â "Booking should be conversational" |

### What remains ours

Both incumbents are **pull-based**. AskDISHA answers when asked. RailOne displays when opened. Neither ever initiates.

> They merged five apps into one and the menus got deeper. They've had a conversational booking bot for eight years. Neither of them ever *watches*. Every failure in this system is a moment where the railway already had the data and simply didn't speak. We built the part that speaks first.

### Feature novelty audit â be honest about this internally

| Capability | Novel? | Role in pitch |
|---|---|---|
| Conversational booking | â AskDISHA, 2018 | Table stakes â build it, don't sell it |
| Confirmation probability | â AskDISHA has it | Supporting UX, not headline |
| Refund status lookup | â AskDISHA has it | Supporting |
| **Proactive alerts on state change** | â | **The product** |
| **TDR detection, deadline, filing** | â | **Flagship** |
| **Connected-journey reasoning** | â structurally impossible in IRCTC today | **Standout** |
| **Cross-system gating** (room on PNR, catering on halt) | â | Depth |

**Action item:** name both RailOne *and* AskDISHA in the demo video. It pre-empts the panel's most likely objection and converts it into evidence of domain command.

---

## 3. What we are building

A **conversational agent** that handles a complete rail journey end to end, from planning through post-journey refund â operating against **our own mock backend**, never live IRCTC.

### Three surfaces (build in this priority order)
1. **Web chat** â the primary demo surface, and the "live public link" the brief requires
2. **WhatsApp-style framing** â no app install, works on any phone; strong accessibility signal for "designed for real Indian users"
3. **MCP server / API** â the architectural argument: this is the interface Railways *should* expose for the agentic era

### Two modes â both are essential
| Mode | Description | Why it matters |
|---|---|---|
| **Reactive** | User asks, agent does | Table stakes â this is what a chatbot is |
| **Proactive** â­ | Agent watches state and speaks first | This is what makes it an **agent**, not a chatbot. This is the differentiator. |

The proactive engine is the spine of the product. If we build only reactive, we've built a nicer form.

---

## 4. Scope

### â Tier 1 â Core demo (must work end to end)

**1. Conversational booking**
- Natural language intent parsing ("Delhi to Bhopal Friday, sleeper, 2 people")
- Fuzzy station disambiguation â asks back conversationally when ambiguous
- Passenger details captured through chat, not forms
- Mock payment confirmation (fake UPI QR / mock gateway)

**2. Waitlist confirmation prediction** *(supporting â AskDISHA already offers this; keep it, don't headline it)*
- Three bands: Confirm (>70%) / Probable (30â70%) / Low (<30%) â industry-standard framing
- Explains *why* in plain language: "GNWL clears faster than RLWL" â **the explanation is our edge here, not the number**
- RAC treated as confirmed
- Openly disclosed as calibrated synthetic data

**3. TDR / refund engine** â­â­ **â the flagship**
- Detects delay/cancellation/AC-failure events from mock train state
- Computes eligibility + correct reason code + **live deadline countdown**
- One-tap filing
- **Also tells users when NOT to file** (auto-refund cases) â half the value
- Tracks status and surfaces the escalation ladder

**4. Proactive alert engine** â­ â the spine
- Chart prepared â platform + coach position pushed
- Waitlist moved â status update
- Delay detected â TDR eligibility + countdown
- Approaching halt â food order cut-off
- Ticket confirmed â retiring room now available

**5. Journey-aware e-catering**
- Cross-references halt duration against order cut-off
- "8 minutes at Jhansi at 2:15 PM â order by 1:50 PM"
- Solves the four-competing-apps fragmentation invisibly

**6. Retiring room via PNR**
- Only offered when CNF/RAC (never WL â credibility detail)
- Triggered by long layovers / odd-hour arrivals
- Reuses the same mock payment flow

### ð¡ Tier 2 â Include if time allows
- **Connecting-journey planner** â IRCTC structurally cannot book two connecting trains, and gives no refund if the connection breaks. Genuine white space; pairs powerfully with waitlist prediction (risk across two legs).
- **Concession & quota eligibility** â "you're 62, senior citizen quota applies"
- **Destination alert / wake-up** â exists via 139, almost nobody knows
- **Payment failure reconciliation** â "â¹1,240 debited, no ticket â here's what happened"
- **Hindi / Hinglish input** â strong accessibility signal

### â Out of scope â deliberately
IRCTC Tourism packages, IRCTC Air, hotels, cabs, parcel/freight, unreserved/platform tickets, freight tracking.

**Rationale:** the brief says reviewers must be able to *complete the main journey from start to finish*. Depth beats breadth. Mention extensibility as one line of roadmap in the pitch; do not build it.

---

## 5. Architecture stance (not implementation â just the principle)

```
User (web chat / WhatsApp framing)
        â
Conversational agent  â OpenAI model / Codex-built
        â
Mock IRCTC MCP server  â our design, our data
        â
Synthetic dataset (trains, PNRs, halts, catering, rooms, delays)
```

**We never touch irctc.co.in.** Established during research: Railways deployed anti-bot systems and deactivated 2.5 crore suspected IDs; unauthorised booking automation has drawn criminal charges under Section 143 of the Railways Act; the brief itself prohibits touching live government systems and using undocumented third-party APIs.

### The mock server is a feature, not a limitation
We are designing **the API surface Indian Railways would need to expose** for agentic access â then implementing a working simulation of it. Candidate endpoints:

```
searchTrains(from, to, date, class)
checkAvailability(trainId, date, class, quota)
getConfirmationProbability(trainId, quota, wlPosition, date)
bookTicket(trainId, passengers, paymentRef)
getPNRStatus(pnr)
getLiveTrainStatus(trainId)
getHaltSchedule(trainId)           â halt durations per station
getCateringOptions(pnr, station)   â cross-referenced with halt window
getRetiringRoomAvailability(pnr, station)
bookRetiringRoom(pnr, station, slot)
checkTDREligibility(pnr)           â reason code + deadline
fileTDR(pnr, reasonCode, passengers)
getRefundStatus(tdrId)
```

**Pitch line:** *"We're not touching live IRCTC infrastructure. Here's the API surface Indian Railways would need to expose for the agentic era â and here's our working simulation of it."*

This single framing scores **End-to-end thinking** and **Honesty** at once.

---

## 6. The demo narrative

One persona, one continuous journey. Give them a name.

| Beat | What happens | Criterion served |
|---|---|---|
| 1 | Types a trip request in plain language | Usability |
| 2 | Agent disambiguates station conversationally | Usability |
| 3 | Shows options **with waitlist odds explained** | Problem, Product thinking |
| 4 | Books through chat; mock payment | Working build |
| 5 | â© *Time advances* â chart prepared â platform + coach pushed | Proactive engine |
| 6 | Approaching halt â food cut-off alert | End-to-end thinking |
| 7 | ð **Delay detected â TDR eligibility + countdown â one-tap file** | **The money shot** |
| 8 | Refund tracked, escalation path shown | End-to-end thinking |

**Beat 7 is the emotional peak of the video.** Everything before it sets up why an agent that speaks first is different from a form that waits.

### Video structure (2 minutes, hard limit)
- **0:00â1:00** â the journey above, as a citizen, no narration of architecture
- **1:00â2:00** â how it was built: Codex/OpenAI role, the mock MCP server design, what's real vs. mocked, how it scales safely

---

## 7. Honesty statement (draft â refine, but say something like this)

> This prototype runs entirely on synthetic data. We do not connect to live IRCTC systems, and we deliberately avoided browser automation and unofficial APIs â both because Railways has invested heavily in blocking automated access, and because the brief prohibits it.
>
> **Real:** the conversation layer, intent parsing, eligibility rules, deadline logic, alert engine, and the full API surface design.
> **Mocked:** train inventory, PNRs, live delay feed, payments, and the historical dataset behind waitlist prediction.
> **Rules modelled from public documentation:** TDR deadlines and reason codes, retiring-room eligibility, catering halt windows, waitlist quota behaviour.
>
> To run in production this would need registered IRCTC partner API access and access to historical PNR outcome data â which is not publicly available to anyone outside IRCTC/CRIS.

Placing this *in the product itself* (not just the video) is a differentiator â most submissions will bury it.

---

## 8. Criterion-by-criterion self-check

| Criterion | How we answer it |
|---|---|
| **Problem** | TDR losses, waitlist anxiety, missed deadlines â all evidenced, all cost users real money |
| **Working build** | One complete journey, plan â book â travel â refund, fully runnable |
| **Usability** | Conversational; no menus; WhatsApp-reachable; works on low-end phones |
| **Product thinking** | Explicit RailOne *and* AskDISHA positioning; honest novelty audit; deliberate scope cuts; telling users when *not* to file |
| **End-to-end thinking** | Designed API surface, not just UI; proactive event engine; escalation ladder |
| **Honesty** | In-product disclosure of real vs. mocked; named the data we can't get and why |

---

## 9. Immediate decisions needed

| # | Decision | Why it blocks |
|---|---|---|
| 1 | **Codex role** â how it's meaningfully used, in one sentence | Hard brief requirement; needed for video minute two |
| 2 | **TDR rule set** â sources disagree on exact windows; pick one, label it a modelled simplification | Core feature logic |
| 3 | **Time simulation** â how the demo fast-forwards to trigger delay/alerts | Beats 5â7 depend on it |
| 4 | **Persona** â who is our named user? | Video coherence |
| 5 | **Hindi/Hinglish** â in or out? | Affects effort and the accessibility claim |
| 6 | **Solo or team of two?** | Submission form requires partner's registered email |

---

## 10. What comes next

1. â Research log â done
2. â Build plan â this document
3. â­ï¸ **Product design document** â screens, conversation flows, state machine, data model, tone of voice
4. â¹ï¸ Technical implementation plan â deliberately deferred

---

## Appendix â lines worth keeping for the pitch

- *"Indian Railways already knows. It just never tells you in time."*
- *"TDR stands for Ticket Deposit Receipt â a name that tells you nothing about the fact that it's how you get your money back. That's the whole problem in three words."*
- *"They merged five apps into one. The menus just got deeper."*
- *"IRCTC has had a conversational booking bot since 2018. It has never once spoken first."*
- *"Every fix so far has changed how you ask. None of them changed the fact that you have to know to ask."*
- *"We're not showing you a faster way to fill the form. We're showing you a system that fills it before the deadline passes."*
- *"Half the value isn't filing the claim â it's telling you when you don't need to."*
