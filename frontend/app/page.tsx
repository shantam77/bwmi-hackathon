"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type HealthResponse = {
  status: string;
  session_id: string;
};

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch("/api/health")
      .then((res) => {
        if (!res.ok) throw new Error(`Backend responded ${res.status}`);
        return res.json();
      })
      .then(setHealth)
      .catch((err) => setError(String(err)));
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-6">
      <h1 className="text-2xl font-semibold text-ink">Saarthi</h1>
      <p className="text-ink-dim text-sm">Phase 0 seam check: frontend &rarr; backend</p>

      {error && (
        <div className="rounded border-l-2 border-signal-stop bg-raised px-4 py-3 text-sm text-ink">
          Could not reach the backend: {error}
        </div>
      )}

      {health && (
        <div className="rounded border-l-2 border-signal-go bg-raised px-4 py-3 font-mono text-sm text-ink">
          <div>status: {health.status}</div>
          <div>session_id: {health.session_id}</div>
        </div>
      )}

      {!health && !error && (
        <div className="text-ink-dim text-sm">Reaching backend&hellip;</div>
      )}
    </main>
  );
}
