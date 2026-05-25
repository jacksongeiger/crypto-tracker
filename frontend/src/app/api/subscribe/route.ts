import { NextResponse } from "next/server";
import { sql } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// RFC 5322-lite: enough to filter out garbage, lenient on plus-tags / subdomains.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function POST(req: Request) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json(
      { ok: false, error: "Invalid JSON" },
      { status: 400 },
    );
  }
  const raw = (body as { email?: unknown })?.email;
  if (typeof raw !== "string") {
    return NextResponse.json(
      { ok: false, error: "Email required" },
      { status: 400 },
    );
  }
  const email = raw.trim();
  if (!email || email.length > 320 || !EMAIL_RE.test(email)) {
    return NextResponse.json(
      { ok: false, error: "Please enter a valid email address." },
      { status: 400 },
    );
  }

  try {
    // ON CONFLICT DO NOTHING — preserves the original created_at for repeat
    // submissions and lets us report `already: true` distinctly from `ok: true`.
    // unsubscribed_at is cleared on re-subscribe so the digest fans out to them.
    const rows = await sql<{ id: string; created_at: Date }[]>`
      INSERT INTO subscribers (email)
      VALUES (${email})
      ON CONFLICT (lower(email)) DO UPDATE
        SET unsubscribed_at = NULL
        WHERE subscribers.unsubscribed_at IS NOT NULL
      RETURNING id, created_at
    `;
    const inserted = rows.length > 0;
    return NextResponse.json({
      ok: true,
      already: !inserted,
    });
  } catch (err) {
    console.error("/api/subscribe error", err);
    return NextResponse.json(
      { ok: false, error: "Server error — try again later." },
      { status: 500 },
    );
  }
}
