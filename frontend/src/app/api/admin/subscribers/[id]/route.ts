import { NextResponse } from "next/server";
import { sql } from "@/lib/db";
import { checkAdminToken } from "@/lib/admin-auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function DELETE(
  req: Request,
  { params }: { params: { id: string } },
) {
  const gate = checkAdminToken(req);
  if (!gate.ok) {
    return NextResponse.json(
      { ok: false, error: gate.reason },
      { status: gate.status },
    );
  }
  const id = params.id;
  if (!UUID_RE.test(id)) {
    return NextResponse.json(
      { ok: false, error: "Invalid id" },
      { status: 400 },
    );
  }
  try {
    // Hard delete — recipient lists should not include rows we marked as
    // removed in admin. Subscribers can always re-sign-up later.
    const rows = await sql<{ email: string }[]>`
      DELETE FROM subscribers WHERE id = ${id}
      RETURNING email
    `;
    if (rows.length === 0) {
      return NextResponse.json(
        { ok: false, error: "Not found" },
        { status: 404 },
      );
    }
    return NextResponse.json({ ok: true, email: rows[0].email });
  } catch (err) {
    console.error("/api/admin/subscribers DELETE error", err);
    return NextResponse.json(
      { ok: false, error: "Server error" },
      { status: 500 },
    );
  }
}
