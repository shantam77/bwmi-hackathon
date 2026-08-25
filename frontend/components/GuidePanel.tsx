"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

interface Stop {
  station_code: string;
  sequence: number;
  arrival: string | null;
  departure: string | null;
  day_offset: number;
}
interface TrainRoute {
  number: string;
  name: string;
  classes: string[];
  corridor: "flagship" | "filler";
  stops: Stop[];
}
interface StationInfo {
  code: string;
  name: string;
  city: string;
  tier: string;
}
interface NetworkResponse {
  stations: StationInfo[];
  trains: TrainRoute[];
}
interface Edge {
  a: string;
  b: string;
  corridor: "flagship" | "filler";
  trains: string[];
}

// Hand-placed, not force-directed -- with only 21 routed stations the goal
// is a diagram that reads as "one real corridor, plus the rest of the
// network," not a physically accurate map. Flagship stations (the two
// corridors this demo's data is actually built around, SBC/YPR-NGP and
// NGP-BSB) sit in the upper band, left to right in real travel order;
// everything a filler (2-stop, hub-to-hub) train touches sits in a looser
// lower band. Any station the live data doesn't include here (there are 17
// alias-only stations in stations.json with no train at all) is simply
// skipped when rendering, rather than guessing a position for it.
const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
  YPR: { x: 55, y: 205 },
  SBC: { x: 55, y: 270 },
  GTL: { x: 165, y: 235 },
  WADI: { x: 270, y: 200 },
  SUR: { x: 375, y: 170 },
  WR: { x: 475, y: 145 },
  NGP: { x: 585, y: 125 },
  G: { x: 680, y: 145 },
  KTE: { x: 760, y: 170 },
  MKP: { x: 825, y: 205 },
  ALD: { x: 875, y: 245 },
  BSB: { x: 905, y: 295 },

  NZM: { x: 150, y: 415 },
  PUNE: { x: 300, y: 435 },
  SC: { x: 380, y: 462 },
  MAS: { x: 460, y: 438 },
  NDLS: { x: 560, y: 392 },
  BCT: { x: 660, y: 432 },
  HWH: { x: 745, y: 398 },
  CSMT: { x: 830, y: 440 },
  DLI: { x: 890, y: 402 },
};

const GRAPH_VIEWBOX = "0 0 960 500";

// ALD sits at the corridor's steepest bend (MKP -> ALD -> BSB) -- a
// straight-below label lands almost on top of the ALD-BSB line. Pull it left
// instead. No other node needs an override at the current layout.
const LABEL_OFFSETS: Record<string, { dx: number; anchor: "start" | "middle" | "end" }> = {
  ALD: { dx: -12, anchor: "end" },
};

function buildEdges(trains: TrainRoute[]): Edge[] {
  const map = new Map<string, Edge>();
  for (const t of trains) {
    for (let i = 0; i < t.stops.length - 1; i++) {
      const a = t.stops[i].station_code;
      const b = t.stops[i + 1].station_code;
      const key = [a, b].sort().join("-");
      const existing = map.get(key);
      if (existing) {
        existing.trains.push(t.number);
      } else {
        map.set(key, { a, b, corridor: t.corridor, trains: [t.number] });
      }
    }
  }
  return [...map.values()];
}

function routeLabel(t: TrainRoute, stationName: (code: string) => string): string {
  return t.stops.map((s) => stationName(s.station_code)).join(" → ");
}

