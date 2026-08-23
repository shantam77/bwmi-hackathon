# IRCTC Agent â Research & Context Log

**Project:** Build What Moves India (BWMI) hackathon submission
**Compiled:** 23 August 2026
**Purpose:** Single reference for every fact, rule and constraint uncovered during discovery. Use this while building so nothing has to be re-researched, and so claims made in the pitch/video are defensible.

> **Confidence key used throughout:**
> â **Verified** â confirmed against a source during research
> â ï¸ **Directional** â trend is well-supported, exact figure varies by source
> â **Unverified** â assumption, needs checking before it goes in the pitch

---

## 1. The hackathon brief â hard requirements

Source: https://buildwhatmovesindia.com/brief

### Deadlines and process
| Item | Detail |
|---|---|
| Submission deadline | **28 August 2026, 8:00 PM IST** â no grace period |
| Stage 1 review | 28 Aug â 1 Sep, top **250** shortlisted |
| Stage 2 | One week of mentorship (WhatsApp group, 5 mentors + OpenAI team), resubmit by **7 Sep 2026** |
| Finalists | 10 announced 8â12 Sep; live presentation in **Bengaluru, 12 Sep 2026** |

### â ï¸ Non-negotiable build requirement
The prototype **must be built with Codex or powered by an OpenAI model**. The brief explicitly states Codex should be a meaningful part of how it is built, not bolted on for the submission. The second minute of the demo video is reserved for explaining how it was built â expect to be asked.

### What must be submitted
- Live public link, opens in a browser with **no access request**. Include mock login credentials if needed.
- **One video, max 2 minutes.** Minute 1 = demo as a citizen. Minute 2 = how it was built and why.
- Project summary **under 250 words**.
- Partner's registered email if a team of two.

### Judging criteria (design the pitch against these six)
1. **Problem** â is it real and important?
2. **Working build** â does the main journey actually work end to end?
3. **Usability** â simpler, clearer, more accessible?
4. **Product thinking** â are choices thoughtful and well explained?
5. **End-to-end thinking** â does it address backend, infrastructure and process, not just UI?
6. **Honesty** â are limitations, mock data and dependencies clearly disclosed?

### Explicit prohibitions
- â Accessing, testing or interfering with a live government system
- â Reverse-engineering private systems or using undocumented private APIs
- â Scraping personal or restricted information
- â Real Aadhaar, PAN, passwords, OTPs, payment details, health data
- â Presenting the prototype as an official government product
- â Government logos implying approval or partnership
- â Resubmitting an old project with minor changes

### Explicitly encouraged
- Mock data, mock accounts, mock backend behaviour wherever production access would be unsafe or unavailable
- Design for real Indian users: mobile devices, slower connections, limited digital experience
- Reviewers test the **citizen experience**, not an admin panel

---

## 2. Competitive landscape â the two findings that most shape positioning

### â Finding 1: AskDISHA â IRCTC already has a conversational booking assistant

**This is the most directly competitive thing we found, and it predates our idea by eight years.**

- **AskDISHA** â "Digital Interaction to Seek Help Anytime" â deployed by IRCTC in **October 2018**. India's first AI chatbot by a public sector enterprise.
- Built by **CoRover**, a conversational AI company; powered by Microsoft Azure architecture.
- **AskDISHA 2.0** added conversational *booking*, not just queries â via **voice, chat and click**, with **OTP instead of a password**.

**What it already does:**
- Books train tickets conversationally
- PNR status and search
- Cancels tickets
- Changes boarding station
- Checks refund status
- Answers Tatkal timing and general travel queries
- **Probability of ticket confirmation** â ï¸ â we had treated this as a differentiator; it is not
- Understands **English, Hindi and Hinglish**
- Covers IRCTC's travel and tourism offerings too

