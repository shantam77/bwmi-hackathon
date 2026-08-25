import GuidePanel from "@/components/GuidePanel";

// Standalone review route for GuidePanel before it's wired into the main
// split-screen layout -- lets the panel's content and graph be checked in
// isolation, full-width, without touching page.tsx at all.
export default function GuidePage() {
  return (
    <main className="bg-surface mx-auto min-h-screen w-full min-w-0 max-w-[900px]">
      <div className="border-rail flex items-center justify-between border-b px-5 py-3">
        <h1 className="text-ink text-sm font-semibold">Saarthi guide</h1>
        <a href="/" className="text-accent text-xs underline">
          &larr; Back to Saarthi
        </a>
      </div>
      <GuidePanel />
    </main>
  );
}
