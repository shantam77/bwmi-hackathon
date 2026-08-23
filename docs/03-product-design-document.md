# IRCTC Agent â Product Design Document

**Project:** Build What Moves India hackathon submission
**Author:** Shantam
**Version:** 1.0 â 23 August 2026
**Companion docs:** `01-research-context-log.md` (evidence) Â· `02-build-plan.md` (scope & positioning)

> **How to use this document.** This defines *what the product is and how it behaves*, not how it's coded. It is written to be handed to Claude Code as the source of truth for behaviour, copy, and states. Everything here should be implementable without further clarification. Where a decision is still open, it is marked **â¬ DECISION PENDING** with a default already specified so nothing blocks.

---

## 1. Product in one paragraph

A conversational travel agent for Indian Railways that plans, books, and â critically â **watches** a journey. It speaks first when something changes: when a chart is prepared, when a halt is approaching, when a delay makes a refund deadline start ticking. It reasons across the rules IRCTC never explains, and turns them into a single recommendation with one action attached. It runs entirely on a mock backend, and says so.

**Product name (working):** `Saarthi` â Hindi/Sanskrit for *charioteer*; the one who drives while you travel. Familiar across North and South India, and already part of railway vocabulary (Rail Saarthi). Alternatives: `Pahiya`, `Yatri`, `Rail Sathi`.

---

## 2. Persona

**Shantam, 27. Bengaluru (Koramangala). Software engineer.**

- Books trains a few times a year â enough to be frustrated, not enough to be expert
- Comfortable with technology, but has never heard the phrase "Ticket Deposit Receipt"
- Books on mobile, often at 11 PM, often in a hurry
- Travels the Bengaluru â North India corridor, which almost always requires a connection
- Reads English fluently; types in a mix of English and Hinglish without thinking about it

**What he wants:** to say where he's going and stop thinking about it.
**What he fears:** the waitlist not clearing, and finding out too late that he lost money he could have got back.

**Demo journey:** Bengaluru (SBC) â Nagpur â Varanasi, on 4 September, with an overnight layover at Nagpur and a retiring room booked there.

---

## 3. Design principles

These are the tie-breakers. When a design question comes up, resolve it against these in order.

**1. Speak first.**
The product's whole reason to exist is that it acts before being asked. If a feature only works when the user initiates, question whether it belongs.

**2. One message, one decision, one action.**
Never present a menu of raw facts. Do the reasoning, state a recommendation, attach a button. The user's job is to say yes or pick between two named options â never to synthesise.

**3. Say the number.**
"You'll get â¹2,710 back of â¹3,580" beats "a partial refund applies." Specificity is the entire trust mechanism. Every claim about money, time, or odds carries a figure.

**4. Explain the rule in one clause, then move on.**
"GNWL is the good kind of waitlist â it clears first." Enough to build understanding, never a lecture. The user should finish a conversation knowing slightly more about how railways work than when they started.

**5. Tell them when to do nothing.**
Half the value of the refund engine is saying "you don't need to file anything, this refunds automatically." Restraint is a feature.

**6. Never pretend to be official.**
No Indian Railways logos, no government styling, no implication of endorsement. The brief prohibits it and it would undermine the honesty position.

**7. Degrade gracefully.**
Designed first for a mid-range Android on a patchy connection. Text before graphics. Nothing essential behind an animation.

---

## 4. Surfaces

| Surface | Role | Priority |
|---|---|---|
| **Web chat** | Primary demo surface; the public link the brief requires | P0 |
| **Alert stream** | Where proactive messages land â same thread, visually distinct | P0 |
| **Journey card** | Persistent trip state, always reachable | P0 |
| **Demo time control** | Lets a reviewer trigger the delay scenario in 10 seconds | P0 |
| **Honesty panel** | In-product disclosure of what's real vs mocked | P0 |
| **WhatsApp framing** | Shown, not necessarily fully built â proves the reach argument | P1 |
| **MCP/API view** | A readable page listing the endpoints we're proposing | P1 |

> **Why the demo time control is P0:** a reviewer has two minutes. The flagship moment is a delay that would happen hours after booking. Without a way to jump forward, the best feature is invisible. This is a demo affordance, labelled as one â which itself reads as honesty rather than as a hack.

