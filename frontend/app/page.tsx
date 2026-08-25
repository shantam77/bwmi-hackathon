"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import { parseSSE } from "@/lib/stream";
import type { ChatMessage, DemoTarget, SessionResponse } from "@/lib/types";
import DemoControls from "@/components/DemoControls";
import HonestyPanel from "@/components/HonestyPanel";
import Thread from "@/components/Thread";

// Shown in the reply bubble while a tool call is in flight and no text has
// streamed back yet -- some turns (TDR filing, a fresh search) take a real,
// noticeable number of seconds, and an empty bubble with no signal reads as
// broken, not "thinking." Replaced outright by the first real token.
const TOOL_LABELS: Record<string, string> = {
  search_trains: "Searching trains…",
  quote_booking: "Getting a fare quote…",
  confirm_booking: "Booking your ticket…",
  get_pnr_status: "Checking PNR status…",
  check_tdr_eligibility: "Checking refund eligibility…",
  file_tdr: "Filing your TDR claim…",
  get_refund_status: "Checking refund status…",
  get_catering_options: "Checking catering options…",
  get_retiring_room_availability: "Checking retiring rooms…",
  book_retiring_room: "Booking your room…",
};

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [demoTarget, setDemoTarget] = useState<DemoTarget | null>(null);
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
        setDemoTarget(data.demo_target);
        setLoaded(true);
      })
      .catch(() => setLoaded(true));
  }, []);

  // Demo Controls always acts on the FIRST PNR booked this session (see
  // store.primary_pnr's own docstring) -- refreshed after every booking so
  // its label never lies about which train it's actually targeting. A
  // lightweight endpoint, not a full /api/session re-fetch, since that
  // would re-pull the entire message history just to learn one PNR.
  async function refreshDemoTarget() {
    try {
      const res = await apiFetch("/api/demo-target");
      const data = await res.json();
      setDemoTarget(data.demo_target);
    } catch {
      // Non-critical -- the label just stays as it was; the next
      // successful booking or refresh will catch it up.
    }
  }

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
      { role: "agent", content: "Thinking…", component: null, pending: true },
    ]);
    setInput("");

    let receivedFirstToken = false;

    try {
      const res = await apiFetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      for await (const event of parseSSE(res)) {
        if (event.type === "token") {
          // Capture "is this the first token" into a per-iteration const
          // before the state update, rather than reading the mutable
          // receivedFirstToken flag from inside the updater closure --
          // React can defer a functional setState update, by which point
          // the outer flag may already have been flipped to true by the
          // next loop iteration, silently turning "replace" into "append".
          const isFirstToken = !receivedFirstToken;
          receivedFirstToken = true;
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            const content = isFirstToken ? event.content : last.content + event.content;
            next[next.length - 1] = { ...last, content, pending: false };
            return next;
          });
        } else if (event.type === "tool_call") {
          if (!receivedFirstToken) {
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              next[next.length - 1] = {
                ...last,
                content: TOOL_LABELS[event.name] ?? "Working…",
                pending: true,
              };
              return next;
            });
          }
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
          if (event.component === "PNRConfirmation") {
            refreshDemoTarget();
          }
        } else if (event.type === "done") {
          break;
        }
      }
    } finally {
      setSending(false);
    }
  }

  async function startNewChat() {
    if (sending) return;
    await apiFetch("/api/session/new", { method: "POST" });
    setMessages([]);
    setDemoTarget(null);
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
      <header className="border-rail flex items-center justify-between border-b px-4 py-3">
        <h1 className="text-ink text-sm font-semibold">Saarthi</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={startNewChat}
            disabled={sending}
            className="border-rail text-ink-dim hover:border-accent hover:text-accent rounded border px-2.5 py-1 text-xs transition-colors disabled:opacity-50"
          >
            New chat
          </button>
          <HonestyPanel />
        </div>
      </header>

      {loaded && (
        <Thread
          ref={bottomRef}
          messages={messages}
          onSendMessage={sendMessage}
          disabled={sending}
        />
      )}

      <DemoControls onSelect={sendClockAction} disabled={sending} target={demoTarget} />

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
          className="bg-raised text-ink focus:ring-accent/60 flex-1 rounded px-3 py-2 text-sm outline-none focus:ring-2"
        />
        <button
          type="submit"
          disabled={sending}
          className="bg-accent text-accent-ink rounded px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </main>
  );
}
