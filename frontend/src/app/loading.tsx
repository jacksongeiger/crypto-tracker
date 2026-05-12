export default function Loading() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-24 sm:px-8" role="status" aria-live="polite">
      <span className="sr-only">Loading…</span>
      <div className="h-3 w-24 animate-pulse rounded bg-line-subtle" />
      <div className="mt-4 h-10 w-3/4 animate-pulse rounded bg-line-subtle" />
      <div className="mt-3 h-4 w-2/3 animate-pulse rounded bg-line-subtle" />
      <div className="mt-12 space-y-5">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="animate-pulse rounded-md border border-line-subtle bg-surface-raised p-7"
          >
            <div className="h-3 w-16 rounded bg-line-subtle" />
            <div className="mt-4 h-6 w-2/3 rounded bg-line-subtle" />
            <div className="mt-3 h-4 w-1/3 rounded bg-line-subtle" />
            <div className="mt-5 h-4 w-full rounded bg-line-subtle" />
            <div className="mt-2 h-4 w-5/6 rounded bg-line-subtle" />
          </div>
        ))}
      </div>
    </div>
  );
}