---

## 5. Conversation design

### 5.1 Voice

**Saarthi sounds like:** a competent friend who has done this many times, telling you what they'd do. Calm, specific, slightly terse. Never chirpy, never apologetic, never a customer-service robot.

| Do | Don't |
|---|---|
| "You'll miss it." | "Unfortunately, it appears you may not be able to make your connection." |
| "I'd take Option 2." | "Both options have their merits!" |
| "47 minutes left to file." | "Please note the deadline is approaching." |
| "Booked. SL/23, GNWL." | "Great news! ð Your booking is confirmed!" |
| "That's the catch." | "However, it should be noted that..." |

**Register rules:**
- Sentence case everywhere. No title case buttons.
- Rupee amounts always with â¹ and thousands separators: `â¹1,240`
- Train times in 24-hour (matches railway convention): `08:40`
- Relative time for anything urgent: `47 minutes from now`, not `at 23:14`
- Emoji: one per message maximum, only as a severity marker (ð´ ð¡ ðµ), never decorative
- Never apologise for the railway. Report, don't sympathise.

### 5.2 Turn structure

Every proactive message follows the same four-part shape. Consistency here is what makes it feel like a system rather than a chatbot:

```
[SEVERITY MARKER] What changed          â one line, factual
                  What it means for you  â the consequence, with numbers
                  What I recommend       â a position, not a menu
                  [Action] [Alternative] â at most two buttons
```

### 5.3 Language handling

**â¬ DECISION PENDING â currently specified as Option C + E from the scope discussion.**

**Specified default:**
- Accept input in English, Hinglish (Latin script), or Devanagari Hindi
- **Mirror the user's language in the reply.** If they write Hinglish, reply in Hinglish. This avoids privileging any one language â important given the finals are in Bengaluru.
- Never announce language support or offer a picker; just respond in kind
- Numbers, station codes, PNRs and â¹ amounts stay in Latin/numerals regardless of language

**Roadmap line (document only, do not build):** production would route translation through **Bhashini**, the government's own language stack, which RailMadad already uses for multilingual grievances â rather than a proprietary translation layer.

*If you'd rather flip this to English-only, the only change is removing the mirroring instruction from the system prompt. Nothing else in this document depends on it.*

---

## 6. Core flows

Each flow below gives the trigger, the exact dialogue, and the states involved. Dialogue is written as specification â Claude Code should treat the shape and tone as binding, and vary wording naturally.

---

### Flow A â Booking

**Trigger:** user opens the app, or types a travel intent.

**Cold open (empty state):**
> Where are you going?
>
> *Try: "Bengaluru to Varanasi on the 4th, 2 people"*

The empty state is an invitation with a worked example. No feature tour, no onboarding carousel.

**A1 â Intent parsed, ambiguity found**

> **Shantam:** bangalore to varanasi 4th sept, 2 people sleeper
>
> **Saarthi:** Bengaluru has four stations running long-distance trains. Varanasi services mostly leave from **SBC (KSR Bengaluru City)** or **YPR (Yesvantpur)**.
>
> I'll check both.

Note: it *tells* him the ambiguity exists and resolves it himself rather than blocking on a question. Only ask when a choice genuinely changes the outcome.

**A2 â No direct train (the real BengaluruâVaranasi situation)**

> **Saarthi:** No direct train on the 4th.
>
> The realistic route is a change at **Nagpur** â it's the standard interchange for this corridor.
>
> ðµ One thing to know up front: IRCTC can't book connected journeys. These will be two separate tickets, and if the first one runs late, the second one doesn't refund automatically. I'll watch both and tell you if that becomes a problem.
>
> **[Show me the connection]** **[Try other dates]**

**This message is doing heavy lifting.** It surfaces a structural limitation of IRCTC that no interface currently mentions, at the moment it becomes relevant â and it plants the setup for the flagship scenario. A judge watching the demo will remember this line when the delay hits.

**A3 â Options presented**

Present at most three. Each option is a compact card, not a table dump:

