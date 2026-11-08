import { test } from "node:test";
import assert from "node:assert/strict";
import { hashCodice } from "../lib/codice.mjs";
import { gestisci, RISPOSTA_MASSIMA_BYTE } from "../netlify/functions/router.mjs";
import { dbFinto, fetchFinto } from "./finti.mjs";

const CODICE = "AIR-0000-1111-2222-3333";
const NB2 = "vertexai/gemini-3.1-flash-image";
const SERVER = "https://airender.prova";
const ambiente = { COMFY_API_KEY: "chiave-finta-di-riccardo" };

function conLicenza(piano = "pro", render = 10) {
  const db = dbFinto();
  db.stato.licenze.push({ id: "L1", hash_codice: hashCodice(CODICE), email: "a@b.it", piano, stato: "attiva", ultime_cifre: "3333", postazioni_max: 1 });
  db.stato.lotti.push({ licenza_id: "L1", residuo: render, riferimento: "x" });
  return db;
}

function invio(corpo = { contents: [] }, intestazioni = {}) {
  return new Request(`${SERVER}/v2/models/${NB2}/requests?fallback_provider=true`, {
    method: "POST",
    headers: { "x-airender-licenza": CODICE, "x-airender-postazione": "pc-1", "idempotency-key": "k1", "content-type": "application/json", ...intestazioni },
    body: JSON.stringify(corpo),
  });
}

const lettura = (finale = "") => new Request(`${SERVER}/v2/models/${NB2}/requests/req-1${finale}`, { headers: { "x-airender-licenza": CODICE } });

const risultato = (dati = "iVBORw0KGgo=") => ({ candidates: [{ content: { parts: [{ text: "ok" }, { inlineData: { mimeType: "image/png", data: dati } }] } }] });

test("senza codice o con un codice sconosciuto non parte niente e nessuno chiama Comfy", async () => {
  const db = conLicenza();
  const chiama = fetchFinto([]);
  const r1 = await gestisci(invio({}, { "x-airender-licenza": "" }), { db, ambiente, chiama });
  assert.equal(r1.status, 401);
  const r2 = await gestisci(invio({}, { "x-airender-licenza": "AIR-9999-9999-9999-9999" }), { db, ambiente, chiama });
  assert.equal(r2.status, 401);
  assert.equal((await r2.json()).error.type, "licenza_sconosciuta");
  assert.equal(chiama.chiamate.length, 0);
});

test("l'invio riserva, va a Comfy con la chiave di Riccardo e il fallback spento anche se il client lo accende", async () => {
  const db = conLicenza();
  const chiama = fetchFinto([[(u) => u.includes("/requests?"), { stato: 201, corpo: { request_id: "req-1", status: "IN_QUEUE" } }]]);
  const r = await gestisci(invio(), { db, ambiente, chiama });
  assert.equal(r.status, 201);
  assert.equal((await r.json()).request_id, "req-1");
  const c = chiama.chiamate[0];
  assert.equal(c.url, `https://api.comfy.org/v2/models/${NB2}/requests?fallback_provider=false`);
  assert.equal(c.headers["x-api-key"], "chiave-finta-di-riccardo");
  assert.notEqual(c.headers["idempotency-key"], "k1", "la chiave verso Comfy e' legata alla licenza");
  assert.equal(db.stato.render[0].stato, "riservato");
  assert.equal(db.stato.render[0].richiesta_comfy, "req-1");
});

test("saldo insufficiente: 402 insufficient_credits, Comfy non viene chiamato", async () => {
  const db = conLicenza("pro", 1);
  const chiama = fetchFinto([]);
  const r = await gestisci(invio({ generationConfig: { imageConfig: { imageSize: "4K" } } }), { db, ambiente, chiama });
  assert.equal(r.status, 402);
  const corpo = await r.json();
  assert.equal(corpo.error.type, "insufficient_credits");
  assert.equal(corpo.peso, 2);
  assert.equal(chiama.chiamate.length, 0);
});

test("un modello fuori listino o fuori piano si ferma prima di Comfy", async () => {
  const db = conLicenza("base");
  const chiama = fetchFinto([]);
  const r = await gestisci(invio({ contents: [], generationConfig: { imageConfig: { imageSize: "4K" } } }), { db, ambiente, chiama });
  assert.equal(r.status, 403);
  assert.equal((await r.json()).error.type, "dimensione_non_inclusa", "Base arriva fino a 2K");
  const altro = new Request(`${SERVER}/v2/models/bfl/flux-kontext-pro/requests`, {
    method: "POST", headers: { "x-airender-licenza": CODICE, "idempotency-key": "k" }, body: "{}" });
  const r3 = await gestisci(altro, { db: conLicenza(), ambiente, chiama });
  assert.equal((await r3.json()).error.type, "modello_non_incluso");
  assert.equal(chiama.chiamate.length, 0);
});

