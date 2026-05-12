import postgres from "postgres";

const connectionString = process.env.DATABASE_URL;
if (!connectionString) {
  throw new Error("DATABASE_URL is not set in frontend/.env.local");
}

declare global {
  // eslint-disable-next-line no-var
  var _sql: ReturnType<typeof postgres> | undefined;
}

export const sql =
  global._sql ??
  postgres(connectionString, {
    max: 5,
    idle_timeout: 30,
    prepare: false,
  });

if (process.env.NODE_ENV !== "production") {
  global._sql = sql;
}