```
LEG 1 â SBC â Nagpur                    4 Sep
12295  Sanghamitra Express      20:00 â 06:15 (+1)
SL     GNWL/18                  â¹1,240 for 2
                                ð¡ Probable â 30-70%

LEG 2 â Nagpur â Varanasi               5 Sep
12539  NagpurâVaranasi Exp      08:40 â 21:10
SL     Available (26)           â¹1,890 for 2
                                ð¢ Confirmed

Layover at Nagpur: 2h 25m
```

> **Saarthi:** That layover is tight but workable â Nagpur's platforms are close together.
>
> The sleeper on leg 1 is GNWL/18. GNWL is the good kind of waitlist, it clears first, and 18 on this train usually clears â but not always. If you want certainty, 3A has 4 seats open for â¹840 more.
>
> **[Book sleeper]** **[Book 3A instead]**

---

### Flow B â Waitlist prediction

**Trigger:** any waitlisted option is displayed.

**Never show a bare number.** Always: band + one-clause explanation of the *type*.

| Band | Marker | Copy pattern |
|---|---|---|
| Confirm (>70%) | ð¢ | "Should clear. GNWL/8 on this train nearly always confirms." |
| Probable (30â70%) | ð¡ | "Could go either way. I'd have a backup." |
| Low (<30%) | ð´ | "I wouldn't. RLWL has a small separate quota and rarely clears this late." |

**On request, expand:**

> **Shantam:** why probable?
>
> **Saarthi:** Three things.
>
> **Waitlist type** â GNWL, the general queue. It clears before RLWL and PQWL because it draws from the full quota.
> **Position** â 18. This train's sleeper typically clears to around 22 on a normal week.
> **Timing** â 4 September is a normal week. Festival dates would push this to Low.
>
> RAC counts as confirmed, by the way â you'd get a seat, just shared.

**Honesty inline, on first prediction only:**

> ðµ These odds come from a synthetic dataset built to match published clearance patterns. IRCTC's real historical PNR data isn't publicly available to anyone outside IRCTC and CRIS.

---

### Flow C â Passenger details and payment

**Principle: never render a form.** Details come conversationally, in one turn where possible.

> **Saarthi:** Who's travelling? Name, age, and berth preference for each â one line each is fine.
>
> **Shantam:** Shantam 27 lower, Ravi 61 lower
>
> **Saarthi:** Ravi's 61 â that qualifies for the senior citizen lower-berth preference, which improves the allocation odds. I've applied it.
>
> Two sleeper berths, â¹1,240 total. Both lower requested.
>
> **[Pay â¹1,240]**

The senior-citizen catch is the moment the product proves it knows something the user doesn't. Small, cheap, memorable.

**Payment:**
- Mock UPI QR + a `Simulate payment` button
- Persistent label: `Demo payment â no money moves`
- On success, immediate state change and confirmation

> **Saarthi:** Booked.
>
> **PNR 8429516703** Â· 12295 Sanghamitra Exp Â· 4 Sep, 20:00
> SL Â· GNWL/18 and GNWL/19
>
> I'll watch this and tell you when it moves. Chart preparation is about four hours before departure â that's when it's final.

---

### Flow D â The alert engine (the spine)

This is the differentiator. It runs on journey state, not on user action.

#### Alert catalogue

| # | Trigger | Severity | Message shape | Action |
|---|---|---|---|---|
| D1 | WL position improves | ðµ | "GNWL/18 â GNWL/11. Moving well." | â |
| D2 | Chart prepared, confirmed | ð¢ | "Confirmed. S7, berths 23 and 24, both lower." | View ticket |
| D3 | Chart prepared, not confirmed | ð´ | "Didn't clear. Auto-cancelled, â¹1,180 refunding â you don't need to file anything." | Find alternatives |
| D4 | Platform assigned | ðµ | "Platform 6. Coach S7 is toward the rear â stand near the far end." | â |
| D5 | Halt approaching | ð¡ | "Bhopal in 40 min, 8-minute halt. Order by 13:50 to make it." | See food |
| D6 | Delay crosses 1h | ðµ | "Running 1h 5m late. Connection still fine." | â |
| D7 | Delay threatens connection | ð¡ | "Now 2h 10m late. Connection at 08:40 is getting tight â I'm watching it." | â |
| D8 | **Delay crosses 3h** | ð´ | **Full TDR flow â see Flow G/H** | File / decide |
| D9 | Retiring room becomes bookable | ðµ | "You're confirmed now, so the Nagpur retiring room is available. 8-hour gap overnight." | Check rooms |
| D10 | Approaching destination | ðµ | "Varanasi in 30 minutes." | â |
| D11 | Refund status change | ðµ | "TDR accepted. â¹1,240 expected in 45 days." | Track |

