import postgres from "postgres";

const connectionString = process.env.DATABASE_URL;
if (!connectionString) {
  throw new Error("DATABASE_URL is not set in frontend/.env.local");
}

declare global {
  // eslint-disable-next-line no-var
  var _sql: ReturnType<typeof postgres> | undefined;
}

// postgres.js ignores ?host= in the URL — pass it as an option instead.
// Set PGHOST=/var/run/postgresql on Linux servers to use the local socket
// (peer auth). Unset on macOS (Postgres.app) uses default TCP localhost.
const host = process.env.PGHOST;

export const sql =
  global._sql ??
  postgres(connectionString, {
    max: 5,
    idle_timeout: 30,
    prepare: false,
    ...(host ? { host } : {}),
  });

if (process.env.NODE_ENV !== "production") {
  global._sql = sql;
}
