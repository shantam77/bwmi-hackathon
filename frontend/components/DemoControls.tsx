"use client";

import { useState } from "react";
import type { DemoTarget } from "@/lib/types";

const BUTTONS: { demo_state: string; label: string; recommended?: boolean }[] = [
  { demo_state: "chart_prepared", label: "Chart prepared" },
  { demo_state: "boarding_day", label: "Boarding day" },
  { demo_state: "delay_1h", label: "Delay 1h" },
  { demo_state: "delay_3h", label: "Delay 3h+", recommended: true },
  { demo_state: "cancelled", label: "Cancelled" },
];

// The single line that answers "delay 3h+ -- for which train?" before
// anyone has to ask. Demo Controls always acts on the session's FIRST
// booked PNR (store.primary_pnr) -- for a connecting journey that's leg 1
// on purpose (it's the one whose delay can break the connection), but
// nothing in the UI said so until this existed. Found to be a real,
// reported point of confusion once more than one leg was booked.
function targetLabel(target: DemoTarget | null): string {
  if (!target) return "Book a ticket to activate Demo controls.";
  const route = `${target.train_number} ${target.train_name} · ${target.from_station_name} → ${target.to_station_name}`;
  if (target.is_first_leg_of_connection) {
    return `Acting on your journey's first leg -- ${route}. A delay here is what could break your connection.`;
  }
  return `Acting on ${route}`;
}

export default function DemoControls({
  onSelect,
  disabled,
  target,
}: {
  onSelect: (demoState: string) => void;
  disabled?: boolean;
  target: DemoTarget | null;
}) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState<string | null>(null);

  return (
    <div className="border-rail border-t">
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-ink-dim flex w-full items-center justify-between px-3 py-2 text-xs"
      >
        <span>Demo controls</span>
        <span>{open ? "▼" : "▲"}</span>
      </button>
      {open && (
        <div className="flex flex-col gap-2 px-3 pb-3">
          <p className="text-ink-dim text-xs leading-relaxed">{targetLabel(target)}</p>
          <div className="flex flex-wrap gap-2">
            {BUTTONS.map((b) => (
              <button
                key={b.demo_state}
                disabled={disabled}
                onClick={() => {
                  setActive(b.demo_state);
                  onSelect(b.demo_state);
                }}
                className={`rounded border px-2 py-1 text-xs disabled:opacity-50 ${
                  active === b.demo_state
                    ? "border-accent text-accent"
                    : "border-rail text-ink-dim"
                }`}
              >
                {b.label}
                {b.recommended ? " ★" : ""}
              </button>
            ))}
            <button
              disabled={disabled}
              onClick={() => {
                setActive(null);
                onSelect("reset");
              }}
              className="border-rail text-ink-dim rounded border px-2 py-1 text-xs disabled:opacity-50"
            >
              Reset journey
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
