"use client";

import { useEffect, useState } from "react";

type Subscriber = {
  id: string;
  email: string;
  created_at: string;
  unsubscribed_at: string | null;
};

export default function AdminSubscribersPage() {
  const [token, setToken] = useState("");
  const [authed, setAuthed] = useState(false);
  const [subscribers, setSubscribers] = useState<Subscriber[]>([]);
  const [counts, setCounts] = useState({ active: 0, total: 0 });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Restore the token from sessionStorage so the page doesn't re-prompt on
  // every refresh during an admin session. Token never leaves the browser
  // except as a header on /api/admin/* requests.
  useEffect(() => {
    const saved = sessionStorage.getItem("admin_token") || "";
    if (saved) {
      setToken(saved);
      void load(saved);
    }
  }, []);

  async function load(t: string) {
    setLoading(true);
    setError("");
    try {
      const r = await fetch("/api/admin/subscribers", {
        headers: { "X-Admin-Token": t },
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok || !d.ok) {
        setError(d.error || `HTTP ${r.status}`);
        setAuthed(false);
        return;
      }
      setSubscribers(d.subscribers || []);
      setCounts({ active: d.count_active || 0, total: d.count_total || 0 });
      setAuthed(true);
      sessionStorage.setItem("admin_token", t);
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  }

  async function remove(id: string, email: string) {
    if (!confirm(`Remove ${email}? This is permanent.`)) return;
    const r = await fetch(`/api/admin/subscribers/${id}`, {
      method: "DELETE",
      headers: { "X-Admin-Token": token },
    });
    if (r.ok) {
      setSubscribers((prev) => prev.filter((s) => s.id !== id));
      setCounts((c) => ({ active: c.active - 1, total: c.total - 1 }));
    } else {
      const d = await r.json().catch(() => ({}));
      alert(`Failed: ${d.error || r.status}`);
    }
  }

  function signOut() {
    sessionStorage.removeItem("admin_token");
    setToken("");
    setAuthed(false);
    setSubscribers([]);
  }

  if (!authed) {
    return (
      <main className="mx-auto max-w-md px-6 py-24">
        <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-brand-500">
          Admin · Subscribers
        </p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
          Sign in
        </h1>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void load(token);
          }}
          className="mt-6 flex flex-col gap-3"
        >
          <input
            type="password"
            placeholder="Admin token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            autoFocus
            className="rounded-md border border-line bg-surface px-3 py-2 text-[14px] text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
          />
          <button
            type="submit"
            disabled={!token || loading}
            className="rounded-md bg-brand-500 px-4 py-2 text-[14px] font-medium text-white hover:bg-brand-600 disabled:opacity-50"
          >
            {loading ? "Checking…" : "Sign in"}
          </button>
          {error ? (
            <p className="text-[13px] text-danger-dark">{error}</p>
          ) : null}
        </form>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-baseline justify-between">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-brand-500">
            Admin · Subscribers
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
            Mailing list
          </h1>
          <p className="mt-1 text-[13px] text-ink-muted">
            {counts.active} active · {counts.total} total
          </p>
        </div>
        <button
          onClick={signOut}
          className="text-[12px] font-medium text-ink-subtle hover:text-ink"
        >
          Sign out
        </button>
      </div>

      <div className="mt-8 overflow-hidden rounded-md border border-line-subtle">
        <table className="w-full text-left text-[13px]">
          <thead className="bg-surface-muted">
            <tr>
              <th className="px-4 py-2 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-subtle">
                Email
              </th>
              <th className="px-4 py-2 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-subtle">
                Subscribed
              </th>
              <th className="px-4 py-2 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-subtle">
                Status
              </th>
              <th className="px-4 py-2 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-subtle">
                {" "}
              </th>
            </tr>
          </thead>
          <tbody>
            {subscribers.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="px-4 py-6 text-center text-ink-muted"
                >
                  No subscribers yet.
                </td>
              </tr>
            ) : (
              subscribers.map((s) => (
                <tr key={s.id} className="border-t border-line-subtle">
                  <td className="px-4 py-2 text-ink">{s.email}</td>
                  <td className="px-4 py-2 text-ink-muted">
                    {new Date(s.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2">
                    {s.unsubscribed_at ? (
                      <span className="font-mono text-[11px] uppercase tracking-[0.1em] text-danger-dark">
                        Unsubscribed
                      </span>
                    ) : (
                      <span className="font-mono text-[11px] uppercase tracking-[0.1em] text-success-dark">
                        Active
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => remove(s.id, s.email)}
                      className="text-[12px] font-medium text-danger-dark hover:underline"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