**Scale:** ~150,000 passenger queries daily at ~90% accuracy; ~178 million passengers served across ~10 billion interactions. Won the Asia Leadership Award for Innovation Using Technology 2019. IRCTC's then-CMD publicly projected 25% of customers shifting to conversational booking.

#### â ï¸ Why this is urgent
An IRCTC-affiliated judge will know AskDISHA. **If the pitch is "natural language instead of forms," the answer is "we shipped that in 2018."**

#### ð¯ But the differentiator survives â and sharpens
AskDISHA is a **query-answering assistant**. Everything it does is **reactive**: the user asks, it answers. Nothing found in any source indicates it:

| Capability | AskDISHA | Us |
|---|---|---|
| Conversational booking | â since 2018 | â (table stakes) |
| Confirmation probability | â | â (supporting, not headline) |
| Refund *status* lookup | â | â |
| **Speaks first on state change** | â | â |
| **Detects a delay has started a refund clock** | â | â |
| **Computes TDR eligibility, deadline, reason code** | â | â |
| **Files a TDR** | â | â |
| **Knows two tickets are one journey** | â | â |
| **Reasons across a broken connection** | â | â |
| **Gates retiring room on PNR status** | â | â |
| **Cross-references halt duration with catering cut-off** | â | â |

**Revised one-line pitch:**
> IRCTC has had conversational booking since 2018. What it has never had is an agent that *watches* your journey and speaks first â before the refund deadline you didn't know existed expires.

**Action: name AskDISHA in the demo video.** Turning the strongest objection into evidence that you know the domain is the cheapest available point on *Product thinking*.

### â Finding 2: RailOne already exists and already consolidated the apps

The second finding that reshapes positioning.

- Launched **1 July 2025** by Indian Railways, developed by **CRIS** (Centre for Railway Information Systems).
- Consolidates **IRCTC Rail Connect + UTS on Mobile + NTES + Rail Madad + Food on Track** into one app.
- Covers: reserved and unreserved booking, platform tickets, live train tracking, PNR status, **coach position finder**, food ordering, complaint registration, refunds.
- Integrated with **R-Wallet** (3% discount on unreserved tickets), DigiLocker linking, biometric/mPIN login, multilingual support.
- Already ships **AI-powered chat support**.
- **2 crore+ downloads** within roughly six months.
- **From 1 March 2026, UTS on Mobile was shut down entirely** â RailOne became the sole official app for reserved and unreserved tickets.
- Aadhaar linking is optional but raises the monthly booking limit and speeds verification.

### â ï¸ But the execution is widely criticised
Public App Store reviews report:
- Poorly designed; basic functions hard to find (e.g. a user could not locate Mumbai local ticket booking, which was straightforward in the old UTS app)
- The Rail Madad complaint feature described as dysfunctional
- A character limit that prevents users describing their actual problem
- Support staff perceived as lacking basic railway system knowledge

### ð¯ Combined positioning â what both findings mean

Two claims are now **off the table**, because the incumbents already made them:

| â Don't pitch | Why not |
|---|---|
| "The apps are fragmented" | RailOne officially solved this in July 2025 |
| "Booking should be conversational" | AskDISHA shipped this in October 2018 |

What remains, and what is genuinely unclaimed:

> They merged five apps into one and the menus got deeper. They've had a conversational booking bot for eight years. Neither of them ever *watches*. Every failure in this system is a moment where the railway already had the data and simply didn't speak â a delay that started a refund clock, a halt too short to order food, a confirmation that just unlocked a room you could sleep in. We built the part that speaks first.

**Action: name both RailOne and AskDISHA in the demo video.** Command of the incumbent landscape is the cheapest available evidence for the *Product thinking* criterion, and it pre-empts the single most likely objection from the panel.

**Also note the pattern:** Railways has attempted app consolidation at least three times (Rail Saarthi 2022, SwaRail, RailOne 2025) and has run a conversational assistant since 2018. Repeated attempts that don't resolve the underlying frustration are evidence that the problem was never app count or input modality. It is that the system is **entirely pull-based** â it answers, but it never initiates.

