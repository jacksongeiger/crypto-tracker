"use client";

import { useState, type FormEvent } from "react";

export function SignupFooter() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "submitting" | "ok" | "error">(
    "idle",
  );
  const [message, setMessage] = useState("");

  async function onSubmit(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    if (state === "submitting") return;
    setState("submitting");
    setMessage("");
    try {
      const r = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const d = (await r.json().catch(() => ({}))) as {
        ok?: boolean;
        error?: string;
        already?: boolean;
      };
      if (r.ok && d.ok) {
        setState("ok");
        setMessage(
          d.already
            ? "You're already on the list."
            : "Subscribed. The next brief lands tomorrow at 7:10 AM PT.",
        );
        setEmail("");
        return;
      }
      setState("error");
      setMessage(d.error || "Something went wrong.");
    } catch {
      setState("error");
      setMessage("Network error — try again.");
    }
  }

  return (
    <footer className="mt-16 border-t border-line-subtle bg-surface-muted">
      <div className="mx-auto max-w-5xl px-6 py-12 sm:px-8">
        <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-brand-500">
          Daily brief, in your inbox
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
          Get the morning email.
        </h2>
        <p className="mt-2 max-w-prose text-bodyLg text-ink-muted">
          The same TL;DR, crypto + AI headlines, and market sentiment you see
          here — delivered to your inbox at 7:10 AM PT.
        </p>
        <form
          onSubmit={onSubmit}
          className="mt-6 flex max-w-md flex-col gap-3 sm:flex-row sm:items-center sm:gap-2"
          aria-describedby="signup-msg"
        >
          <label htmlFor="signup-email" className="sr-only">
            Email address
          </label>
          <input
            id="signup-email"
            type="email"
            required
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="flex-1 rounded-md border border-line bg-surface px-3 py-2 text-[14px] text-ink placeholder:text-ink-disabled focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
            disabled={state === "submitting"}
          />
          <button
            type="submit"
            disabled={state === "submitting" || !email}
            className="rounded-md bg-brand-500 px-4 py-2 text-[14px] font-medium text-white transition hover:bg-brand-600 disabled:opacity-50"
          >
            {state === "submitting" ? "Subscribing…" : "Subscribe"}
          </button>
        </form>
        <p
          id="signup-msg"
          className={`mt-3 min-h-[1.25rem] text-[13px] ${
            state === "ok"
              ? "text-success-dark"
              : state === "error"
                ? "text-danger-dark"
                : "text-ink-muted"
          }`}
          aria-live="polite"
        >
          {message}
        </p>
        <p className="mt-8 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-subtle">
          Merkavian Intelligence
        </p>
      </div>
    </footer>
  );
}