// Labelled "Reference", not "Guide" -- on a narrow screen this sits right
// next to the outer Application/Guide pane switcher, and two controls both
// saying "Guide" on screen at once is exactly the kind of ambiguity this
// whole feature exists to avoid.
const TABS = [
  { id: "guide", label: "Reference" },
  { id: "tutorial", label: "Tutorial" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export default function GuidePanel() {
  const [data, setData] = useState<NetworkResponse | null>(null);
  const [error, setError] = useState(false);
  const [tab, setTab] = useState<TabId>("guide");

  useEffect(() => {
    apiFetch("/api/network")
      .then((res) => res.json())
      .then(setData)
      .catch(() => setError(true));
  }, []);

  const stationName = (code: string) => data?.stations.find((s) => s.code === code)?.name ?? code;
  const edges = data ? buildEdges(data.trains) : [];
  const routedCodes = new Set(edges.flatMap((e) => [e.a, e.b]));
  const nodes = [...routedCodes]
    .filter((code) => NODE_POSITIONS[code])
    .map((code) => ({ code, ...NODE_POSITIONS[code] }));

  const flagshipTrains = data?.trains.filter((t) => t.corridor === "flagship") ?? [];
  const fillerTrains = data?.trains.filter((t) => t.corridor === "filler") ?? [];

  return (
    <div className="flex min-w-0 flex-col gap-9 p-5 text-sm">
      <section className="flex flex-col gap-1.5">
        <h2 className="text-ink text-base font-semibold">What you&apos;re looking at</h2>
        <p className="text-ink-dim leading-relaxed">
          Saarthi is a conversational agent for Indian Railways -- it plans, books, and then{" "}
          <em>keeps watching</em> a journey after booking, speaking up on its own when something
          changes (a delay, a chart clearing, a broken connection), rather than waiting to be
          asked. Everything on this page describes the mock data and demo mechanics behind the
          chat panel; nothing here is live railway data.
        </p>
      </section>

      <div className="border-rail flex gap-1 border-b">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`-mb-px border-b-2 px-3 py-2 text-xs font-medium transition-colors ${
              tab === t.id
                ? "border-accent text-accent"
                : "text-ink-dim border-transparent hover:text-ink"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && (
        <p className="text-signal-stop text-xs">Couldn&apos;t reach the backend just now.</p>
      )}

      {data && tab === "guide" && (
        <>
          <section className="flex min-w-0 flex-col gap-2">
            <h2 className="text-ink text-sm font-semibold">The rail network in this demo</h2>
            <p className="text-ink-dim text-xs leading-relaxed">
              Two real, fully-scheduled corridors -- Bengaluru to Nagpur, and Nagpur to Varanasi
              -- are what everything else in this demo is built around (they&apos;re what makes a
              connecting journey through Nagpur possible). The rest of the network exists only as
              simple point-to-point trains between major hubs, for search realism.
            </p>
            <div className="border-rail bg-raised overflow-x-auto rounded border p-3">
              <svg
                viewBox={GRAPH_VIEWBOX}
                width={640}
                height={333}
                role="img"
                aria-label="Rail network graph"
              >
                {/* Filler edges drawn first, so flagship edges always sit
                    visually on top at any crossing. */}
                {edges.filter((e) => e.corridor === "filler").map((e) => {
                  const from = NODE_POSITIONS[e.a];
                  const to = NODE_POSITIONS[e.b];
                  if (!from || !to) return null;
                  const mx = (from.x + to.x) / 2;
                  const my = (from.y + to.y) / 2;
                  return (
                    <path
                      key={`${e.a}-${e.b}`}
                      d={`M ${from.x} ${from.y} Q ${mx} ${my + 34} ${to.x} ${to.y}`}
                      fill="none"
                      stroke="var(--rail)"
                      strokeWidth={1.5}
                      strokeLinecap="round"
                    >
                      <title>
                        {stationName(e.a)} ↔ {stationName(e.b)} &middot;{" "}
                        {e.trains.length} train{e.trains.length > 1 ? "s" : ""}
                      </title>
                    </path>
                  );
                })}
                {edges.filter((e) => e.corridor === "flagship").map((e) => {
                  const from = NODE_POSITIONS[e.a];
                  const to = NODE_POSITIONS[e.b];
                  if (!from || !to) return null;
                  return (
                    <path
                      key={`${e.a}-${e.b}`}
                      d={`M ${from.x} ${from.y} L ${to.x} ${to.y}`}
                      fill="none"
                      stroke="var(--accent)"
                      strokeWidth={3}
                      strokeLinecap="round"
                    >
                      <title>
                        {stationName(e.a)} ↔ {stationName(e.b)} &middot;{" "}
                        {e.trains.length} train{e.trains.length > 1 ? "s" : ""}
                      </title>
                    </path>
                  );
                })}
                {nodes.map((n) => {
                  const isHub = n.code === "NGP";
                  const isFlagshipNode = !!NODE_POSITIONS[n.code] && edges.some(
                    (e) => e.corridor === "flagship" && (e.a === n.code || e.b === n.code),
                  );
                  const r = isHub ? 12 : isFlagshipNode ? 7 : 5;
                  const city = data.stations.find((s) => s.code === n.code)?.city;
                  const offset = LABEL_OFFSETS[n.code];
                  const labelX = n.x + (offset?.dx ?? 0);
                  const anchor = offset?.anchor ?? "middle";
                  return (
                    <g key={n.code}>
                      <circle
                        cx={n.x}
                        cy={n.y}
                        r={r}
                        fill={isFlagshipNode ? "var(--accent)" : "var(--surface)"}
                        stroke={isFlagshipNode ? "var(--accent)" : "var(--ink-dim)"}
                        strokeWidth={isFlagshipNode ? 0 : 1.5}
                      >
                        <title>
                          {n.code} &middot; {stationName(n.code)}
                        </title>
                      </circle>
                      <text
                        x={labelX}
                        y={n.y + r + 13}
                        textAnchor={anchor}
                        fontSize={isFlagshipNode ? 12 : 10}
                        fontWeight={isHub ? 700 : 600}
                        fill="var(--ink)"
                        className="font-mono"
                      >
                        {n.code}
                      </text>
                      {isFlagshipNode && city && (
                        <text
                          x={labelX}
                          y={n.y + r + 26}
                          textAnchor={anchor}
                          fontSize={10}
                          fill="var(--ink-dim)"
                        >
                          {city}
                        </text>
                      )}
                    </g>
                  );
                })}
              </svg>
            </div>
            <div className="text-ink-dim flex flex-wrap items-center gap-4 text-[11px]">
              <span className="flex items-center gap-1.5">
                <span className="bg-accent inline-block h-[3px] w-4 rounded-full" /> Flagship
                corridor (6 trains) &mdash; code and city both shown
              </span>
              <span className="flex items-center gap-1.5">
                <span className="bg-rail inline-block h-[1.5px] w-4 rounded-full" /> Filler route
                (point-to-point) &mdash; code only, see key below
              </span>
            </div>
            <div>
              <p className="text-ink-dim mb-1.5 text-[11px] font-semibold tracking-wide uppercase">
                Station key
              </p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] sm:grid-cols-3">
                {nodes
                  .slice()
                  .sort((a, b) => {
                    const aFlag = edges.some(
                      (e) => e.corridor === "flagship" && (e.a === a.code || e.b === a.code),
                    );
                    const bFlag = edges.some(
                      (e) => e.corridor === "flagship" && (e.a === b.code || e.b === b.code),
                    );
                    if (aFlag !== bFlag) return aFlag ? -1 : 1;
                    return a.x - b.x;
                  })
                  .map((n) => (
                    <div key={n.code} className="flex gap-1.5">
                      <code className="text-ink font-mono font-medium">{n.code}</code>
                      <span className="text-ink-dim">{stationName(n.code)}</span>
                    </div>
                  ))}
              </div>
            </div>
          </section>

          <section className="flex flex-col gap-2">
            <h2 className="text-ink text-sm font-semibold">Trains in the mock data</h2>
            <p className="text-ink-dim text-xs leading-relaxed">
              15 trains total. Book any flagship-corridor journey (Bengaluru &rarr; Nagpur &rarr;
              Varanasi) to see a real connecting-journey flow with two separate tickets.
            </p>
            <div className="flex flex-col gap-3">
              <div>
                <p className="text-accent mb-1 text-xs font-semibold">Flagship corridor</p>
                <div className="border-rail divide-y rounded border">
                  {flagshipTrains.map((t) => (
                    <div key={t.number} className="flex flex-col gap-0.5 p-2.5">
                      <code className="text-ink font-mono text-xs font-medium">
                        {t.number} {t.name}
                      </code>
                      <p className="text-ink-dim text-[11px] leading-relaxed">
                        {routeLabel(t, stationName)}
                      </p>
                      <p className="text-ink-dim text-[11px]">Classes: {t.classes.join(", ")}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-ink-dim mb-1 text-xs font-semibold">Filler routes</p>
                <div className="border-rail divide-y rounded border">
                  {fillerTrains.map((t) => (
                    <div key={t.number} className="flex items-baseline justify-between gap-3 p-2.5">
                      <code className="text-ink font-mono text-xs">
                        {t.number} {t.name}
                      </code>
                      <p className="text-ink-dim shrink-0 text-[11px]">{routeLabel(t, stationName)}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section className="flex flex-col gap-2">
            <h2 className="text-ink text-sm font-semibold">Where PNRs come from</h2>
            <p className="text-ink-dim text-xs leading-relaxed">
              There&apos;s no pre-seeded list of sample PNRs to try -- a PNR is a random 10-digit
              number generated the moment you actually confirm a booking in the chat, exactly like
              real IRCTC. To get one: tell Saarthi where you&apos;re going (try the flagship
              corridor above), pick a train, give passenger details, and confirm payment. The PNR
              it hands back is real for the rest of this session, and it&apos;s what Demo Controls
              (below) acts on.
            </p>
          </section>

          <section className="flex flex-col gap-2">
            <h2 className="text-ink text-sm font-semibold">What the demo-control toggles do</h2>
            <p className="text-ink-dim text-xs leading-relaxed">
              These fast-forward a simulated per-session clock -- nothing here is a real delay
              feed. Every button acts on the <strong>first train you booked this session</strong>{" "}
              (the chat shows this above the buttons once you&apos;ve booked, by train and route,
              specifically so it&apos;s never ambiguous which leg is affected on a connecting
              journey).
            </p>
            <div className="border-rail divide-y rounded border text-xs">
              {[
                ["Chart prepared", "Jumps to 4 hours before departure -- the real IRCTC moment a waitlisted ticket either clears or doesn't."],
                ["Boarding day", "Jumps to 1 hour before departure -- platform assignment and last-minute waitlist movement."],
                ["Delay 1h", "Marks the train running 1h 5m late."],
                ["Delay 3h+", "Marks it running 3h 20m late -- crosses the real TDR eligibility threshold, and on a connecting journey, triggers Saarthi's own broken-connection reasoning if the delay would cause a missed connection."],
                ["Cancelled", "Marks the train cancelled shortly after its scheduled departure."],
                ["Reset journey", "Clears the simulated clock back to real time."],
              ].map(([label, desc]) => (
                <div key={label} className="flex flex-col gap-0.5 p-2.5 sm:flex-row sm:gap-3">
                  <span className="text-ink w-32 shrink-0 font-medium">{label}</span>
                  <span className="text-ink-dim leading-relaxed">{desc}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="flex flex-col gap-2">
            <h2 className="text-ink text-sm font-semibold">What Saarthi can actually do</h2>
            <div className="border-rail divide-y rounded border text-xs">
              {[
                ["Search & book", "Direct or connecting journeys, with a waitlist-odds explanation for each option -- never a bare list of times and fares."],
                ["Watch proactively", "Once booked, it speaks up on its own: waitlist movement, chart-prep outcome, platform assignment, a delay crossing 1h then 3h, a retiring room becoming eligible -- no need to ask."],
                ["Broken connections (Flow H)", "If a delay on leg 1 of a connecting journey would cause you to miss leg 2, it detects this itself and lays out two real, itemized options -- refund both, or rebook leg 2 -- with a recommendation."],
                ["TDR (refund claims)", "Checks real eligibility and a real deadline before ever suggesting you file one; tells you plainly when a refund is automatic and filing isn't needed at all."],
                ["Catering & retiring rooms", "Food ordering ahead of an upcoming halt, and retiring-room booking, both gated on your ticket's real status."],
              ].map(([label, desc]) => (
                <div key={label} className="flex flex-col gap-0.5 p-2.5">
                  <span className="text-ink font-medium">{label}</span>
                  <span className="text-ink-dim leading-relaxed">{desc}</span>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {data && tab === "tutorial" && (
        <>
          <section className="flex flex-col gap-3">
            <div>
              <p className="text-ink-dim text-xs leading-relaxed">
                A complete run-through, start to finish -- follow it in order in the chat panel.
                Copy the quoted lines directly; everything else is what to expect and what to
                watch for.
              </p>
            </div>
            <ol className="flex flex-col gap-3">
              {[
                {
                  title: "Start clean",
                  body: "Click New chat if there's leftover state. This resets the thread and clears the Demo Controls target label.",
                },
                {
                  title: "Search the flagship route",
                  body: "Expect up to 3 ranked options via Nagpur, each labelled OPTION 1/2/3, with a bolded recommendation underneath -- never a restated list of numbers.",
                  copy: "Bengaluru to Varanasi on 4 September, 1 person",
                },
                {
                  title: "Book leg 1",
                  body: "Confirm the quote, click Simulate payment. You get a real PNR (10 random digits -- generated, not pre-seeded). Open Demo controls -- the label should now name this exact train and route.",
                  copy: "Book train 12295 from SBC to NGP in SL class. Passenger: Amit, 45, lower berth",
                },
                {
                  title: "Book leg 2, linked",
                  body: "Use leg 1's PNR from the previous step. Demo Controls should still point at leg 1 -- that's deliberate, its delay is what can break the connection.",
                  copy: "Now book the connecting leg, train 12539 from NGP to BSB in SL class, same passenger. Link it to PNR <leg1 PNR>",
                },
                {
                  title: "Chart prepared",
                  body: "Demo Controls -> Chart prepared. Expect either a confirmed-seat alert naming the train and berth, or an auto-refund alert if it stayed waitlisted -- either way, the train is named, never a bare status.",
                },
                {
                  title: "Boarding day",
                  body: "Demo Controls -> Boarding day. If confirmed, expect a platform-assignment alert naming the station and train. A still-waitlisted ticket correctly gets no platform.",
                },
                {
                  title: "Delay 1h",
                  body: "Demo Controls -> Delay 1h. Expect a plain running-late alert naming the train, 1h 5m late.",
                },
                {
                  title: "Delay 3h+ -- the Flow H moment",
                  body: "Demo Controls -> Delay 3h+. This crosses the TDR threshold and, because leg 1 now lands after leg 2 departs, triggers the broken-connection check: a critical alert plus a DecisionBlock with two real, itemized options and a recommendation. Reply \"Option 1\" or \"Option 2\" and confirm the response walks through the DecisionBlock's own numbers, never invented ones. \"Abandon both\" completes in one turn (refund on both legs, no extra confirmation step). \"Travel late, rebook leg 2\" rebooks onto the exact replacement train the DecisionBlock named -- check the final confirmation matches it.",
                },
                {
                  title: "Cancelled (fresh booking)",
                  body: "New chat, book any single train, then Demo Controls -> Cancelled. Ask about a refund -- expect it to say plainly that this is automatic and no filing is needed.",
                },
                {
                  title: "TDR on a real delay",
                  body: "New chat, book one train with no connection, Demo Controls -> Delay 3h+, then ask about your refund. Expect eligibility, a plain-language reason, a relative countdown deadline, and it only files after you explicitly say to.",
                },
                {
                  title: "Catering & retiring room",
                  body: "On a confirmed PNR, ask about food before an upcoming stop, and about a retiring room at the destination. Expect real, filtered options gated on your ticket's actual status -- a plain no if you're not eligible, not a soft dodge.",
                },
                {
                  title: "Honesty panel, API surface, this guide",
                  body: "\"Demo -- synthetic data\" in the header opens in place, chat untouched behind it. \"See the proposed API surface\" opens in a new tab. This page (/guide) is the network/capabilities reference.",
                },
                {
                  title: "Reset",
                  body: "Demo Controls -> Reset journey, then New chat. Confirm the Demo Controls label reverts to prompting for a fresh booking.",
                },
              ].map((step, i) => (
                <li key={step.title} className="border-rail flex gap-3 rounded border p-2.5">
                  <span className="text-accent-ink bg-accent flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-bold">
                    {i + 1}
                  </span>
                  <div className="flex flex-col gap-1">
                    <p className="text-ink text-xs font-semibold">{step.title}</p>
                    <p className="text-ink-dim text-[11px] leading-relaxed">{step.body}</p>
                    {step.copy && (
                      <code className="border-rail bg-surface text-ink w-fit rounded border px-2 py-1 font-mono text-[11px]">
                        {step.copy}
                      </code>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </>
      )}

      {data && tab === "guide" && (
        <>
          <section className="flex flex-col gap-2">
            <h2 className="text-ink text-sm font-semibold">What&apos;s real, what&apos;s mocked</h2>
            <div className="border-rail divide-y rounded border text-xs">
              {[
                ["Real", "The conversation, the reasoning, the eligibility rules, deadline logic, the alert engine, and the full API design."],
                ["Mocked", "Train inventory, PNRs, live delay data, payments, and the historical dataset behind confirmation odds."],
                ["Modelled from public documentation", "TDR deadlines and reason codes, retiring-room eligibility, catering halt windows, waitlist quota behaviour."],
                ["What production would need", "Registered IRCTC partner API access, and historical PNR outcome data -- not publicly available outside IRCTC and CRIS."],
              ].map(([label, desc]) => (
                <div key={label} className="flex flex-col gap-0.5 p-2.5">
                  <span className="text-ink font-medium">{label}</span>
                  <span className="text-ink-dim leading-relaxed">{desc}</span>
                </div>
              ))}
            </div>
            <a href="/api-surface" target="_blank" rel="noopener noreferrer" className="text-accent text-xs underline">
              See the proposed API surface &rarr;
            </a>
          </section>

          <AdminResetSection />
        </>
      )}
    </div>
  );
}

// Wipes every session's data across the whole deployment -- not scoped to
// the visitor's own session, unlike everything else in this app (session
// isolation already means a new visitor sees a clean slate regardless, so
// this exists purely to clear accumulated test data before a wider audience
// uses the app). Requires the same admin token the backend endpoint checks;
// with no token entered, or the wrong one, the backend simply refuses --
// this is not the app's access control, it just avoids a bare destructive
// button doing anything on a stray click.
function AdminResetSection() {
  const [open, setOpen] = useState(false);
  const [token, setToken] = useState("");
  const [status, setStatus] = useState<"idle" | "confirming" | "loading" | "done" | "error">(
    "idle",
  );
  const [resultText, setResultText] = useState("");

  async function runReset() {
    setStatus("loading");
    try {
      const res = await apiFetch("/api/admin/reset-db", {
        method: "POST",
        headers: { "X-Admin-Token": token },
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus("error");
        setResultText(data.detail ?? `Request failed (${res.status}).`);
        return;
      }
      setStatus("done");
      setResultText(`Cleared ${data.total} row${data.total === 1 ? "" : "s"} across every session.`);
    } catch {
      setStatus("error");
      setResultText("Couldn't reach the backend.");
    }
  }

  return (
    <section className="border-rail flex flex-col gap-2 border-t pt-4">
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-ink-faint hover:text-ink-dim w-fit text-[11px] underline decoration-dotted"
      >
        Admin: reset all demo data
      </button>
      {open && (
        <div className="border-rail bg-raised flex flex-col gap-2 rounded border p-3">
          <p className="text-ink-dim text-[11px] leading-relaxed">
            Wipes every PNR, message, and alert for <strong>every visitor</strong>, not just this
            session -- for clearing test data before opening this up more broadly, not something
            a visitor needs. Requires the admin token set on the backend; does nothing without it.
          </p>
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Admin token"
            className="bg-surface text-ink border-rail rounded border px-2 py-1 text-xs outline-none"
          />
          {status !== "confirming" ? (
            <button
              onClick={() => setStatus("confirming")}
              disabled={!token || status === "loading"}
              className="border-rail text-ink-dim hover:border-signal-stop hover:text-signal-stop w-fit rounded border px-2 py-1 text-xs disabled:opacity-50"
            >
              Reset all demo data
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-signal-stop text-[11px] font-medium">Sure? This can&apos;t be undone.</span>
              <button
                onClick={runReset}
                className="bg-signal-stop text-accent-ink rounded px-2 py-1 text-xs font-medium"
              >
                Yes, wipe it
              </button>
              <button
                onClick={() => setStatus("idle")}
                className="border-rail text-ink-dim rounded border px-2 py-1 text-xs"
              >
                Cancel
              </button>
            </div>
          )}
          {status === "loading" && (
            <p className="text-ink-dim text-[11px]" role="status" aria-live="polite">
              Resetting…
            </p>
          )}
          {status === "done" && <p className="text-signal-go text-[11px]">{resultText}</p>}
          {status === "error" && <p className="text-signal-stop text-[11px]">{resultText}</p>}
        </div>
      )}
    </section>
  );
}