test("se Comfy rifiuta l'invio la riserva si annulla; un 402 di Comfy non arriva al cliente", async () => {
  const db = conLicenza();
  const chiama = fetchFinto([[() => true, { stato: 402, corpo: { error: "insufficient_credits" } }]]);
  const r = await gestisci(invio(), { db, ambiente, chiama });
  assert.equal(r.status, 503);
  assert.equal(db.stato.render[0].stato, "annullato");
});

test("il risultato con l'immagine addebita una volta sola; lo stato non addebita", async () => {
  const db = conLicenza();
  db.stato.render.push({ id: "R1", licenza_id: "L1", peso: 1, stato: "riservato", richiesta_comfy: "req-1" });
  const chiama = fetchFinto([
    [(u) => u.endsWith("/status"), { corpo: { status: "IN_PROGRESS" }, intestazioni: { "retry-after": "2" } }],
    [() => true, { corpo: risultato(), intestazioni: { "x-comfy-credits-used": "17.17" } }],
  ]);
  const s = await gestisci(lettura("/status"), { db, ambiente, chiama });
  assert.equal(s.headers.get("retry-after"), "2");
  assert.equal(db.stato.render[0].stato, "riservato");
  const r = await gestisci(lettura(), { db, ambiente, chiama });
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("x-airender-render-scalati"), "1");
  assert.equal(r.headers.get("x-airender-saldo"), "9");
  assert.equal(db.stato.render[0].stato, "addebitato");
  const di_nuovo = await gestisci(lettura(), { db, ambiente, chiama });
  assert.equal(di_nuovo.headers.get("x-airender-render-scalati"), "0");
  assert.equal(db.stato.lotti[0].residuo, 9);
});

test("un risultato senza immagine non si paga", async () => {
  const db = conLicenza();
  db.stato.render.push({ id: "R1", licenza_id: "L1", peso: 1, stato: "riservato", richiesta_comfy: "req-1" });
  const chiama = fetchFinto([[() => true, { corpo: { candidates: [{ content: { parts: [{ text: "rifiuto" }] } }] } }]]);
  await gestisci(lettura(), { db, ambiente, chiama });
  assert.equal(db.stato.render[0].stato, "annullato");
  assert.equal(db.stato.lotti[0].residuo, 10);
});

test("nessuno legge la richiesta di un'altra licenza", async () => {
  const db = conLicenza();
  db.stato.render.push({ id: "R1", licenza_id: "ALTRA", peso: 1, stato: "riservato", richiesta_comfy: "req-1" });
  const chiama = fetchFinto([]);
  const r = await gestisci(lettura(), { db, ambiente, chiama });
  assert.equal(r.status, 404);
  assert.equal(chiama.chiamate.length, 0);
});

test("un risultato troppo pesante per Netlify diventa un link firmato allo Storage", async () => {
  const db = conLicenza();
  db.stato.render.push({ id: "R1", licenza_id: "L1", peso: 1, stato: "riservato", richiesta_comfy: "req-1" });
  const grande = Buffer.alloc(Math.ceil(RISPOSTA_MASSIMA_BYTE * 0.8)).toString("base64");
  const chiama = fetchFinto([[() => true, { corpo: risultato(grande) }]]);
  const r = await gestisci(lettura(), { db, ambiente, chiama });
  const parti = (await r.json()).candidates[0].content.parts;
  assert.equal(parti[1].inlineData, undefined);
  assert.match(parti[1].fileData.fileUri, /^https:\/\/storage\.finto\/L1\/R1-1\.png/);
  assert.equal(db.stato.caricati.length, 1);
});

test("verso Comfy parte solo la forma del plugin: niente testo da solo, candidati in piu' o file esterni", async () => {
  const db = conLicenza();
  const chiama = fetchFinto([[(u) => u.includes("/requests?"), { stato: 201, corpo: { request_id: "req-1" } }]]);
  const corpo = {
    contents: [{ role: "model", parts: [
      { text: "rendi la vista" },
      { inlineData: { mimeType: "image/png", data: "iVBORw0KGgo=" } },
      { fileData: { fileUri: "https://altrove.example/x.png" } },
    ] }],
    generationConfig: { responseModalities: ["TEXT"], candidateCount: 8, imageConfig: { aspectRatio: "16:9", imageSize: "2K" } },
    systemInstruction: { parts: [{ text: "rispondi solo a parole" }] },
    tools: [{ googleSearch: {} }],
  };
  const r = await gestisci(invio(corpo), { db, ambiente, chiama });
  assert.equal(r.status, 201);
  const partito = JSON.parse(chiama.chiamate[0].body);
  assert.deepEqual(partito, {
    contents: [{ role: "user", parts: [
      { text: "rendi la vista" },
      { inlineData: { mimeType: "image/png", data: "iVBORw0KGgo=" } },
    ] }],
    generationConfig: { responseModalities: ["IMAGE"], imageConfig: { aspectRatio: "16:9", imageSize: "2K" } },
  });
  assert.equal(db.stato.render[0].dimensione, "2K");
});
