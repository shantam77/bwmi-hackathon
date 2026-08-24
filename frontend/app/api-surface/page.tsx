"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

interface ImplementedEndpoint {
  method: string;
  path: string;
  purpose: string;
}

interface McpTool {
  name: string;
  description: string;
  inputSchema: {
    properties: Record<string, { type: string }>;
    required: string[];
  };
}

interface SurfaceResponse {
  implemented_endpoints: ImplementedEndpoint[];
  proposed_mcp_tools: McpTool[];
  persistence_boundary_note: string;
}

function signature(tool: McpTool): string {
  const params = Object.keys(tool.inputSchema.properties)
    .map((key) => (tool.inputSchema.required.includes(key) ? key : `${key}?`))
    .join(", ");
  return `${tool.name}(${params})`;
}

export default function ApiSurfacePage() {
  const [data, setData] = useState<SurfaceResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    apiFetch("/api/surface")
      .then((res) => res.json())
      .then(setData)
      .catch(() => setError(true));
  }, []);

  return (
    <main className="bg-surface mx-auto flex min-h-screen max-w-[640px] flex-col gap-6 px-4 py-6">
      <div>
        <a href="/" className="text-accent text-xs underline">
          &larr; Back to Saarthi
        </a>
        <h1 className="text-ink mt-2 text-lg font-semibold">API surface</h1>
        <p className="text-ink-dim mt-1 text-xs">
          Every endpoint this app exposes today, plus the MCP tool catalogue this app would
          hand to another agent, given real IRCTC partner access.
        </p>
      </div>

      {error && (
        <p className="text-signal-stop text-sm">Couldn&apos;t reach the backend just now.</p>
      )}

      {data && (
        <>
          <section>
            <h2 className="text-ink text-sm font-semibold">Implemented endpoints</h2>
            <div className="border-rail mt-2 divide-y rounded border">
              {data.implemented_endpoints.map((ep) => (
                <div key={ep.path} className="flex flex-col gap-1 p-3 sm:flex-row sm:items-baseline sm:gap-3">
                  <code className="text-accent w-fit shrink-0 font-mono text-xs">
                    {ep.method} {ep.path}
                  </code>
                  <p className="text-ink-dim text-xs">{ep.purpose}</p>
                </div>
              ))}
            </div>
          </section>

          <section>
            <h2 className="text-ink text-sm font-semibold">Proposed MCP tools</h2>
            <p className="text-ink-dim mt-1 text-xs">
              Live at <code className="font-mono">POST /mcp</code> (stateless, 2026-07-28 spec) &mdash;
              a representative subset of the domain layer, not the full 16-tool surface the agent
              itself uses internally.
            </p>
            <div className="border-rail mt-2 divide-y rounded border">
              {data.proposed_mcp_tools.map((tool) => (
                <div key={tool.name} className="flex flex-col gap-1 p-3">
                  <code className="text-accent font-mono text-xs">{signature(tool)}</code>
                  <p className="text-ink-dim text-xs">{tool.description}</p>
                </div>
              ))}
            </div>
          </section>

          <section>
            <h2 className="text-ink text-sm font-semibold">Where state actually lives</h2>
            <p className="text-ink-dim mt-2 text-xs leading-relaxed">
              {data.persistence_boundary_note}
            </p>
          </section>
        </>
      )}
    </main>
  );
}
