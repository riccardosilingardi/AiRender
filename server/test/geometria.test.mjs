import { test } from "node:test";
import assert from "node:assert/strict";
import { hashCodice } from "../lib/codice.mjs";
import modello from "../geometria.json" with { type: "json" };
import { assetDelCliente, firmaAsset, gestisci, MODELLO } from "../netlify/functions/geometria.mjs";
import { dbFinto } from "./finti.mjs";

const CODICE = "AIR-0000-1111-2222-3333";
const SERVER = "https://airender.prova";
const DEPLOY = "https://airender-geometria.run.comfy.app";
const ambiente = { COMFY_API_KEY: "chiave-finta-di-riccardo", AIRENDER_COMFY_WORKFLOW_URL: DEPLOY + "/" };
// Un PNG di blocchi (CRC a zero: qui conta solo la forma), con un commento tEXt.
const blocco = (tipo, dati) => {
  const l = Buffer.alloc(4); l.writeUInt32BE(dati.length);
  return Buffer.concat([l, Buffer.from(tipo, "latin1"), dati, Buffer.alloc(4)]);
};
const PNG = Buffer.concat([Buffer.from("89504e470d0a1a0a", "hex"), blocco("IHDR", Buffer.alloc(13)),
  blocco("tEXt", Buffer.from("Comment\0ABCD", "latin1")), blocco("IDAT", Buffer.alloc(4)), blocco("IEND", Buffer.alloc(0))]);

function conLicenza(piano = "studio", render = 10) {
  const db = dbFinto();
  db.stato.licenze.push({ id: "L1", hash_codice: hashCodice(CODICE), email: "a@b.it", piano, stato: "attiva", ultime_cifre: "3333", postazioni_max: 3 });
  db.stato.lotti.push({ licenza_id: "L1", residuo: render, riferimento: "x" });
  return db;
}

// Il deployment finto: asset, job, stato che finisce dopo `letture`, uscita PNG.
function deployFinto({ finale = "succeeded", letture = 1, rifiutaInvio = 0 } = {}) {
  const chiamate = [];
  let lette = 0;
  const f = async (url, opzioni = {}) => {
    chiamate.push({ url: String(url), ...opzioni });
    const u = new URL(url);
    const j = (stato, corpo) => new Response(JSON.stringify(corpo), { status: stato, headers: { "content-type": "application/json" } });
    if (u.pathname === "/api/v2/assets") return j(201, { id: "asset-7" });
    if (u.pathname === "/api/v2/jobs" && opzioni.method === "POST") {
      return rifiutaInvio ? j(rifiutaInvio, { message: "no" }) : j(201, { id: "job-1", status: "queued", urls: { self: "/x/job-1" } });
    }
    if (u.pathname === "/api/v2/jobs/job-1") {
      lette += 1;
      if (lette <= letture) return j(200, { id: "job-1", status: "running", outputs: [] });
      return j(200, { id: "job-1", status: finale, outputs: finale === "succeeded" ? [{ node_id: "16", url: "/api/v2/assets/out-1/content" }] : [],
        error: finale === "failed" ? { message: "nodo rotto" } : undefined });
    }
    if (u.pathname === "/api/v2/jobs/job-1/cancel") return j(200, {});
    if (u.pathname === "/api/v2/assets/out-1/content") return new Response(PNG, { status: 200, headers: { "content-type": "image/png" } });
    throw new Error(`deploy finto: nessuna regola per ${url}`);
  };
  f.chiamate = chiamate;
  return f;
}

const intestazioni = (altro = {}) => ({ "x-airender-licenza": CODICE, "x-airender-postazione": "pc-1", "x-airender-canale": "plugin", ...altro });

function caricamento(altro = {}) {
  const modulo = new FormData();
  modulo.append("file_path", "vista.png");
  modulo.append("content_type", "image/png");
  modulo.append("file", new Blob([PNG], { type: "image/png" }), "vista.png");
  return new Request(`${SERVER}/geometria/api/v2/assets`, { method: "POST", headers: intestazioni(altro), body: modulo });
}

function grafoDelMotore(asset, prompt = "a house", seme = 42, controlli = "spigoli") {
  const g = structuredClone(modello.grafi[controlli]);
  g[modello.nodi.immagine].inputs.image = { __type: "core/ASSET", info: { id: asset } };
  g[modello.nodi.prompt].inputs.text = prompt;
  g[modello.nodi.campionatore].inputs.seed = seme;
  return g;
}

