import test from "node:test";
import assert from "node:assert/strict";
import { creaDb } from "../lib/db.mjs";

function cattura(ambiente) {
  const viste = [];
  const chiama = async (url, opzioni) => {
    viste.push(opzioni.headers);
    return new Response("[]", { status: 200 });
  };
  return { db: creaDb({ SUPABASE_URL: "https://x.supabase.co", ...ambiente }, chiama), viste };
}

test("la chiave segreta nuova viaggia solo in apikey, mai in Authorization", async () => {
  const { db, viste } = cattura({ SUPABASE_SECRET_KEY: "sb_secret_abc", SUPABASE_SERVICE_ROLE_KEY: "eyJvecchia" });
  await db.rpc("airender_saldo", {});
  assert.equal(viste[0].apikey, "sb_secret_abc");
  assert.equal(viste[0].authorization, undefined);
});

test("la service_role vecchia va in apikey e in Authorization", async () => {
  const { db, viste } = cattura({ SUPABASE_SERVICE_ROLE_KEY: "eyJvecchia" });
  await db.rpc("airender_saldo", {});
  assert.equal(viste[0].apikey, "eyJvecchia");
  assert.equal(viste[0].authorization, "Bearer eyJvecchia");
});