### Other apps in the ecosystem (mostly now absorbed)
| App | Function |
|---|---|
| IRCTC Rail Connect | Reserved tickets (booking window 07:00â23:00) |
| UTS on Mobile | Unreserved/platform tickets â **discontinued 1 Mar 2026** |
| NTES | Live running status, delays, diversions, cancellations (info only) |
| RailMadad | Grievances â helpline **139** |
| IRCTC eCatering / Food on Track | Food by PNR |
| SwaRail | Earlier super-app attempt, same consolidation goal |
| Rail Saarthi | 2022 single-window attempt |
| R-Mitra | Security/crime helpline, coach panic button |

**Note the pattern:** Railways has attempted app consolidation at least three times (Rail Saarthi 2022, SwaRail, RailOne 2025). Repeated attempts suggest the underlying problem is not app count â it is interaction model. That is a strong argument for our thesis.

---

## 3. Legal and access constraints â what we must NOT do

### â Automating the live IRCTC site is off the table
- Indian Railways deployed **anti-bot systems plus a CDN partnership** specifically to block automated bookings by agents.
- Bot traffic used to spike in the **first five minutes of Tatkal**, at times up to **50% of login attempts**.
- **2.5 crore suspected unauthorised user IDs deactivated.**
- IRCTC has historically reported named Tatkal-automation software services to authorities.
- Unauthorised ticket automation/touting has drawn criminal charges under **Section 143 of the Railways Act**.
- IRCTC agent agreements explicitly bar unauthorised booking software and dummy passenger profiles, with financial penalties and permanent debarment.

**Consequences for us:** a browser-automation demo would likely be blocked live on stage, and sits in a legally grey area. Ruled out. This aligns with the brief's own prohibition on touching live government systems.

### â Official API access is real but not obtainable for a hackathon
- IRCTC does run a **registered developer/partner API programme** â apply as a business, state purpose, get approved, paid tiers. This is how ixigo/ClearTrip/Trainman operate.
- It is a weeks-to-months B2B commercial process. Not accessible on our timeline.
- Most "IRCTC API" results (RapidAPI, allthingsdev, GitHub scrapers) are **unofficial third-party wrappers** â using these would violate the brief's ban on undocumented private APIs.

### ð¯ Our resulting architecture stance
We design and implement **our own mock API / MCP server** representing what a clean, agent-friendly IRCTC interface *should* expose. The agent only ever talks to our mock.

**Pitch line:** *"We are not touching live IRCTC infrastructure. Here is the API surface Indian Railways would need to expose for the agentic era â and here is our working simulation of it."* This answers **End-to-end thinking** and **Honesty** simultaneously.

---

## 4. Waitlist confirmation prediction

### â This is a proven, established product category â not speculative
- **ConfirmTkt** built its business on exactly this: analysing historical ticketing trends to predict confirmation chances.
- It maintains a **"confirmation threshold" per train** â the waitlist level beyond which confirmation becomes unlikely â dependent on class of travel, past trends, and month of travel.
- Modern versions use ML over historical booking patterns, past cancellations, quota types and seasonality, cross-referenced with day of week, festivals and major holidays.
- **IRCTC's own site now displays a probability percentage directly.** Independent tools benchmark themselves against it.

### â Industry-standard output format â copy this
| Band | Range | Advice given |
|---|---|---|
| Confirm | **>70%** | High chance â go ahead and book |
| Probable | **30â70%** | Medium â book at your own risk |
| Low Chance | **<30%** | Low â advised not to book |

Notes: **RAC is treated as confirmed** for prediction purposes. Tatkal predictions are generally not offered.

### â The factors that actually drive it
- **Waitlist type** â this matters most:
  - **GNWL** (General Waitlist) â confirms first and fastest
  - **RLWL** (Remote Location Waitlist) â separate, smaller quota, confirms slower
  - **PQWL** (Pooled Quota Waitlist)
  - **TQWL** (Tatkal Waitlist) â worst odds
