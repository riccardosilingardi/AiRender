import { test } from "node:test";
import assert from "node:assert/strict";
import { VariabileMancante } from "../lib/ambiente.mjs";
import { protetto } from "../lib/risposte.mjs";
import { gestisci } from "../netlify/functions/router.mjs";
import { hashCodice } from "../lib/codice.mjs";
import { dbFinto, fetchFinto } from "./finti.mjs";

const req = () => new Request("https://airender.prova/api/saldo", { headers: { "x-airender-licenza": "AIR-0000-1111-2222-3333" } });

test("un'eccezione imprevista diventa un errore JSON in italiano e una riga di log senza il codice licenza", async () => {
  const righe = [];
  const f = protetto("saldo", async () => { throw new Error("Supabase airender_licenza: 500 giu'"); }, (r) => righe.push(r));
  const r = await f(req());
  assert.equal(r.status, 500);
  const corpo = await r.json();
  assert.equal(corpo.error.type, "errore_interno");
  assert.ok(corpo.cosa_fare);
  assert.equal(righe.length, 1);
  const riga = JSON.parse(righe[0]);
  assert.equal(riga.funzione, "saldo");
  assert.equal(riga.percorso, "/api/saldo");
  assert.ok(!righe[0].includes("AIR-0000"));
});

test("una variabile d'ambiente mancante risponde 503 servizio_non_configurato", async () => {
  const f = protetto("saldo", async () => { throw new VariabileMancante("Manca SITO_URL"); }, () => {});
  const r = await f(req());
  assert.equal(r.status, 503);
  assert.equal((await r.json()).error.type, "servizio_non_configurato");
});

test("senza COMFY_API_KEY il router si ferma prima di riservare credito", async () => {
  const db = dbFinto();
  const CODICE = "AIR-0000-1111-2222-3333";
  db.stato.licenze.push({ id: "L1", hash_codice: hashCodice(CODICE), email: "a@b.it", piano: "pro", stato: "attiva", ultime_cifre: "3333", postazioni_max: 1 });
  db.stato.lotti.push({ licenza_id: "L1", residuo: 10, riferimento: "x" });
  const chiama = fetchFinto([]);
  const invio = new Request("https://airender.prova/v2/models/vertexai/gemini-3.1-flash-image/requests", {
    method: "POST",
    headers: { "x-airender-licenza": CODICE, "x-airender-postazione": "pc-1", "idempotency-key": "k1", "content-type": "application/json" },
    body: JSON.stringify({ contents: [], generationConfig: { imageConfig: { imageSize: "2K" } } }),
  });
  await assert.rejects(gestisci(invio, { db, ambiente: {}, chiama }), VariabileMancante);
  assert.equal((db.stato.render || []).length, 0);
  assert.equal(chiama.chiamate.length, 0);
});
