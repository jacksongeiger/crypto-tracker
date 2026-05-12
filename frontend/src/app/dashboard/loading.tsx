export default function DashboardLoading() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-16 sm:px-8" role="status" aria-live="polite">
      <span className="sr-only">Loading dashboard…</span>
      <div className="h-3 w-24 animate-pulse rounded bg-line-subtle" />
      <div className="mt-3 h-10 w-2/3 animate-pulse rounded bg-line-subtle" />
      <div className="mt-3 h-4 w-1/2 animate-pulse rounded bg-line-subtle" />
      <div className="mt-10 flex gap-3 overflow-x-auto">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="min-w-[180px] animate-pulse rounded-md border border-line-subtle bg-surface-raised p-4"
          >
            <div className="h-3 w-10 rounded bg-line-subtle" />
            <div className="mt-3 h-5 w-20 rounded bg-line-subtle" />
            <div className="mt-3 h-6 w-full rounded bg-line-subtle" />
          </div>
        ))}
      </div>
      <div className="mt-10 grid gap-5 lg:grid-cols-2">
        {Array.from({ length: 2 }).map((_, i) => (
          <div
            key={i}
            className="animate-pulse rounded-md border border-line-subtle bg-surface-raised p-7"
          >
            <div className="h-3 w-24 rounded bg-line-subtle" />
            <div className="mt-4 h-8 w-1/2 rounded bg-line-subtle" />
            <div className="mt-6 h-20 rounded bg-line-subtle" />
          </div>
        ))}
      </div>
    </div>
  );
}
