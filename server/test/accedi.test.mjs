import { test } from "node:test";
import assert from "node:assert/strict";
import { hashCodice } from "../lib/codice.mjs";
import { gestisci } from "../netlify/functions/accedi.mjs";
import { dbFinto } from "./finti.mjs";

const CODICE = "AIR-0000-1111-2222-3333";

function conLicenza(stato = "attiva") {
  const db = dbFinto();
  db.stato.licenze.push({ id: "L1", hash_codice: hashCodice(CODICE), email: "Studio@Esempio.it", piano: "base", stato, ultime_cifre: "3333", postazioni_max: 1 });
  db.stato.lotti.push({ licenza_id: "L1", residuo: 7, riferimento: "x" });
  return db;
}

const accedi = (corpo, metodo = "POST") => new Request("https://airender.prova/api/accedi", {
  method: metodo, headers: { "content-type": "application/json" }, body: metodo === "POST" ? JSON.stringify(corpo) : undefined,
});

test("email e codice della stessa licenza: si entra, l'email non distingue maiuscole", async () => {
  const r = await gestisci(accedi({ email: " studio@esempio.IT ", codice: CODICE.toLowerCase() }), { db: conLicenza() });
  assert.equal(r.status, 200);
  const corpo = await r.json();
  assert.equal(corpo.piano, "base");
  assert.equal(corpo.saldo, 7);
  assert.equal(corpo.ultime_cifre, "3333");
});

test("email sbagliata e codice sconosciuto danno lo stesso rifiuto", async () => {
  const sbagliata = await gestisci(accedi({ email: "altro@esempio.it", codice: CODICE }), { db: conLicenza() });
  const sconosciuto = await gestisci(accedi({ email: "studio@esempio.it", codice: "AIR-9999-9999-9999-9999" }), { db: conLicenza() });
  assert.equal(sbagliata.status, 401);
  assert.equal(sconosciuto.status, 401);
  assert.deepEqual(await sbagliata.json(), await sconosciuto.json());
});

test("una licenza sospesa lo dice; moduli incompleti si fermano prima del database", async () => {
  const sospesa = await gestisci(accedi({ email: "studio@esempio.it", codice: CODICE }), { db: conLicenza("sospesa") });
  assert.equal(sospesa.status, 403);
  assert.equal((await sospesa.json()).error.type, "licenza_sospesa");
  const db = conLicenza();
  assert.equal((await gestisci(accedi({ email: "", codice: CODICE }), { db })).status, 400);
  assert.equal((await gestisci(accedi({ email: "a@b.it", codice: "AIR-1" }), { db })).status, 400);
  assert.equal((await gestisci(accedi({}, "GET"), { db })).status, 405);
});
