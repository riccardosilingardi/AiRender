import { test } from "node:test";
import assert from "node:assert/strict";
import { hashCodice } from "../lib/codice.mjs";
import { listino } from "../lib/listino.mjs";
import { gestisci as accedi } from "../netlify/functions/accedi.mjs";
import { gestisci as chiediLink, sitoDelLink } from "../netlify/functions/link-accesso.mjs";
import { gestisci as saldo } from "../netlify/functions/saldo.mjs";
import { dbFinto } from "./finti.mjs";

const AMBIENTE = { SITO_URL: "https://airender.prova/", AIRENDER_FIRMA: "s" };

function preparato() {
  const db = dbFinto();
  db.stato.licenze.push({ id: "L1", hash_codice: hashCodice("AIR-0000-1111-2222-3333"), email: "Studio@Esempio.it", piano: "pro", stato: "attiva", ultime_cifre: "3333", postazioni_max: 2 });
  db.stato.licenze.push({ id: "L2", hash_codice: hashCodice("AIR-4444-5555-6666-7777"), email: "studio@esempio.it", piano: "prova", stato: "attiva", ultime_cifre: "7777", postazioni_max: 1 });
  db.stato.lotti.push({ licenza_id: "L1", residuo: 19, riferimento: "x" });
  const inviate = [];
  const posta = { inviaLink: async (a, voci, minuti) => inviate.push({ a, voci, minuti }) };
  let n = 0;
  const casuale = (k) => Buffer.alloc(k, ++n);
  return { db, inviate, opzioni: { ambiente: AMBIENTE, db, email: posta, casuale } };
}

const richiesta = (percorso, corpo) => new Request(`https://airender.prova${percorso}`, {
  method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(corpo),
});
const gettoneDi = (voce) => voce.link.split("#accesso=")[1];

test("un'email con due licenze riceve un link per ciascuna, verso il sito AIRENDER", async () => {
  const { inviate, opzioni } = preparato();
  const r = await chiediLink(richiesta("/api/link-accesso", { email: " STUDIO@esempio.it " }), opzioni);
  assert.equal(r.status, 200);
  assert.equal(inviate.length, 1);
  assert.equal(inviate[0].a, "studio@esempio.it");
  assert.equal(inviate[0].minuti, listino.accesso.link_minuti);
  assert.deepEqual(inviate[0].voci.map((v) => v.ultime_cifre), ["3333", "7777"]);
  assert.ok(inviate[0].voci.every((v) => v.link.startsWith("https://airender.prova/studio/#accesso=")));
});

test("un'email sconosciuta ha la stessa risposta e nessuna email parte", async () => {
  const { inviate, opzioni } = preparato();
  const nota = await chiediLink(richiesta("/api/link-accesso", { email: "studio@esempio.it" }), opzioni);
  const ignota = await chiediLink(richiesta("/api/link-accesso", { email: "chi@altro.it" }), opzioni);
  assert.equal(ignota.status, nota.status);
  assert.equal((await ignota.json()).inviata, true);
  assert.equal(inviate.length, 1);
});

test("il link si scambia una volta sola con una chiave che vale come il codice", async () => {
  const { db, inviate, opzioni } = preparato();
  await chiediLink(richiesta("/api/link-accesso", { email: "studio@esempio.it" }), opzioni);
  const gettone = gettoneDi(inviate[0].voci[0]);
  const r = await accedi(richiesta("/api/accedi", { link: gettone }), { db });
  assert.equal(r.status, 200);
  const corpo = await r.json();
  assert.equal(corpo.piano, "pro");
  assert.equal(corpo.saldo, 19);
  assert.match(corpo.codice, /^AIR-/);
  assert.notEqual(corpo.codice, "AIR-0000-1111-2222-3333");
  // la chiave apre il saldo della stessa licenza
  const s = await saldo(new Request("https://airender.prova/api/saldo", { headers: { "x-airender-licenza": corpo.codice } }), { ambiente: AMBIENTE, db });
  assert.equal((await s.json()).saldo, 19);
  // seconda volta: rifiutato
  const ancora = await accedi(richiesta("/api/accedi", { link: gettone }), { db });
  assert.equal(ancora.status, 401);
  assert.equal((await ancora.json()).error.type, "link_scaduto");
});

test("oltre il massimo per ora non partono altri link, e la risposta non cambia", async () => {
  const { inviate, opzioni } = preparato();
  for (let i = 0; i < listino.accesso.link_massimi_ora + 2; i++) {
    const r = await chiediLink(richiesta("/api/link-accesso", { email: "studio@esempio.it" }), opzioni);
    assert.equal(r.status, 200);
  }
  assert.equal(inviate.length, listino.accesso.link_massimi_ora);
});

test("l'indirizzo del link lo decide il server: anteprima Netlify o SITO_URL, mai la richiesta", () => {
  assert.equal(sitoDelLink({ SITO_URL: "https://a.it/" }), "https://a.it");
  assert.equal(sitoDelLink({ SITO_URL: "https://a.it", CONTEXT: "deploy-preview", DEPLOY_PRIME_URL: "https://dp--a.netlify.app" }), "https://dp--a.netlify.app");
  assert.equal(sitoDelLink({ SITO_URL: "https://a.it", CONTEXT: "production", DEPLOY_PRIME_URL: "https://x" }), "https://a.it");
});

test("un link malformato o un'email vuota si fermano prima del database", async () => {
  const { db, opzioni } = preparato();
  assert.equal((await accedi(richiesta("/api/accedi", { link: "corto" }), { db })).status, 400);
  assert.equal((await chiediLink(richiesta("/api/link-accesso", { email: "" }), opzioni)).status, 400);
  assert.deepEqual(db.stato.chiamate, []);
});
