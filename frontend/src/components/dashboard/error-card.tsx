export function ErrorCard({
  title,
  className = "",
}: {
  title: string;
  className?: string;
}) {
  return (
    <div
      className={`rounded-md border border-line-subtle bg-surface-raised p-6 ${className}`}
    >
      <div className="font-mono text-caption uppercase text-ink-subtle">
        {title}
      </div>
      <div className="mt-3 text-bodySm text-danger">
        Data unavailable right now.
      </div>
    </div>
  );
}