- Waitlist number/position
- Route demand
- Travel class
- Season / festival periods

### â ï¸ The data problem â and how we handle it honestly
Real historical PNR-outcome data is **not publicly available**; ConfirmTkt's own founders have described obtaining it as one of their biggest challenges. Only IRCTC/CRIS hold it.

**Our approach:** generate a synthetic dataset calibrated to the publicly documented patterns above (GNWL clears faster than RLWL, festival periods clear slower, closer-to-departure behaves differently), then compute the same three bands.

**Exact sentence for the video:**
> "This models the same approach ConfirmTkt and RailYatri use commercially â waitlist type, position and seasonality against historical clearance patterns. Real IRCTC historical data isn't publicly available, so we generated a synthetic dataset calibrated to those known patterns for the demo."

That one sentence covers *Problem understanding*, *Honesty*, and *End-to-end thinking*.

---

## 5. TDR â Ticket Deposit Receipt (our flagship feature)

### What it is
The formal refund claim mechanism used when the **Railways caused the disruption** and normal cancellation rules don't apply. Governed by the Railways (Cancellation of Tickets and Refund of Fare) Rules 2015, read with the Indian Railways Conditions of Carriage 1990.

**The name itself is a UX failure** â "Ticket Deposit Receipt" gives no hint that it means "refund claim." Worth saying in the pitch.

### â When a TDR applies
- Train cancelled by Railways
- Train delayed **more than 3 hours** and passenger chooses not to travel
- **AC failure** in an AC coach
- **Class downgrade** due to inadequate or damaged coach facilities
- Train terminated short of destination / diverted

### â Filing path (current UI)
`irctc.co.in` â login â **My Account â My Transactions â File TDR** â select PNR â select reason from dropdown â select affected passengers â submit â track under My Transactions.

### â The deadlines â savage and reason-specific
| Scenario | Deadline |
|---|---|
| Train 3+ hrs late, not travelling | **Before the train's actual departure** from boarding station |
| Travelled in lower class than booked | Within **3 hours** of actual departure |
| Other general cases | Within **72 hours** of scheduled arrival at destination |
| Train fully cancelled by Railways | No time limit (and usually auto-refunded anyway) |

â ï¸ Sources vary slightly on some windows (one cites a ~4-hour general rule, another 30 minutes before departure for the delay case). **Before the pitch, pick one consistent rule set for the mock and state that it's a modelled simplification.**

### â Why claims fail â the core of our value proposition
1. **Even one minute late disqualifies a valid claim.**
2. **Only one TDR per PNR** â must choose which passengers it covers if partially used.
3. **Wrong dropdown reason = denial.** Same event, wrong label, no money.
4. **Most refund failures come from incorrect user action, not system failure.** IRCTC does not auto-resolve stuck refunds.
5. **Without filing a TDR, there is simply no refund** for a delayed train â if you don't know the feature exists, you silently lose the fare.
6. **Some cases need physical paperwork** â AC failure or termination may require a **TTE certificate physically mailed** to IRCTC; the clock only starts once received and verified.
7. **False claims can trigger legal action or IRCTC ID cancellation.**

### â When you should NOT file (half the value is telling people this)
- Train **fully cancelled** by Railways â refund is automatic
- **Waitlisted ticket never confirmed** after chart preparation â auto-cancelled, refund automatic (minus ~â¹60 e-ticket service charge)
- **Tatkal waitlist** not confirmed â auto-refunded, typically within 5 days, no TDR needed

### â Refund timelines
| Path | Timeline |
|---|---|
| IRCTC iPay wallet | Instant to 24 hrs |
| UPI / net banking / debit card | 5â10 working days |
| Credit card | Up to ~21 days |
| **TDR cases** | **~45 days** |
| Statutory wait before escalation | **60 days** |
| Counter bookings | 3â5 working days post-cancellation |

