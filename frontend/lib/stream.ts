import type { SSEEvent } from "./types";

/** Parses the frozen SSE contract (token/tool_call/component/alert/done) off
 * a fetch Response's body stream. Newline-delimited JSON, one event per
 * "data: {...}\n\n" block -- see backend/app/agent/runner.py's sse(). */
export async function* parseSSE(response: Response): AsyncGenerator<SSEEvent> {
  if (!response.body) return;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      const line = rawEvent.split("\n").find((l) => l.startsWith("data: "));
      if (line) {
        const jsonStr = line.slice("data: ".length);
        try {
          yield JSON.parse(jsonStr) as SSEEvent;
        } catch {
          // malformed chunk -- skip rather than crash the stream
        }
      }
      boundary = buffer.indexOf("\n\n");
    }
  }
}
