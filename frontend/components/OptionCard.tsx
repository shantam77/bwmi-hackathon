import type { OptionCardProps } from "@/lib/types";

const BAND_LABEL: Record<string, string> = {
  confirm: "Confirmed",
  probable: "Probable",
  low: "Low chance",
};

const BAND_COLOR: Record<string, string> = {
  confirm: "text-signal-go border-signal-go",
  probable: "text-signal-wait border-signal-wait",
  low: "text-signal-stop border-signal-stop",
};

export default function OptionCard({ ambiguous_stations, options }: OptionCardProps) {
  if (options.length === 0) {
    return (
      <div className="rounded border-l-2 border-signal-stop bg-raised px-4 py-3 text-sm text-ink">
        No options found.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {ambiguous_stations.length > 0 && (
        <p className="text-ink-dim text-xs">
          {ambiguous_stations
            .map((a) => `"${a.query}" checked against ${a.candidates.join(", ")}`)
            .join(" · ")}
        </p>
      )}
      {options.map((option, i) => (
        <div key={i} className="rounded border border-rail bg-raised p-3">
          {option.interchange && (
            <p className="text-ink-dim mb-2 text-xs">
              Via {option.interchange} &middot; layover {option.layover_minutes} min
            </p>
          )}
          {option.legs.map((leg, j) => (
            <div key={j} className={j > 0 ? "mt-2 border-t border-rail pt-2" : ""}>
              <div className="flex items-baseline justify-between">
                <span className="text-ink font-medium">
                  {leg.train_number} {leg.train_name}
                </span>
                <span
                  className={`rounded border px-1.5 py-0.5 font-mono text-xs ${BAND_COLOR[leg.waitlist_band] ?? ""}`}
                >
                  {BAND_LABEL[leg.waitlist_band] ?? leg.status}
                </span>
              </div>
              <p className="text-ink-dim font-mono text-xs">
                {leg.from_station} {leg.departure} &rarr; {leg.to_station} {leg.arrival}
                {leg.arrival_day_offset > leg.departure_day_offset ? " (+1)" : ""}
              </p>
              <p className="text-ink-dim text-xs">
                {leg.travel_class} &middot; {leg.status}
                {leg.status === "WL" ? ` ${leg.waitlist_type}/${leg.seats_or_position}` : ""}
                &middot; &#8377;{leg.fare_per_passenger.toLocaleString("en-IN")} / passenger
              </p>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