function invio(workflow, altro = {}) {
  return new Request(`${SERVER}/geometria/api/v2/jobs`, {
    method: "POST", headers: { ...intestazioni(altro), "idempotency-key": "k1", "content-type": "application/json" },
    body: JSON.stringify({ workflow }),
  });
}

const leggi = (percorso, metodo = "GET") => new Request(`${SERVER}/geometria/api/v2/jobs/${percorso}`, { method: metodo, headers: intestazioni() });

async function caricaEInvia(db, chiama, workflow) {
  const a = await gestisci(caricamento(), { db, ambiente, chiama });
  assert.equal(a.status, 201);
  const { id } = await a.json();
  return gestisci(invio(workflow ? workflow(id) : grafoDelMotore(id)), { db, ambiente, chiama });
}

test("un piano senza «Tieni la geometria» si ferma prima di Comfy, con la frase per l'utente", async () => {
  for (const piano of ["base", "pro", "prova", "nessuno"]) {
    const chiama = deployFinto();
    const r = await gestisci(caricamento(), { db: conLicenza(piano), ambiente, chiama });
    assert.equal(r.status, 403, piano);
    const corpo = await r.json();
    assert.equal(corpo.error.type, "funzione_non_inclusa");
    assert.match(corpo.cosa_fare, /Togli la spunta/);
    assert.equal(chiama.chiamate.length, 0);
  }
});

test("senza codice licenza non parte niente", async () => {
  const chiama = deployFinto();
  const r = await gestisci(caricamento({ "x-airender-licenza": "" }), { db: conLicenza(), ambiente, chiama });
  assert.equal(r.status, 401);
  assert.equal(chiama.chiamate.length, 0);
});

test("la vista si carica con la chiave di Riccardo, senza testi PNG, e torna un id firmato per la licenza", async () => {
  const chiama = deployFinto();
  const r = await gestisci(caricamento(), { db: conLicenza(), ambiente, chiama });
  assert.equal(r.status, 201);
  const { id } = await r.json();
  assert.equal(assetDelCliente("L1", id, ambiente.COMFY_API_KEY), "asset-7");
  assert.equal(assetDelCliente("L2", id, ambiente.COMFY_API_KEY), null, "un'altra licenza non lo usa");
  const c = chiama.chiamate[0];
  assert.equal(c.url, `${DEPLOY}/api/v2/assets`);
  assert.equal(c.headers.authorization, "Bearer chiave-finta-di-riccardo");
  const mandato = Buffer.from(await c.body.get("file").arrayBuffer());
  assert.equal(mandato.includes(Buffer.from("tEXt")), false, "il commento PNG non parte");
});

test("l'invio riserva il peso del listino, ricostruisce il grafo e manda solo asset, prompt e seme del client", async () => {
  const db = conLicenza();
  const chiama = deployFinto();
  const r = await caricaEInvia(db, chiama, (id) => {
    const g = grafoDelMotore(id, "a villa", 7);
    g["8"].inputs.strength = 0;   // il client prova a cambiare la forza
    g[modello.nodi.campionatore].inputs.steps = 200; // e i passi
    g["99"] = { class_type: "SaveImage", inputs: {} }; // e ad aggiungere un nodo
    return g;
  });
  assert.equal(r.status, 201);
  const lavoro = await r.json();
  assert.deepEqual(lavoro.urls, { self: "/geometria/api/v2/jobs/job-1", cancel: "/geometria/api/v2/jobs/job-1/cancel" });
  const c = chiama.chiamate.find((x) => x.url === `${DEPLOY}/api/v2/jobs`);
  assert.notEqual(c.headers["idempotency-key"], "k1");
  const mandato = JSON.parse(c.body).workflow;
  assert.equal(mandato["99"], undefined);
  assert.deepEqual(mandato["8"].inputs, modello.grafi.spigoli["8"].inputs);
  assert.equal(mandato[modello.nodi.campionatore].inputs.steps, modello.grafi.spigoli[modello.nodi.campionatore].inputs.steps);
  assert.equal(mandato[modello.nodi.campionatore].inputs.seed, 7);
  assert.equal(mandato[modello.nodi.prompt].inputs.text, "a villa");
  assert.deepEqual(mandato[modello.nodi.immagine].inputs.image, { __type: "core/ASSET", info: { id: "asset-7" } });
  const [render] = db.stato.render;
  assert.equal(render.modello, MODELLO);
  assert.equal(render.peso, 1);
  assert.equal(render.stato, "riservato");
  assert.equal(render.richiesta_comfy, "job-1");
});

