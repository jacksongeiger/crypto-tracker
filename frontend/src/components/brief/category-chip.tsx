import Link from "next/link";
import type { Category } from "@/types/brief";
import { CATEGORY_LABELS } from "@/types/brief";

const TONE: Record<Category, string> = {
  policy: "bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-100",
  markets: "bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-200",
  tech: "bg-surface-muted text-ink ring-1 ring-inset ring-line",
  // AI uses a teal-shifted tint to stay in the cool-color family but
  // distinguish from the Coinbase-blue Tech/Markets/Policy chips.
  ai: "bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-200",
  adoption: "bg-brand-100 text-brand-700 ring-1 ring-inset ring-brand-200",
  misc: "bg-surface-muted text-ink-muted ring-1 ring-inset ring-line-subtle",
};

export function CategoryChip({
  category,
  asLink = true,
}: {
  category: Category;
  asLink?: boolean;
}) {
  const tone = TONE[category];
  const content = (
    <>
      <span aria-hidden className="block h-1 w-1 rounded-full bg-current opacity-60" />
      {CATEGORY_LABELS[category]}
    </>
  );
  const className = `inline-flex items-center gap-1.5 rounded-sm px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em] ${tone} transition-colors duration-150 ease-coinbase`;

  if (asLink) {
    return (
      <Link
        href={`/news/${category}`}
        className={`${className} hover:bg-brand-100 hover:text-brand-700`}
      >
        {content}
      </Link>
    );
  }
  return <span className={className}>{content}</span>;
}
