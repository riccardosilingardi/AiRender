// Le funzioni SQL su un Postgres vero. Serve psql e un database vuoto in
// AIRENDER_PG (es. "postgresql://postgres@localhost/airender_prova"): senza,
// il test si salta e lo dice.
import { execFileSync } from "node:child_process";
import { test } from "node:test";
import assert from "node:assert/strict";

const db = process.env.AIRENDER_PG;
const qui = new URL(".", import.meta.url).pathname;

test("le funzioni SQL dei crediti reggono riserva, addebito, annullo e scadenze", { skip: !db && "AIRENDER_PG non impostata" }, () => {
  const psql = (file) => execFileSync("psql", ["-v", "ON_ERROR_STOP=1", "-q", "-d", db, "-f", file], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  psql(`${qui}../supabase/migrations/001_crediti.sql`);
  const uscita = execFileSync("psql", ["-v", "ON_ERROR_STOP=1", "-q", "-d", db, "-f", `${qui}crediti.sql`], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  assert.equal(typeof uscita, "string");
});

test("il link di accesso vale una volta, scade, e la chiave che crea apre la licenza finche' non e' revocata", { skip: !db && "AIRENDER_PG non impostata" }, () => {
  const psql = (file) => execFileSync("psql", ["-v", "ON_ERROR_STOP=1", "-q", "-d", db, "-f", file], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  psql(`${qui}../supabase/migrations/001_crediti.sql`);
  psql(`${qui}../supabase/migrations/004_accesso_link.sql`);
  psql(`${qui}link.sql`);
});

test("i render senza immagine si rimborsano fino al tetto delle 24 ore, poi si pagano", { skip: !db && "AIRENDER_PG non impostata" }, () => {
  const psql = (file) => execFileSync("psql", ["-v", "ON_ERROR_STOP=1", "-q", "-d", db, "-f", file], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  psql(`${qui}../supabase/migrations/001_crediti.sql`);
  psql(`${qui}../supabase/migrations/005_tetto_rimborsi.sql`);
  psql(`${qui}rimborsi.sql`);
});
