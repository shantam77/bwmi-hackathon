import type { ChatMessage } from "@/lib/types";
import AgentMessage from "./AgentMessage";

export default function Thread({
  messages,
  onSendMessage,
  disabled,
}: {
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  disabled?: boolean;
}) {
  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 px-6 text-center">
        <p className="text-ink text-lg">Where are you going?</p>
        <p className="text-ink-dim text-sm">
          Try: &ldquo;Bengaluru to Varanasi on the 4th, 2 people&rdquo;
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4">
      {messages.map((m, i) =>
        m.role === "user" ? (
          <div key={i} className="text-ink max-w-[85%] self-end text-sm">
            {m.content}
          </div>
        ) : (
          <AgentMessage key={i} message={m} onSendMessage={onSendMessage} disabled={disabled} />
        ),
      )}
    </div>
  );
}