test("un asset di un'altra licenza o non firmato non parte", async () => {
  const db = conLicenza();
  const chiama = deployFinto();
  const falso = `asset-7.${firmaAsset("L2", "asset-7", ambiente.COMFY_API_KEY)}`;
  for (const id of [falso, "asset-7", "asset-7.abc"]) {
    const r = await gestisci(invio(grafoDelMotore(id)), { db, ambiente, chiama });
    assert.equal(r.status, 403);
  }
  assert.equal(chiama.chiamate.length, 0);
  assert.equal(db.stato.render.length, 0);
});

test("saldo che non basta: 402 e il deployment non riceve il lavoro", async () => {
  const db = conLicenza("studio", 0);
  const chiama = deployFinto();
  const r = await caricaEInvia(db, chiama);
  assert.equal(r.status, 402);
  assert.equal(chiama.chiamate.some((c) => c.url.endsWith("/api/v2/jobs")), false);
});

test("si addebita solo quando il lavoro riesce con un'uscita, una volta sola; l'uscita passa dal server", async () => {
  const db = conLicenza();
  const chiama = deployFinto({ letture: 1 });
  await caricaEInvia(db, chiama);
  const primo = await gestisci(leggi("job-1"), { db, ambiente, chiama });
  assert.equal((await primo.json()).status, "running");
  assert.equal(db.stato.render[0].stato, "riservato");
  const proibito = await gestisci(leggi("job-1/outputs/0"), { db, ambiente, chiama });
  assert.equal(proibito.status, 409, "prima della fine non si scarica");

  const finito = await gestisci(leggi("job-1"), { db, ambiente, chiama });
  const corpo = await finito.json();
  assert.equal(corpo.status, "succeeded");
  assert.deepEqual(corpo.outputs, [{ node_id: "16", url: "/geometria/api/v2/jobs/job-1/outputs/0" }]);
  assert.equal(finito.headers.get("x-airender-render-scalati"), "1");
  assert.equal(db.stato.render[0].stato, "addebitato");
  const ancora = await gestisci(leggi("job-1"), { db, ambiente, chiama });
  assert.equal(ancora.headers.get("x-airender-render-scalati"), "0");
  assert.equal(db.stato.lotti[0].residuo, 9);

  const immagine = await gestisci(leggi("job-1/outputs/0"), { db, ambiente, chiama });
  assert.equal(immagine.status, 200);
  assert.equal(immagine.headers.get("content-type"), "image/png");
  assert.deepEqual(Buffer.from(await immagine.arrayBuffer()), PNG, "l'uscita arriva com'e'");
  const download = chiama.chiamate.find((c) => c.url.endsWith("/out-1/content"));
  assert.equal(download.headers.authorization, "Bearer chiave-finta-di-riccardo");
});

test("un lavoro fallito annulla la riserva e dice perche'", async () => {
  const db = conLicenza();
  const chiama = deployFinto({ finale: "failed", letture: 0 });
  await caricaEInvia(db, chiama);
  const r = await gestisci(leggi("job-1"), { db, ambiente, chiama });
  const corpo = await r.json();
  assert.equal(corpo.status, "failed");
  assert.equal(corpo.error.message, "nodo rotto");
  assert.equal(db.stato.render[0].stato, "annullato");
  assert.equal(db.stato.lotti[0].residuo, 10);
});

test("se il deployment rifiuta l'invio la riserva si annulla; un 401 di Comfy non arriva al cliente", async () => {
  const db = conLicenza();
  const r = await caricaEInvia(db, deployFinto({ rifiutaInvio: 401 }));
  assert.equal(r.status, 503);
  assert.equal((await r.json()).error.type, "servizio_non_disponibile");
  assert.equal(db.stato.render[0].stato, "annullato");
});