### â Escalation ladder (great material for the "what happens next" part of the flow)
RailMadad â (if unresolved in ~30 days) Railway Claims Tribunal / Railway Ombudsman â CPGRAMS â RTI Act 2005 â Consumer court under CPA 2019 (e-Daakhil; NCDRC accepts joint complaints naming both IRCTC and Railways) â National Consumer Helpline 1800-11-4000.

### ð¯ The agent framing
Every input needed is already known to the system: train delay, PNR, correct reason code, deadline. It just never acts.

> ð "Train 12628 is running 3h 20m late. You're eligible for a full refund if you don't travel â deadline is before departure, about 40 minutes from now. Want me to file the TDR? I'll select the correct reason code."

---

## 6. Retiring rooms

### â Eligibility rules (must be respected in the mock â judges may know these)
- **Confirmed (CNF) or RAC PNR only.** Waitlisted tickets are explicitly **not** eligible.
- **One booking at source station + one at destination station, per PNR.**
- Duration: **minimum ~3â12 hours, maximum 48 hours** (varies by station; hourly booking only at some).
- Advance booking: up to ~30â60 days, generally until ~4 hours before departure.
- **Minimum age 12** to check in.
- Occupants must match the number of passengers on the PNR.
- Valid photo ID required at check-in.
- Available at **major stations only**; smaller stations may be counter-booking only.
- Booked via the separate portal **rr.irctc.co.in** â i.e. *another* site the user has to discover.

### â Cancellation and edge rules
- Auto-cancelled within 96 hours of check-in if the train ticket is cancelled
- No refund for same-day cancellation / within 12 hours of check-in
- Late check-in extended up to 1 hour after train arrival
- Combined slots over 24 hrs (12+24, 24+12, 24+24) â second slot treated as an extension, **+25% tariff**
- Failure to check in attracts the full cost of stay

### â ï¸ Indicative tariffs (for realistic mock data)
| Type | Range |
|---|---|
| Non-AC dormitory | â¹200â400 / 12 hrs |
| Non-AC private room | â¹400â800 / 24 hrs |
| AC private room | â¹800â2,500 / 24 hrs |

Rates vary by station tier â New Delhi and Mumbai higher, smaller stations lower.

### ð¯ Why it fits our agent
The canonical use case is: *"my train arrives at 1 AM and my next one is at 9 AM â where do I go?"* Our agent already knows arrival time, ticket status, and layover length, so it can **proactively** offer a room only when eligible and actually useful. Suppressing the offer for WL tickets is a cheap credibility signal.

---

## 7. E-catering / food

### â How it works today
- Order by **PNR**, delivered to your seat/coach at a chosen station during the halt.
- Available at **300+ stations**, 3,000â10,000+ trains depending on provider.
- Restaurants must be **FSSAI-approved**; IRCTC issues a **delivery code** by SMS/email.
- Users are advised to order **in advance of the delivery station**.
- Order tracking, free cancellation before preparation begins, coach change supported.

### â ï¸ The fragmentation problem
At least four competing partner front-ends: **Zomato, RailRestro, ECatering.app, RelFood**, plus IRCTC's own Food on Track. Each requires separately entering PNR/train/station.

### ð¯ Our angle
Nobody cross-references **halt duration** against **order cut-off time**. Our agent already knows the route and schedule:

> "You have 8 minutes at Jhansi at 2:15 PM. Order by 1:50 PM for it to reach your coach in time."

---

## 8. Full journey map â every touchpoint and its pain

### Stage 1 â Planning & discovery
| Touchpoint | Pain |
|---|---|
| Station search | Ambiguous names ("Delhi"?), code vs. name confusion |
| Availability | Raw numbers, no interpretation |
| Quota maze | GNWL/RLWL/PQWL/TQWL differences largely unknown to users |
| **Connecting journeys** | ð¥ **IRCTC has no facility to book two connecting trains â and no refund if the connection breaks.** Structural white space. |
| Concessions | Senior citizen, Divyangjan, patient quotas â buried, poorly explained |

