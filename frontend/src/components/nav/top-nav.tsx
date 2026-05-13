"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ChevronDown, Menu, X } from "lucide-react";

const NEWS_ITEMS = [
  { slug: "overview", label: "Overview" },
  { slug: "policy", label: "Policy" },
  { slug: "markets", label: "Markets" },
  { slug: "tech", label: "Tech" },
  { slug: "ai", label: "AI" },
  { slug: "adoption", label: "Adoption" },
  { slug: "misc", label: "Misc" },
] as const;

type NavSection = "news" | "dashboard";

function getSection(pathname: string): NavSection | null {
  if (pathname.startsWith("/news")) return "news";
  if (pathname.startsWith("/dashboard")) return "dashboard";
  return null;
}

function getNewsSlug(pathname: string): string | null {
  const match = pathname.match(/^\/news\/([^/]+)/);
  return match ? match[1] : null;
}

export function TopNav() {
  const pathname = usePathname();
  const section = getSection(pathname);
  const newsSlug = getNewsSlug(pathname);

  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  // Close on route change
  useEffect(() => {
    setMenuOpen(false);
    setMobileOpen(false);
  }, [pathname]);

  // Outside click closes the News dropdown
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (!menuRef.current) return;
      if (!menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    if (menuOpen) {
      document.addEventListener("mousedown", handler);
      return () => document.removeEventListener("mousedown", handler);
    }
  }, [menuOpen]);

  // Escape closes both
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setMenuOpen(false);
        setMobileOpen(false);
      }
    }
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  return (
    <header className="sticky top-0 z-50 border-b border-line-subtle bg-surface/90 backdrop-blur supports-[backdrop-filter]:bg-surface/70">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-6 sm:px-8">
        {/* Wordmark */}
        <Link
          href="/news/overview"
          className="flex items-center gap-2 text-ink"
          aria-label="crypto-tracker home"
        >
          <span
            aria-hidden
            className="block h-4 w-4 rounded-sm bg-brand-500"
            style={{ boxShadow: "0 0 0 3px rgba(0,82,255,0.15)" }}
          />
          <span className="font-semibold tracking-tight">crypto-tracker</span>
        </Link>

        {/* Desktop tabs */}
        <nav className="hidden md:flex md:items-stretch md:gap-1" aria-label="Primary">
          <div ref={menuRef} className="relative flex items-stretch">
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              className={`relative inline-flex h-14 items-center gap-1 px-3 text-sm font-medium transition-colors duration-150 ease-coinbase ${
                section === "news"
                  ? "text-ink"
                  : "text-ink-muted hover:text-ink"
              }`}
            >
              News
              <ChevronDown
                className={`h-3.5 w-3.5 transition-transform duration-150 ease-coinbase ${
                  menuOpen ? "rotate-180" : ""
                }`}
                strokeWidth={2.2}
              />
              {section === "news" && <ActiveUnderline />}
            </button>

            {menuOpen && (
              <div
                role="menu"
                className="absolute left-0 top-full z-50 mt-0 w-56 rounded-md border border-line bg-surface shadow-md ring-1 ring-black/[0.02]"
              >
                <div className="px-2 py-2">
                  {NEWS_ITEMS.map((item) => {
                    const active = newsSlug === item.slug;
                    return (
                      <Link
                        key={item.slug}
                        href={`/news/${item.slug}`}
                        role="menuitem"
                        className={`flex items-center justify-between rounded px-3 py-2 text-sm transition-colors duration-150 ease-coinbase ${
                          active
                            ? "bg-brand-50 text-brand-700"
                            : "text-ink hover:bg-surface-muted"
                        }`}
                      >
                        <span>{item.label}</span>
                        {active && (
                          <span
                            aria-hidden
                            className="h-1.5 w-1.5 rounded-full bg-brand-500"
                          />
                        )}
                      </Link>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          <Link
            href="/dashboard"
            className={`relative inline-flex h-14 items-center px-3 text-sm font-medium transition-colors duration-150 ease-coinbase ${
              section === "dashboard"
                ? "text-ink"
                : "text-ink-muted hover:text-ink"
            }`}
          >
            Dashboard
            {section === "dashboard" && <ActiveUnderline />}
          </Link>
        </nav>

        <div className="flex-1" />

        {/* Right-side meta (desktop) */}
        <div className="hidden items-center gap-3 md:flex">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-success-tint px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-success-dark">
            <span aria-hidden className="block h-1.5 w-1.5 rounded-full bg-success" />
            live
          </span>
        </div>

        {/* Mobile hamburger */}
        <button
          type="button"
          className="inline-flex h-9 w-9 items-center justify-center rounded-md text-ink-muted hover:bg-surface-muted hover:text-ink md:hidden"
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((v) => !v)}
        >
          {mobileOpen ? (
            <X className="h-5 w-5" strokeWidth={2} />
          ) : (
            <Menu className="h-5 w-5" strokeWidth={2} />
          )}
        </button>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="border-t border-line-subtle bg-surface md:hidden">
          <div className="mx-auto max-w-7xl px-6 py-4">
            <div className="font-mono text-caption uppercase text-ink-subtle">
              News
            </div>
            <ul className="mt-2 space-y-0.5">
              {NEWS_ITEMS.map((item) => {
                const active = newsSlug === item.slug;
                return (
                  <li key={item.slug}>
                    <Link
                      href={`/news/${item.slug}`}
                      className={`block rounded px-3 py-2 text-sm ${
                        active
                          ? "bg-brand-50 text-brand-700"
                          : "text-ink hover:bg-surface-muted"
                      }`}
                    >
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
            <div className="mt-5 font-mono text-caption uppercase text-ink-subtle">
              App
            </div>
            <ul className="mt-2 space-y-0.5">
              <li>
                <Link
                  href="/dashboard"
                  className={`block rounded px-3 py-2 text-sm ${
                    section === "dashboard"
                      ? "bg-brand-50 text-brand-700"
                      : "text-ink hover:bg-surface-muted"
                  }`}
                >
                  Dashboard
                </Link>
              </li>
            </ul>
          </div>
        </div>
      )}
    </header>
  );
}

function ActiveUnderline() {
  return (
    <span
      aria-hidden
      className="pointer-events-none absolute inset-x-3 bottom-0 h-[2px] rounded-t bg-brand-500"
    />
  );
}
