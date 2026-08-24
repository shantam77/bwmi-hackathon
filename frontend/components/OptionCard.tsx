import type { OptionCardProps } from "@/lib/types";

const BAND_LABEL: Record<string, string> = {
  confirm: "Confirmed",
  probable: "Probable",
  low: "Low chance",
};

const BAND_PILL: Record<string, string> = {
  confirm: "text-signal-go bg-signal-go-bg",
  probable: "text-signal-wait bg-signal-wait-bg",
  low: "text-signal-stop bg-signal-stop-bg",
};

export default function OptionCard({ ambiguous_stations, options }: OptionCardProps) {
  if (options.length === 0) {
    return (
      <div className="border-signal-stop bg-signal-stop-bg text-ink rounded border-l-2 px-4 py-3 text-sm">
        No options found.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {ambiguous_stations.length > 0 && (
        <p className="text-ink-dim text-xs">
          {ambiguous_stations
            .map(
              (a) =>
                `"${a.query}" checked against ${a.candidates
                  .map((c) => `${c.name} (${c.code})`)
                  .join(", ")}`,
            )
            .join(" · ")}
        </p>
      )}
      {options.map((option, i) => (
        <div key={i} className="border-rail bg-raised rounded border p-3">
          <div className="mb-2 flex items-center gap-2">
            <span className="text-accent-ink bg-accent rounded px-1.5 py-0.5 text-[11px] font-bold tracking-wide">
              OPTION {i + 1}
            </span>
            {option.interchange && (
              <span className="text-ink-dim text-xs">
                Via {option.interchange} &middot; layover {option.layover_minutes} min
              </span>
            )}
          </div>
          {option.legs.map((leg, j) => {
            const bandLabel = BAND_LABEL[leg.waitlist_band] ?? leg.status;
            const countText =
              leg.status === "WL"
                ? `${leg.waitlist_type}/${leg.seats_or_position}`
                : `${leg.seats_or_position} seats`;
            return (
              <div key={j} className={j > 0 ? "border-rail mt-3 border-t pt-3" : ""}>
                <p className="text-ink text-sm font-semibold">
                  {leg.train_number} {leg.train_name}
                </p>
                <p className="text-ink-dim mb-2 text-xs">
                  {leg.from_station} &rarr; {leg.to_station} &middot; {leg.travel_class}
                </p>
                <div className="mb-2 flex gap-4">
                  <div className="flex-1">
                    <div className="text-ink-dim text-[10px] tracking-wide uppercase">Departs</div>
                    <div className="font-mono text-sm font-semibold tabular-nums">
                      {leg.departure}
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="text-ink-dim text-[10px] tracking-wide uppercase">Arrives</div>
                    <div className="font-mono text-sm font-semibold tabular-nums">
                      {leg.arrival}
                      {leg.arrival_day_offset > leg.departure_day_offset ? " +1" : ""}
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className={`rounded px-2 py-0.5 text-xs font-medium ${BAND_PILL[leg.waitlist_band] ?? ""}`}>
                    {bandLabel} &middot; {countText}
                  </span>
                  <span className="font-mono text-sm font-semibold">
                    &#8377;{leg.fare_per_passenger.toLocaleString("en-IN")}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
