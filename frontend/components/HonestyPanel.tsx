"use client";

import { useState } from "react";

export default function HonestyPanel() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="text-ink-dim text-xs underline decoration-dotted"
      >
        Demo &mdash; synthetic data
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="border-rail bg-surface max-h-[80vh] w-full max-w-[480px] overflow-y-auto rounded border p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-ink text-sm font-semibold">What&apos;s real, what&apos;s mocked</h2>
              <button onClick={() => setOpen(false)} className="text-ink-dim text-xs">
                Close
              </button>
            </div>

            <div className="flex flex-col gap-3 text-sm">
              <div>
                <p className="text-ink font-medium">What&apos;s real</p>
                <p className="text-ink-dim text-xs">
                  The conversation, the reasoning, the eligibility rules, deadline logic, the
                  alert engine, and the full API design.
                </p>
              </div>
              <div>
                <p className="text-ink font-medium">What&apos;s mocked</p>
                <p className="text-ink-dim text-xs">
                  Train inventory, PNRs, live delay data, payments, and the historical dataset
                  behind confirmation odds.
                </p>
              </div>
              <div>
                <p className="text-ink font-medium">Modelled from public documentation</p>
                <p className="text-ink-dim text-xs">
                  TDR deadlines and reason codes, retiring-room eligibility, catering halt
                  windows, waitlist quota behaviour. Sources disagree on some exact windows; we
                  picked one consistent set.
                </p>
              </div>
              <div>
                <p className="text-ink font-medium">What production would need</p>
                <p className="text-ink-dim text-xs">
                  Registered IRCTC partner API access, and historical PNR outcome data &mdash;
                  which isn&apos;t publicly available to anyone outside IRCTC and CRIS.
                </p>
              </div>
              <div>
                <p className="text-ink font-medium">What we deliberately didn&apos;t do</p>
                <p className="text-ink-dim text-xs">
                  No browser automation, no unofficial APIs, no contact with live railway
                  systems.
                </p>
              </div>
              <a
                href="/api-surface"
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent text-xs underline"
              >
                See the proposed API surface &rarr;
              </a>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
