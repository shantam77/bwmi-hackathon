import type { AlertProps } from "@/lib/types";
import CountdownChip from "./CountdownChip";

const SEVERITY_BORDER: Record<string, string> = {
  critical: "border-signal-stop",
  warn: "border-signal-wait",
  info: "border-rail",
};

const SEVERITY_ICON: Record<string, string> = {
  critical: "\u{1F534}", // red circle
  warn: "\u{1F7E1}", // yellow circle
  info: "\u{1F535}", // blue circle
};

export default function AlertMessage({ props }: { props: AlertProps }) {
  const severity = props.severity ?? "info";
  return (
    <div
      className={`border-l-[3px] bg-raised px-3 py-2 ${SEVERITY_BORDER[severity] ?? SEVERITY_BORDER.info}`}
    >
      <p className="text-ink text-sm">
        <span className="mr-1">{SEVERITY_ICON[severity] ?? SEVERITY_ICON.info}</span>
        {props.message}
      </p>
      <div className="mt-1 flex items-center gap-2">
        {props.tdr_deadline_iso && (
          <>
            <span className="text-ink-dim text-xs">File within:</span>
            <CountdownChip
              deadlineIso={props.tdr_deadline_iso}
              offsetSeconds={props.clock_offset_seconds}
            />
          </>
        )}
        {props.action && <span className="text-ink-dim text-xs">{props.action}</span>}
      </div>
    </div>
  );
}
