"use client";

import { useState } from "react";
import type { DecisionBlockProps, DecisionOption } from "@/lib/types";
import CountdownChip from "./CountdownChip";

function formatAmount(amount: number): string {
  const sign = amount < 0 ? "-" : "";
  return `${sign}₹${Math.abs(amount).toLocaleString("en-IN")}`;
}

function OptionPanel({
  option,
  offsetSeconds,
  onChoose,
}: {
  option: DecisionOption;
  offsetSeconds?: number;
  onChoose: () => void;
}) {
  return (
    <div className="border-rail flex-1 rounded border p-3">
      <p className="text-ink font-medium">{option.name}</p>
      <div className="mt-2 flex flex-col gap-1">
        {option.items.map((item, i) => (
          <div key={i} className="flex justify-between gap-2 text-xs">
            <span className="text-ink-dim">
              {item.label}
              {item.note ? ` — ${item.note}` : ""}
            </span>
            <span className="text-ink font-mono">{formatAmount(item.amount)}</span>
          </div>
        ))}
      </div>
      {option.deadline_iso && (
        <div className="mt-2">
          <CountdownChip deadlineIso={option.deadline_iso} offsetSeconds={offsetSeconds} />
        </div>
      )}
      <div className="border-rail mt-2 border-t pt-2">
        {option.bottom_line_recovered > 0 && (
          <p className="text-signal-go font-mono text-sm">
            Recover {formatAmount(option.bottom_line_recovered)}
          </p>
        )}
        {option.bottom_line_total_paid > 0 && option.bottom_line_recovered === 0 && (
          <p className="text-signal-wait font-mono text-sm">
            Extra cost {formatAmount(option.bottom_line_total_paid)}
          </p>
        )}
      </div>
      <button
        onClick={onChoose}
        className="bg-signal-go mt-2 w-full rounded px-3 py-1.5 text-xs font-medium text-black"
      >
        Choose {option.name}
      </button>
    </div>
  );
}

export default function DecisionBlock({
  option_1,
  option_2,
  recommendation,
  leg2_rule_explanation,
  clock_offset_seconds,
  onSendMessage,
}: DecisionBlockProps & { onSendMessage: (text: string) => void }) {
  const [showExplain, setShowExplain] = useState(false);

  return (
    <div className="border-signal-stop rounded border-l-[3px] bg-raised p-3">
      <div className="flex flex-col gap-2 sm:flex-row">
        <OptionPanel
          option={option_1}
          offsetSeconds={clock_offset_seconds}
          onChoose={() => onSendMessage(`Option 1 -- ${option_1.name}`)}
        />
        <OptionPanel
          option={option_2}
          offsetSeconds={clock_offset_seconds}
          onChoose={() => onSendMessage(`Option 2 -- ${option_2.name}`)}
        />
      </div>
      <p className="text-ink mt-3 text-sm">{recommendation}</p>
      <button
        onClick={() => setShowExplain((v) => !v)}
        className="text-ink-dim mt-2 text-xs underline"
      >
        {showExplain ? "Hide explanation" : "Explain the leg 2 rule"}
      </button>
      {showExplain && (
        <p className="text-ink-dim mt-2 text-xs leading-relaxed">{leg2_rule_explanation}</p>
      )}
    </div>
  );
}