### Stage 2 â Booking
- Master passenger list / saved travellers
- **Payment failure and double-debit** â money gone, no ticket
- Berth preference logic (lower berth for elderly) â allocation rules opaque
- Aadhaar linking optional but raises monthly booking limit â poorly communicated

### Stage 3 â Post-booking, pre-travel
- PNR status and chart preparation timing
- Alerts: waitlist movement, chart prepared, platform number, delays
- Retiring rooms (CNF/RAC only)
- Cancellation windows and charges
- **TDR**

### Stage 4 â Day of travel
- Live running status, delay, diversion
- **Platform number + coach position** â the classic luggage sprint
- Boarding point change
- Food ordering vs. halt duration
- **Destination alert / wake-up alarm** â genuinely exists via the **139** service (along with wheelchair booking and meal booking) and is almost unknown

### Stage 5 â Onboard
- RailMadad complaints: cleanliness, staff behaviour, catering, technical
- **AC failure / class downgrade â TDR-eligible, but needs a TTE certificate**
- Security â R-Mitra panic button

### Stage 6 â Post-journey
- Refund tracking and escalation
- Booking history, GST invoices for business travel
- Grievance escalation ladder

---

## 9. Scale context (useful for the pitch)

| Metric | Figure |
|---|---|
| IRCTC registered users | ~66 million (Dec 2023) |
| Daily tickets booked | ~7.31 lakh/day average |
| Daily rail passengers | ~2.3 crore |
| Daily waitlisted tickets | ~7.9 lakh (of ~22 lakh booked) |
| Peak booking rate achieved | ~32,000 tickets/minute |
| RailMadad grievances | 10,000+ registered daily; helpline 139 is 58%+ of complaints |
| IRCTC ownership | Government of India ~62.4% |

â ï¸ Several of these are from different years â date-stamp any figure used in the video.

---

## 10. Open questions to resolve before building

1. **Codex/OpenAI usage** â how will Codex be a meaningful part of the build, and what is the one-sentence answer for minute two of the video?
2. **Which TDR rule set** do we implement, given source disagreement on exact windows?
3. **Scope lock** â which Tier 1 features make the demo, and which are "mentioned as roadmap"?
4. **Demo persona** â who is the user in the video? A named, specific persona lands better than "a user."
5. **Time simulation** â the delay/TDR/alert flow needs a way to fast-forward time in the demo. Needs a deliberate design decision.
6. **Language support** â Hindi/Hinglish input is a strong accessibility signal for "designed for real Indian users." In or out?

---

## Source index

| Topic | Key sources |
|---|---|
| Brief | buildwhatmovesindia.com/brief |
| Anti-bot enforcement | Ministry of Railways statements, newsonair.gov.in, Upstox, IRCTC agent declarations |
| API access | IRCTC partner programme documentation, RapidAPI/allthingsdev listings (third-party) |
| Waitlist prediction | ConfirmTkt (offline-prediction page, founder interviews via Inc42/YourStory/KNN), RailTC, RailWise |
| TDR | Business Standard, redBus/redRail guide, righttoinformation.wiki, citizennest, irctconline.in |
| Retiring rooms | rr.irctc.co.in terms & conditions, RailMitra, RailAdda, LastBerth, PNR Alert |
| E-catering | ecatering.irctc.co.in, Zomato train-food page, RailRestro |
| RailOne | Deccan Herald, Gulf News, The News Mill, GoodReturns, Apple App Store reviews |
| AskDISHA / CoRover | IndiaAI (Ministry of Railways initiatives page; AskDISHA 2.0 announcement; "On the right track" AI/NLP article incl. CoRover founder interview) |
| Scale figures | Wikipedia (IRCTC), IndiaAI (RailMadad), Ministry of Railways |
