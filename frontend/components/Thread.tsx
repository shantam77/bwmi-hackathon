import { forwardRef } from "react";
import type { ChatMessage } from "@/lib/types";
import AgentMessage from "./AgentMessage";

const Thread = forwardRef<HTMLDivElement, {
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  disabled?: boolean;
}>(function Thread({ messages, onSendMessage, disabled }, bottomRef) {
  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 px-6 text-center">
        <p className="text-ink text-lg">Where are you going?</p>
        <p className="text-ink-dim text-sm">
          Try: &ldquo;Bengaluru to Varanasi on 4 September, 2 people&rdquo;
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4">
      {messages.map((m, i) =>
        m.role === "user" ? (
          <div key={i} className="text-ink max-w-[85%] self-end text-sm whitespace-pre-line">
            {m.content}
          </div>
        ) : (
          <AgentMessage key={i} message={m} onSendMessage={onSendMessage} disabled={disabled} />
        ),
      )}
      {/* Inside the actual scroll container (this div, via overflow-y-auto)
          -- a ref placed as a sibling of Thread instead would sit outside
          the scrollable element entirely and scrollIntoView() would have
          nothing meaningful to do. */}
      <div ref={bottomRef} />
    </div>
  );
});

export default Thread;
