export function SummaryCard({
  summary,
  label = "TL;DR",
}: {
  summary: string;
  label?: string;
}) {
  return (
    <section
      aria-label={label}
      className="relative overflow-hidden rounded-md border border-brand-100 bg-brand-50/60 p-6 sm:p-7"
    >
      <span
        aria-hidden
        className="absolute left-0 top-0 h-full w-[3px] bg-brand-500"
      />
      <div className="font-mono text-caption uppercase text-brand-700">
        {label}
      </div>
      <p className="mt-3 text-bodyLg text-ink">{summary}</p>
    </section>
  );
}