#### Alert design rules

- **Severity is never decorative.** ð´ means money or a deadline is at stake. ð¡ means act soon. ðµ is information. Never escalate for attention.
- **Never two alerts in a row without user input.** Batch them.
- **Every ð´ alert carries a countdown**, updating live.
- **Silence is valid.** If nothing changed, say nothing.

---

### Flow E â Catering, halt-aware

**Trigger:** approaching a station with e-catering, and enough time remains to order.

> ð¡ **Saarthi:** Bhopal in 40 minutes. The halt is 8 minutes at 13:58.
>
> To make that, order by **13:50**. Four places deliver to your coach here.
>
> **[See what's available]** **[Skip]**

On expand, list is filtered to *only what can actually arrive in time*. The filtering is the product; the list is commodity.

> **Saarthi:** These four can make the 13:50 cut-off. I've hidden two others that can't.
>
> The delivery code comes by SMS â the person hands it over at your seat.

---

### Flow F â Retiring room

**Trigger:** confirmed/RAC ticket + a layover over ~4 hours, or an arrival between 22:00 and 06:00.

> ðµ **Saarthi:** Your Nagpur gap is 8 hours overnight, 22:15 to 06:30.
>
> Retiring rooms are inside the station â you don't leave the premises. Non-AC double is â¹520 for 12 hours, AC is â¹1,150.
>
> Worth knowing: these need a confirmed or RAC ticket, which you now have. Waitlisted passengers can't book them.
>
> **[Book non-AC â â¹520]** **[Book AC â â¹1,150]** **[Skip]**

**Eligibility guard (build this):** if PNR status is WL, the offer never appears. If a reviewer asks about a waitlisted ticket, the answer is:

> Not yet â retiring rooms need a confirmed or RAC ticket. Yours is GNWL/18. If it clears at chart preparation I'll offer it then.

Enforcing a real rule the incumbent enforces is a cheap, high-value credibility signal.

---

### Flow G â TDR, the simple case

**Trigger:** delay crosses 3 hours, single-leg journey.

> ð´ **Saarthi:** 12295 is running **3h 20m late**.
>
> That crosses the 3-hour line, which means you can claim a **full refund of â¹1,240** â but only if you don't board, and only if I file before the train actually departs.
>
> **That's 47 minutes from now.** â± 46:58
>
> This is called a TDR â Ticket Deposit Receipt. Terrible name; it just means refund claim. Most people never file one because they don't know it exists.
>
> **[File it â full refund]** **[I'll travel anyway]**

**On filing:**

> **Saarthi:** Filed. Reference **TDR-4471902**.
>
> I selected reason code *"Train late by more than 3 hours, passenger did not travel"* â picking the wrong reason is the most common way these get rejected.
>
> TDR refunds take around 45 days. I'll tell you when it moves.

**The "don't file" case matters as much:**

> ðµ **Saarthi:** 12295 has been cancelled by Railways.
>
> You don't need to do anything. Cancelled trains refund automatically â â¹1,240 back in 5 to 7 days. Filing a TDR here would just add confusion.
>
> Want me to look at alternatives for the 4th?

---

### Flow H â The broken connection â­ **flagship**

**Trigger:** delay crosses 3 hours AND a downstream leg exists AND the connection is now unmakeable.

This is the moment the product justifies itself. Four rule systems, three deadlines, one recommendation.

> ð´ **Saarthi:** Your Nagpur train is **3h 20m late**. You'd arrive 09:35 instead of 06:15.
>
> Your Varanasi connection leaves at **08:40**. You'll miss it.
>
> I've worked through it. Two real options.
>
> ---
>
> **Option 1 â Abandon both**
> Leg 1: full refund, â¹1,240 â but I must file before departure. **47 minutes.**
> Leg 2: here's the catch. IRCTC treats these as unrelated tickets, so a missed connection isn't a valid refund reason. Ordinary cancellation applies â **â¹1,470 back of â¹1,890.**
> Retiring room: auto-cancels with the ticket, â¹520 back.
> **You recover â¹3,230 of â¹3,650. You don't travel.**
>
> **Option 2 â Travel late, rebook leg 2**
> There's a 14:20 NagpurâVaranasi, 6 sleeper seats, same â¹1,890.
> Keep leg 1. Cancel and rebook leg 2 â **â¹420 lost in charges.** Retiring room shifts to a daytime slot at no extra cost.
> **Extra cost â¹420. You reach Varanasi about 6 hours later than planned.**
>
> ---
>
> **I'd take Option 2.** You lose â¹420 instead of â¹420 in fees plus a trip you wanted to make â and you still get there today. Option 1 only makes sense if arriving tonight was the whole point.
>
> **[Option 2 â rebook]** **[Option 1 â refund everything]** **[Explain the leg 2 rule]**

**On "explain the leg 2 rule":**

> **Saarthi:** IRCTC has no concept of a connected journey. Two tickets on two trains are two unrelated contracts.
>
> So when leg 1 is late, leg 2's railway hasn't done anything wrong â no delay, no cancellation, no failure on their side. There's no refund reason that fits. You just cancel it like any other ticket and take the standard charge.
>
> This is one of the clearest gaps in how the system works. It costs people money on every missed connection in the country, and nothing in the current interface warns you before you book.

That last paragraph is the pitch, delivered inside the product. If a judge clicks one thing, it should be this.

---

### Flow I â Refund tracking and escalation

> **Saarthi:** TDR-4471902 â **accepted**. â¹1,240 expected by 8 October.
>
> If it hasn't landed by then, there's a ladder: RailMadad first, then the Railway Claims Tribunal or Ombudsman after 30 days, then consumer court. I'll flag it if the date passes.

Rarely seen in a two-minute demo, but its presence in the product is direct evidence for *end-to-end thinking*. Keep it reachable from the journey card.

---

## 7. Screen and component inventory

| Component | Purpose | Notes |
|---|---|---|
| **Chat thread** | Everything happens here | Agent messages, user messages, alerts interleaved |
| **Journey card** | Persistent trip summary | Sticky at top once booked. PNR, legs, status, countdown if any |
| **Option card** | A train option | Compact; band marker; never a spec table |
| **Alert message** | Proactive push | Left border in severity colour; visually distinct from replies |
| **Countdown chip** | Live deadline | Only on ð´ alerts. Monospace numerals |
| **Decision block** | Two named options with costs | Used by Flow H. The most designed element in the product |
| **Payment sheet** | Mock UPI QR | Permanent demo label |
| **Demo time control** | Jump journey state | Collapsed strip, bottom. Labelled `Demo controls` |
| **Honesty panel** | Real vs mocked | Reachable from header, always |
| **API surface page** | Proposed endpoints | Static page; the infra argument made visible |

### Demo time control â spec

A single collapsed strip, expandable:

```
Demo controls                                    â²
ââââââââââââââââââââââââââââââââââââââââââââââââââ
Jump to:  [ Chart prepared ]  [ Boarding day ]
          [ Delay 1h ]  [ Delay 3h+ â­ ]  [ Cancelled ]
Reset journey
```

`Delay 3h+` is marked as the recommended path. A reviewer with 90 seconds should be able to find the flagship moment without being told.

---

## 8. Journey state model

```
DRAFT
  ââ OPTIONS_SHOWN
       ââ PASSENGERS_ENTERED
            ââ PAYMENT_PENDING
                 ââ BOOKED_WL âââ¬â BOOKED_RAC âââ
                                ââ BOOKED_CNF âââ¤
                                                 â
                                          CHART_PREPARED
                                                 â
                    ââââââââââââââââââââââââââââââ¤
                    â                            â
              NOT_CLEARED                  PRE_DEPARTURE
            (auto-refund)                       â
                                    âââââââââââââ¼ââââââââââââ
                                    â           â           â
                              ON_TIME      DELAYED     CANCELLED
                                    â           â           â
                              IN_JOURNEY   TDR_WINDOW   AUTO_REFUND
                                    â           â
                               COMPLETED   TDR_FILED
                                                â
                                         REFUND_PENDING
                                                â
                                          REFUND_DONE
```

**Gates to enforce:**

| Gate | Rule |
|---|---|
| Retiring room offer | Only when `BOOKED_CNF` or `BOOKED_RAC` |
| TDR eligibility | Only when `DELAYED` â¥3h, or `CANCELLED`, or AC failure flag |
| TDR deadline | Before actual departure, for the delay case |
| Catering offer | Only when remaining time to halt > order cut-off |
| Connection risk | Recomputed on every delay update |
| Auto-refund notice | `NOT_CLEARED` or `CANCELLED` â suppress TDR offer entirely |

---

## 9. Edge and failure states

Failures are direction, not mood. Never apologise; say what happened and what to do.

| Situation | Copy |
|---|---|
| No trains found | "Nothing runs SBC â Varanasi direct on the 4th. The route works via Nagpur or Itarsi â want me to check those?" |
| Payment fails | "Payment didn't go through â no money left your account. Try again, or use a different method." |
| Deadline already passed | "The window for this one closed at 19:58. Nothing to file. Here's what the rules would have allowed, so it doesn't catch you next time." |
| Ambiguous intent | "Two things I need: the date, and where you're starting from." *(Ask for both at once, never one at a time.)* |
| Out of scope | "I only handle reserved train journeys â no flights, hotels or tour packages. For this trip, want me to check trains on the 5th instead?" |
| Backend error | "Couldn't reach the booking system. Your details are saved â try again in a moment." |

---

## 10. Honesty by design

The brief scores honesty explicitly. Most submissions will bury a disclaimer in a video. Put it in the product.

**Persistent header element:** `Demo â synthetic data` (quiet, always visible, opens the panel)

**Honesty panel content:**

> **What's real**
> The conversation, the reasoning, the eligibility rules, deadline logic, the alert engine, and the full API design.
>
> **What's mocked**
> Train inventory, PNRs, live delay data, payments, and the historical dataset behind confirmation odds.
>
> **Modelled from public documentation**
> TDR deadlines and reason codes, retiring-room eligibility, catering halt windows, waitlist quota behaviour. Sources disagree on some exact windows; we picked one consistent set.
>
> **What production would need**
> Registered IRCTC partner API access, and historical PNR outcome data â which isn't publicly available to anyone outside IRCTC and CRIS.
>
> **What we deliberately didn't do**
> No browser automation, no unofficial APIs, no contact with live railway systems.

**Inline disclosures** appear once, at first relevance â first prediction, first payment. Never repeated.

---

## 11. Visual direction

**Design brief:** a night-time, mobile, single-column messaging surface for someone standing on a platform. The subject's own materials are railway signage: high-contrast, glanceable, monospaced numerals, colour used strictly as a status code rather than decoration.

**The one risk worth taking:** treat the whole interface as **departure-board vernacular** â the flip-board typography and strict status colouring of a station indicator, applied to a chat surface. It is specific to this subject, it isn't a generic AI aesthetic, and it makes severity legible at a glance in exactly the situation the product is designed for.

**Palette** â status-first, dark by default (people book at night, on platforms, at low brightness):

| Token | Hex | Use |
|---|---|---|
| `--surface` | `#0E1116` | Background |
| `--raised` | `#171C24` | Cards, agent messages |
| `--ink` | `#E8EAED` | Primary text |
| `--ink-dim` | `#9AA3AF` | Secondary, timestamps |
| `--signal-go` | `#3FB950` | Confirmed, good odds |
| `--signal-wait` | `#D29922` | Probable, act soon |
| `--signal-stop` | `#E5534B` | Deadline, money at risk |
| `--rail` | `#2D3742` | Dividers, borders |

**Type:**
- **Display / numerals:** a mono or semi-mono face for times, PNRs, â¹ amounts, countdowns â `JetBrains Mono` or `IBM Plex Mono`. Numerals must be tabular so countdowns don't jitter.
- **Body:** `Inter` or `IBM Plex Sans` â neutral, excellent Devanagari coverage if Hindi input is enabled.
- Type scale tight and small; this is a utility, not a landing page.

**Layout:**
- Single column, max 520px, centered
- Agent messages left-aligned on `--raised`; user messages right-aligned, no bubble fill
- Alerts: full-width, 3px left border in the severity colour, slightly inset
- Journey card sticky at top, collapses to one line on scroll

**Motion:** almost none. One exception â the countdown ticks, and the decision block fades in over ~200ms so it reads as arriving rather than appearing. Respect `prefers-reduced-motion`.

**Quality floor, unannounced:** responsive to 360px, visible keyboard focus, contrast â¥4.5:1, works with text-only if images fail.

---

## 12. Data model sketch

Entities the mock backend needs. Not a schema â a checklist.

| Entity | Key fields |
|---|---|
| `Station` | code, name, city, aliases, tier |
| `Train` | number, name, class availability, days of operation |
| `Schedule` | trainId, stationCode, arrival, departure, **haltMinutes**, day offset |
| `Availability` | trainId, date, class, quota, seats or WL position |
| `WaitlistModel` | trainId, class, quota, typical clearance ceiling, seasonal modifier |
| `PNR` | number, trainId, date, passengers, status, berths |
| `Passenger` | name, age, berth preference, concession flags |
| `LiveStatus` | trainId, date, current delay minutes, last station, platform |
| `CateringVendor` | stationCode, name, cutoff minutes, menu, price band |
| `RetiringRoom` | stationCode, type, tariff, min/max hours, availability |
| `TDRRule` | reason code, label, deadline rule, refund basis, needs certificate |
| `TDRClaim` | id, pnr, reason code, filed at, status, expected date |
| `JourneyPlan` | legs[], interchange, layover minutes, linked retiring room |
| `AlertRule` | trigger condition, severity, template, action |

**`JourneyPlan` is the one that matters.** It's what IRCTC doesn't have â the object that knows two tickets are one trip. Every flagship behaviour derives from it.

---

## 13. Build sequence

Aligned to the agreed priority. Each stage is independently demo-able.

| Stage | Deliverable | Demo state if you stop here |
|---|---|---|
| **1** | Mock backend + chat + booking | A working conversational booking demo |
| **2** | Waitlist prediction + explanation | A demo with a real differentiator |
| **3** | Alert engine + single-leg TDR | **The money shot** â proactive refund rescue |
| **4** | `JourneyPlan` + broken-connection reasoning | The standout scenario |
| **5** | Retiring room + catering timing | The complete journey |

Stages 1â3 constitute a submittable product. 4â5 are upside, and legitimate work for the mentorship week if needed.

---

## 14. Open decisions

| # | Decision | Default in this doc |
|---|---|---|
| 1 | Product name | `Saarthi` |
| 2 | Language handling | Mirror user's language + Bhashini as roadmap |
| 3 | Exact TDR window set | Delay case = before actual departure; state as modelled simplification |
| 4 | Whether to build WhatsApp surface or only show it | Show it; build if time |
| 5 | Dark-only or light theme too | Dark only |

---

## 15. Explicitly out of scope

IRCTC Tourism, IRCTC Air, hotels, cabs, parcels and freight, unreserved and platform tickets, seat-map selection, PNR sharing, group bookings above 6, counter-ticket handling.

Each gets one line in the roadmap section of the submission write-up. None gets built.

---

## Appendix â copy bank

Lines worth keeping consistent wherever they recur:

- "GNWL is the good kind of waitlist â it clears first."
- "TDR â Ticket Deposit Receipt. Terrible name; it just means refund claim."
- "You don't need to do anything. This one refunds automatically."
- "IRCTC has no concept of a connected journey."
- "Picking the wrong reason is the most common way these get rejected."
- "I'll watch this and tell you when it moves."
- "Retiring rooms need a confirmed or RAC ticket."
- "Demo payment â no money moves."
