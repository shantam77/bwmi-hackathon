"use client";

import { useState } from "react";

const BUTTONS: { demo_state: string; label: string; recommended?: boolean }[] = [
  { demo_state: "chart_prepared", label: "Chart prepared" },
  { demo_state: "boarding_day", label: "Boarding day" },
  { demo_state: "delay_1h", label: "Delay 1h" },
  { demo_state: "delay_3h", label: "Delay 3h+", recommended: true },
  { demo_state: "cancelled", label: "Cancelled" },
];

export default function DemoControls({
  onSelect,
  disabled,
}: {
  onSelect: (demoState: string) => void;
  disabled?: boolean;
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
        <div className="flex flex-wrap gap-2 px-3 pb-3">
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
      )}
    </div>
  );
}