test("il cliente che smette di aspettare annulla, e il lavoro non si paga anche se poi finisce", async () => {
  const db = conLicenza();
  const chiama = deployFinto({ letture: 0 });
  await caricaEInvia(db, chiama);
  const r = await gestisci(leggi("job-1/cancel", "POST"), { db, ambiente, chiama });
  assert.equal(r.status, 200);
  assert.ok(chiama.chiamate.some((c) => c.url === `${DEPLOY}/api/v2/jobs/job-1/cancel`));
  assert.equal(db.stato.render[0].stato, "annullato");
  const dopo = await gestisci(leggi("job-1"), { db, ambiente, chiama });
  assert.equal(dopo.headers.get("x-airender-render-scalati"), "0");
  assert.equal(db.stato.render[0].stato, "annullato");
  assert.equal(db.stato.lotti[0].residuo, 10);
});

test("nessuno legge il lavoro di un'altra licenza", async () => {
  const db = conLicenza();
  const chiama = deployFinto();
  await caricaEInvia(db, chiama);
  db.stato.render[0].licenza_id = "L2";
  for (const p of ["job-1", "job-1/outputs/0"]) {
    assert.equal((await gestisci(leggi(p), { db, ambiente, chiama })).status, 404);
  }
});

test("senza indirizzo del deployment il server lo dice e non riserva", async () => {
  const db = conLicenza();
  const r = await gestisci(caricamento(), { db, ambiente: { COMFY_API_KEY: "k" }, chiama: deployFinto() }).catch((e) => e);
  assert.equal(r.name, "VariabileMancante");
  assert.equal(db.stato.render.length, 0);
});

test("i controlli scelti dal client scelgono il grafo: Profondita' e Linee dritte senza Spigoli", async () => {
  const db = conLicenza();
  const chiama = deployFinto();
  const r = await caricaEInvia(db, chiama, (id) => grafoDelMotore(id, "a house", 3, "profondita+linee"));
  assert.equal(r.status, 201);
  const mandato = JSON.parse(chiama.chiamate.find((x) => x.url === `${DEPLOY}/api/v2/jobs`).body).workflow;
  assert.equal(mandato["8"], undefined, "niente Spigoli");
  assert.equal(mandato["3"], undefined);
  assert.ok(mandato["18"] && mandato["20"]);
  assert.deepEqual(mandato["20"].inputs.model, ["18", 0]);
});

test("un grafo senza nessun controllo si rifiuta prima di riservare", async () => {
  const db = conLicenza();
  const chiama = deployFinto();
  const r = await caricaEInvia(db, chiama, (id) => {
    const g = grafoDelMotore(id);
    delete g["8"];
    return g;
  });
  assert.equal(r.status, 400);
  assert.equal(db.stato.render.length, 0);
});

test("«Riaggancia alla vista»: il render firmato entra nel latente, i controlli restano dalla vista", async () => {
  const db = conLicenza();
  const chiama = deployFinto();
  const a = await gestisci(caricamento(), { db, ambiente, chiama });
  const { id } = await a.json();
  const g = structuredClone(modello.grafi_riaggancia.spigoli);
  g[modello.nodi.immagine].inputs.image = { __type: "core/ASSET", info: { id } };
  g[modello.nodi.render].inputs.image = { __type: "core/ASSET", info: { id } };
  g[modello.nodi.prompt].inputs.text = "a house";
  g[modello.nodi.campionatore].inputs.seed = 7;
  const r = await gestisci(invio(g), { db, ambiente, chiama });
  assert.equal(r.status, 201);
  const mandato = JSON.parse(chiama.chiamate.find((x) => x.url === `${DEPLOY}/api/v2/jobs`).body).workflow;
  assert.equal(mandato["14"], undefined, "niente foglio vuoto");
  assert.deepEqual(mandato["9"].inputs.latent_image, ["23", 0]);
  assert.ok(mandato["9"].inputs.denoise < 1);
  assert.equal(mandato[modello.nodi.render].inputs.image.info.id, id.split(".")[0]);
});

test("«Riaggancia alla vista» con un render non firmato si rifiuta prima di riservare", async () => {
  const db = conLicenza();
  const chiama = deployFinto();
  const r = await caricaEInvia(db, chiama, (id) => {
    const g = structuredClone(modello.grafi_riaggancia.spigoli);
    g[modello.nodi.immagine].inputs.image = { __type: "core/ASSET", info: { id } };
    g[modello.nodi.render].inputs.image = { __type: "core/ASSET", info: { id: "falso.0000" } };
    g[modello.nodi.prompt].inputs.text = "a house";
    g[modello.nodi.campionatore].inputs.seed = 7;
    return g;
  });
  assert.equal(r.status, 403);
  assert.equal(db.stato.render.length, 0);
});
