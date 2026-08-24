"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import { parseSSE } from "@/lib/stream";
import type { ChatMessage, SessionResponse } from "@/lib/types";
import DemoControls from "@/components/DemoControls";
import Thread from "@/components/Thread";

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiFetch("/api/session")
      .then((res) => res.json())
      .then((data: SessionResponse) => {
        // Rehydration can resolve after the user has already started a new
        // conversation locally (React Strict Mode double-invokes this effect
        // in dev, and the fetch can simply be slow). Only apply it if
        // nothing has happened locally yet -- never stomp newer state with
        // a stale snapshot.
        setMessages((prev) =>
          prev.length === 0
            ? data.messages.map((m) => ({
                role: m.role,
                content: m.content,
                component: m.component,
              }))
            : prev,
        );
        setLoaded(true);
      })
      .catch(() => setLoaded(true));
  }, []);

  useEffect(() => {
    // requestAnimationFrame so this runs after layout has settled -- without
    // it, scrollIntoView can compute against a not-yet-painted (too short)
    // page, especially right after rehydration mounts the whole thread at
    // once. "auto" not "smooth": instant is correct for a page load, and
    // matches the PDD's near-zero-motion design anyway.
    requestAnimationFrame(() => {
      bottomRef.current?.scrollIntoView({ behavior: "auto" });
    });
  }, [messages]);

  async function sendMessage(text: string) {
    if (!text.trim() || sending) return;
    setSending(true);
    setMessages((prev) => [
      ...prev,
      { role: "user", content: text },
      { role: "agent", content: "", component: null },
    ]);
    setInput("");

    try {
      const res = await apiFetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      for await (const event of parseSSE(res)) {
        if (event.type === "token") {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            next[next.length - 1] = { ...last, content: last.content + event.content };
            return next;
          });
        } else if (event.type === "component") {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            next[next.length - 1] = {
              ...last,
              component: { component: event.component, props: event.props },
            };
            return next;
          });
        } else if (event.type === "done") {
          break;
        }
      }
    } finally {
      setSending(false);
    }
  }

  async function sendClockAction(demoState: string) {
    if (sending) return;
    setSending(true);

    try {
      const res = await apiFetch("/api/clock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ demo_state: demoState }),
      });

      for await (const event of parseSSE(res)) {
        if (event.type === "alert") {
          setMessages((prev) => [
            ...prev,
            {
              role: "agent",
              content: (event.props.message as string) ?? "",
              component: { component: "AlertMessage", props: event.props },
            },
          ]);
        } else if (event.type === "component") {
          // Flow H's DecisionBlock arrives this way -- distinct from
          // "alert" since it's a rich component, not a severity-marker
          // message. Missing this branch means the backend can correctly
          // compute and stream it and the frontend still silently drops it.
          setMessages((prev) => [
            ...prev,
            {
              role: "agent",
              content: "Your connection is broken. I've worked through it.",
              component: { component: event.component, props: event.props },
            },
          ]);
        } else if (event.type === "done") {
          break;
        }
      }
    } finally {
      setSending(false);
    }
  }

  return (
    <main className="bg-surface mx-auto flex h-screen max-w-[520px] flex-col">
      <header className="border-rail border-b px-4 py-3">
        <h1 className="text-ink text-sm font-semibold">Saarthi</h1>
      </header>

      {loaded && (
        <Thread
          ref={bottomRef}
          messages={messages}
          onSendMessage={sendMessage}
          disabled={sending}
        />
      )}

      <DemoControls onSelect={sendClockAction} disabled={sending} />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          sendMessage(input);
        }}
        className="border-rail flex gap-2 border-t p-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={sending}
          placeholder="Type a message..."
          className="bg-raised text-ink flex-1 rounded px-3 py-2 text-sm outline-none"
        />
        <button
          type="submit"
          disabled={sending}
          className="bg-signal-go rounded px-4 py-2 text-sm font-medium text-black disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </main>
  );
}
