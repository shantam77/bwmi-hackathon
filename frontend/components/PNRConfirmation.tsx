import type { PNRConfirmationProps } from "@/lib/types";

export default function PNRConfirmation({ pnr, train_number, train_name, date, travel_class, status, total_fare, passengers }: PNRConfirmationProps) {
  return (
    <div className="border-signal-go rounded border-l-2 bg-raised p-3">
      <p className="text-ink-dim text-xs">PNR</p>
      <p className="text-ink font-mono text-lg">{pnr}</p>
      <p className="text-ink-dim font-mono text-xs">
        {train_number} {train_name} &middot; {date} &middot; {travel_class} &middot; {status}
      </p>
      <p className="text-ink-dim text-xs">{passengers.length} passenger(s)</p>
      <p className="text-ink mt-1 font-mono">&#8377;{total_fare.toLocaleString("en-IN")}</p>
    </div>
  );
}
