// Lightweight token gate for admin endpoints. Token lives in
// frontend/.env.local as ADMIN_TOKEN; missing env -> all requests rejected.
// Compares constant-time and reads the value from either the X-Admin-Token
// header or a `?token=` query parameter.

import { timingSafeEqual } from "node:crypto";

export function checkAdminToken(req: Request): {
  ok: boolean;
  status: number;
  reason?: string;
} {
  const expected = process.env.ADMIN_TOKEN;
  if (!expected || expected.length < 16) {
    return { ok: false, status: 500, reason: "ADMIN_TOKEN not set on server" };
  }
  const url = new URL(req.url);
  const provided =
    req.headers.get("x-admin-token") ?? url.searchParams.get("token") ?? "";
  if (!provided) {
    return { ok: false, status: 401, reason: "Token required" };
  }
  const a = Buffer.from(provided);
  const b = Buffer.from(expected);
  if (a.length !== b.length) {
    return { ok: false, status: 403, reason: "Invalid token" };
  }
  if (!timingSafeEqual(a, b)) {
    return { ok: false, status: 403, reason: "Invalid token" };
  }
  return { ok: true, status: 200 };
}
