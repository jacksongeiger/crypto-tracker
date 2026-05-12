import { notFound } from "next/navigation";

const VALID_CATEGORIES = new Set([
  "overview",
  "policy",
  "markets",
  "tech",
  "adoption",
  "misc",
]);

export default async function CategoryPage({
  params,
}: {
  params: { category: string };
}) {
  if (!VALID_CATEGORIES.has(params.category)) {
    notFound();
  }
  if (params.category === "overview") {
    // /news/overview is its own static route — should not hit this branch.
    notFound();
  }
  return (
    <main className="mx-auto max-w-3xl px-6 py-24 sm:px-8">
      <p className="font-mono text-caption uppercase text-ink-subtle">
        News · {params.category}
      </p>
      <h1 className="mt-3 text-h1 font-semibold text-ink">
        Coming in Phase 4
      </h1>
      <p className="mt-4 text-bodyLg text-ink-muted">
        Category filtering and per-category summaries are wired in the next
        slice. The current brief lives at{" "}
        <a className="underline text-brand-500" href="/news/overview">
          /news/overview
        </a>
        .
      </p>
    </main>
  );
}
