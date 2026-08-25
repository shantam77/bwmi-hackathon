"use client";

import { useEffect, useRef, useState } from "react";
import type { CSSProperties, PointerEvent as ReactPointerEvent } from "react";
import { apiFetch } from "@/lib/api";
import { parseSSE } from "@/lib/stream";
import type { ChatMessage, DemoTarget, SessionResponse } from "@/lib/types";
import DemoControls from "@/components/DemoControls";
import GuidePanel from "@/components/GuidePanel";
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

const DEFAULT_CHAT_WIDTH = 520;
const MIN_PANE_WIDTH = 360;
const CHAT_WIDTH_STORAGE_KEY = "saarthi-chat-width";

function clampChatWidth(px: number): number {
  const max = Math.max(MIN_PANE_WIDTH, window.innerWidth - MIN_PANE_WIDTH);
  return Math.min(Math.max(px, MIN_PANE_WIDTH), max);
}

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [demoTarget, setDemoTarget] = useState<DemoTarget | null>(null);
  // Which pane shows on a narrow screen (lg: and up, both always show side
  // by side and this is ignored). Defaults to "guide" -- someone getting
  // hands-on with this for the first time (a judge, most concretely) sees
  // the context and mock-data explanation before the chat itself.
  const [mobilePane, setMobilePane] = useState<"chat" | "guide">("guide");
  // Only takes effect at lg: and up (see the CSS var / arbitrary-value
  // trick on <main>'s className below) -- on a narrow screen the chat pane
  // is always full width regardless of this.
  const [chatWidth, setChatWidth] = useState(DEFAULT_CHAT_WIDTH);
  const [isDraggingDivider, setIsDraggingDivider] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const stored = Number(window.localStorage.getItem(CHAT_WIDTH_STORAGE_KEY));
    if (Number.isFinite(stored) && stored > 0) {
      setChatWidth(clampChatWidth(stored));
    }
  }, []);

  // Grows the textarea with content, up to the max-h-32 cap set in its
  // className (beyond that it scrolls internally instead of growing
  // further). Resets to one line automatically once input clears, since
  // that also runs this effect.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [input]);

  function handleDividerPointerDown(e: ReactPointerEvent) {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = chatWidth;
    setIsDraggingDivider(true);
    document.body.style.userSelect = "none";

    function handleMove(moveEvent: PointerEvent) {
      setChatWidth(clampChatWidth(startWidth + (moveEvent.clientX - startX)));
    }
    function handleUp(upEvent: PointerEvent) {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleUp);
      document.body.style.userSelect = "";
      setIsDraggingDivider(false);
      const finalWidth = clampChatWidth(startWidth + (upEvent.clientX - startX));
      window.localStorage.setItem(CHAT_WIDTH_STORAGE_KEY, String(finalWidth));
    }

    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleUp);
  }

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
    <div
      className="flex h-screen min-w-0 flex-col lg:flex-row"
      style={{ "--chat-width": `${chatWidth}px` } as CSSProperties}
    >
      {/* Only meaningful below lg: -- there both panes can't fit, so this
          picks which one is shown. At lg: and up both panes are always
          flex regardless of mobilePane, so this bar has nothing to do and
          is hidden entirely. */}
      <div className="border-rail bg-surface flex gap-1 border-b px-3 pt-2 lg:hidden">
        {(
          [
            ["chat", "Application"],
            ["guide", "Guide"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            onClick={() => setMobilePane(id)}
            className={`-mb-px border-b-2 px-3 py-2 text-xs font-medium transition-colors ${
              mobilePane === id
                ? "border-accent text-accent"
                : "text-ink-dim border-transparent hover:text-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <main
        className={`bg-surface min-h-0 flex-1 flex-col lg:h-screen lg:w-(--chat-width) lg:flex-none ${
          mobilePane === "chat" ? "flex" : "hidden"
        } lg:flex`}
      >
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
          className="border-rail flex items-end gap-2 border-t p-3"
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              // Enter sends; Shift+Enter (or Ctrl/Cmd+Enter) inserts a line
              // break instead -- needed since the agent explicitly asks for
              // passenger details one line per passenger. isComposing guards
              // against IME confirmation keystrokes (relevant here since the
              // agent mirrors Hindi/Hinglish input) being misread as submit.
              if (e.key !== "Enter" || e.nativeEvent.isComposing) return;
              if (!e.shiftKey && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                sendMessage(input);
                return;
              }
              if (e.ctrlKey || e.metaKey) {
                // Unlike Shift+Enter, Ctrl/Cmd+Enter isn't a newline the
                // browser inserts natively in a textarea -- it's otherwise a
                // silent no-op, so insert one by hand at the caret.
                e.preventDefault();
                const el = e.currentTarget;
                const start = el.selectionStart ?? input.length;
                const end = el.selectionEnd ?? input.length;
                const next = input.slice(0, start) + "\n" + input.slice(end);
                setInput(next);
                requestAnimationFrame(() => {
                  el.selectionStart = el.selectionEnd = start + 1;
                });
              }
              // Plain Shift+Enter: let the browser's default newline
              // insertion happen.
            }}
            disabled={sending}
            placeholder="Type a message... (Shift+Enter for a new line)"
            rows={1}
            className="bg-raised text-ink focus:ring-accent/60 max-h-32 flex-1 resize-none rounded px-3 py-2 text-sm leading-relaxed outline-none focus:ring-2"
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

      {/* Drag handle for the chat/guide split -- lg: only, since below that
          only one pane is ever visible and there's nothing to resize. The
          hit area (w-2.5) is wider than the visible line (bg-rail, 1.5px)
          so it's actually grabbable, not a 1px target to hunt for. */}
      <div
        onPointerDown={handleDividerPointerDown}
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize chat and guide panes"
        className={`hidden w-2.5 shrink-0 cursor-col-resize touch-none lg:flex lg:items-stretch lg:justify-center ${
          isDraggingDivider ? "bg-accent/10" : "hover:bg-accent/10"
        }`}
      >
        <div className={`h-full w-[1.5px] ${isDraggingDivider ? "bg-accent" : "bg-rail"}`} />
      </div>

      <aside
        className={`min-h-0 min-w-0 flex-1 flex-col overflow-y-auto lg:h-screen ${
          mobilePane === "guide" ? "flex" : "hidden"
        } lg:flex`}
      >
        <GuidePanel />
      </aside>
    </div>
  );
}
