/** Shown in place of the reply text while a turn is in flight and nothing
 * has streamed back yet. Some turns (a fresh search, filing a TDR claim)
 * take a real, noticeable number of seconds -- this has to read
 * unambiguously as "working," not as a short final answer, so it pairs an
 * animated three-dot pulse with the current status label. Dots hold still
 * (but stay visible) under prefers-reduced-motion via the plain .typing-dot
 * class in globals.css, which only gets keyframes outside that media query. */
export default function TypingIndicator({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-ink-dim text-sm">{label}</span>
      <span className="flex items-center gap-1" aria-hidden="true">
        <span className="typing-dot bg-ink-dim h-1.5 w-1.5 rounded-full" style={{ animationDelay: "0ms" }} />
        <span className="typing-dot bg-ink-dim h-1.5 w-1.5 rounded-full" style={{ animationDelay: "150ms" }} />
        <span className="typing-dot bg-ink-dim h-1.5 w-1.5 rounded-full" style={{ animationDelay: "300ms" }} />
      </span>
    </div>
  );
}
