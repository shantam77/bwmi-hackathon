import type { PaymentSheetProps } from "@/lib/types";

export default function PaymentSheet({
  props,
  onConfirm,
  disabled,
}: {
  props: PaymentSheetProps;
  onConfirm: () => void;
  disabled?: boolean;
}) {
  return (
    <div className="rounded border border-rail bg-raised p-3">
      <p className="text-ink font-medium">
        {props.train_number} {props.train_name}
      </p>
      <p className="text-ink-dim font-mono text-xs">
        {props.from_station} &rarr; {props.to_station} &middot; {props.date} &middot;{" "}
        {props.travel_class}
      </p>
      <div className="mt-2 flex flex-col gap-1">
        {props.passengers.map((p, i) => (
          <p key={i} className="text-ink-dim text-xs">
            {p.name}, {p.age}
            {p.berth_preference ? `, ${p.berth_preference} berth` : ""}
          </p>
        ))}
      </div>
      {props.senior_citizen_note && (
        <p className="text-signal-wait mt-2 text-xs">{props.senior_citizen_note}</p>
      )}
      <p className="text-ink mt-3 font-mono text-lg">
        &#8377;{props.total_fare.toLocaleString("en-IN")}
      </p>
      <button
        onClick={onConfirm}
        disabled={disabled}
        className="bg-accent text-accent-ink mt-2 rounded px-3 py-2 text-sm font-medium disabled:opacity-50"
      >
        Simulate payment
      </button>
      <p className="text-ink-dim mt-1 text-xs">Demo payment &mdash; no money moves</p>
    </div>
  );
}
