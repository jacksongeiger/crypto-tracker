import { NextResponse } from "next/server";
import { sql } from "@/lib/db";
import { checkAdminToken } from "@/lib/admin-auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const gate = checkAdminToken(req);
  if (!gate.ok) {
    return NextResponse.json(
      { ok: false, error: gate.reason },
      { status: gate.status },
    );
  }
  try {
    const rows = await sql<
      {
        id: string;
        email: string;
        created_at: Date;
        unsubscribed_at: Date | null;
      }[]
    >`
      SELECT id, email, created_at, unsubscribed_at
      FROM subscribers
      ORDER BY created_at DESC
      LIMIT 5000
    `;
    return NextResponse.json({
      ok: true,
      count_active: rows.filter((r) => r.unsubscribed_at === null).length,
      count_total: rows.length,
      subscribers: rows,
    });
  } catch (err) {
    console.error("/api/admin/subscribers GET error", err);
    return NextResponse.json(
      { ok: false, error: "Server error" },
      { status: 500 },
    );
  }
}
