export function BriefMeta({
  briefId,
  generatedAt,
  inputSignalCount,
  modelUsed,
}: {
  briefId: string;
  generatedAt: string;
  inputSignalCount: number;
  modelUsed: string;
}) {
  const gen = new Date(generatedAt).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
    timeZoneName: "short",
  });
  return (
    <footer className="mt-16 border-t border-line-subtle pt-6">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-subtle">
        <span>Brief {briefId.slice(0, 8)}…</span>
        <span aria-hidden>·</span>
        <span>Generated {gen}</span>
        <span aria-hidden>·</span>
        <span className="tabular-nums">{inputSignalCount} signals</span>
        <span aria-hidden>·</span>
        <span>{modelUsed}</span>
        <span aria-hidden>·</span>
        <span>Conviction-weighted</span>
      </div>
    </footer>
  );
}
