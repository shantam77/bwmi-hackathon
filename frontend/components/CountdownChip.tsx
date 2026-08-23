"use client";

import { useEffect, useState } from "react";

/** deadlineIso is on the SIMULATED clock's timeline, which can be months
 * from the browser's real wall-clock time (the persona date is in
 * September). offsetSeconds (from the alert that carried this deadline)
 * converts real "now" into simulated "now" -- without it this would count
 * down against the wrong date entirely. */
function remainingMs(deadlineIso: string, offsetSeconds: number): number {
  const simulatedNow = Date.now() + offsetSeconds * 1000;
  return Math.max(0, new Date(deadlineIso).getTime() - simulatedNow);
}

export default function CountdownChip({
  deadlineIso,
  offsetSeconds = 0,
}: {
  deadlineIso: string;
  offsetSeconds?: number;
}) {
  const [remaining, setRemaining] = useState(() => remainingMs(deadlineIso, offsetSeconds));

  useEffect(() => {
    setRemaining(remainingMs(deadlineIso, offsetSeconds));
    const id = setInterval(() => setRemaining(remainingMs(deadlineIso, offsetSeconds)), 1000);
    return () => clearInterval(id);
  }, [deadlineIso, offsetSeconds]);

  const totalSeconds = Math.floor(remaining / 1000);
  const hh = Math.floor(totalSeconds / 3600);
  const mm = Math.floor((totalSeconds % 3600) / 60);
  const ss = totalSeconds % 60;
  const pad = (n: number) => n.toString().padStart(2, "0");

  return (
    <span className="text-signal-stop font-mono text-sm tabular-nums">
      {hh > 0 ? `${pad(hh)}:` : ""}
      {pad(mm)}:{pad(ss)}
    </span>
  );
}
