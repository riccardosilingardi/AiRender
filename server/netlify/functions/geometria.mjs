// «Tieni la geometria» coi crediti AIRENDER: la prima passata col ControlNet
// (Spigoli, Profondita', Linee dritte), sul deployment della Comfy Developer
// Platform di Riccardo.
//
// Parla la stessa API v2 dei workflow del deployment (carica l'asset, manda
// il lavoro, leggi lo stato, scarica l'uscita), sotto /geometria/api/v2, cosi'
// il motore usa lo stesso client di core/provider/geometria.py cambiando solo
// indirizzo e intestazioni.
//
// Cosa aggiunge al deployment:
// - al posto della chiave Comfy il cliente manda il suo codice licenza, e il
//   piano deve comprendere «Tieni la geometria» (LISTINO, funzioni);
// - il grafo NON viene dal client: il server lo ricostruisce da geometria.json
//   (scritto da scripts/scrivi_listino.py a partire dal workflow del motore e
//   da core/config.py) e dal client prende solo asset, prompt e seme. Con la
//   chiave di Riccardo parte solo questo workflow;
// - un asset si puo' usare solo dalla licenza che l'ha caricato (id firmato);
// - all'invio RISERVA LISTINO.pesi_azioni.tieni_geometria; ADDEBITA quando il
//   lavoro finisce «succeeded» con un'uscita; ANNULLA se il deployment rifiuta
//   l'invio, se il lavoro fallisce o se il cliente lo ferma;
// - toglie EXIF, XMP e testi dalla vista prima di caricarla (lib/pulisci.mjs).
//
// La chiave (COMFY_API_KEY) e l'indirizzo del deployment
// (AIRENDER_COMFY_WORKFLOW_URL) vivono solo nell'ambiente di Netlify.

import { createHash } from "node:crypto";
import modello from "../../geometria.json" with { type: "json" };
import { serve } from "../../lib/ambiente.mjs";
import { creaDb } from "../../lib/db.mjs";
import { intestazioniCliente, licenzaDi } from "../../lib/licenza.mjs";
import { funzioni, listino } from "../../lib/listino.mjs";
import { immaginePulita } from "../../lib/pulisci.mjs";
import { rifiutoDellaRiserva } from "../../lib/riserva.mjs";
import { errore, json, protetto } from "../../lib/risposte.mjs";
import { chiaveVersoComfy } from "./router.mjs";

export const PREFISSO = "/geometria/api/v2";
// Come si chiama la prima passata nella tabella dei render (colonna modello).
export const MODELLO = "airender/tieni-geometria";
export const STATI_FINITI = ["succeeded", "failed", "expired", "canceled"];
// Limiti di forma, non di prezzo: oltre, la richiesta non viene dal motore.
const PROMPT_MASSIMO = 6000;
const SEME_MASSIMO = 2 ** 32 - 1;
const TIPI = ["image/png", "image/jpeg", "image/webp"];
const ATTESA_COMFY_MS = 20_000;

export function analizzaPercorso(pathname) {
  if (!pathname.startsWith(PREFISSO + "/")) return null;
  const parti = pathname.slice(PREFISSO.length + 1).replace(/\/$/, "").split("/").map(decodeURIComponent);
  if (parti.length === 1 && parti[0] === "assets") return { cosa: "asset" };
  if (parti[0] !== "jobs") return null;
  if (parti.length === 1) return { cosa: "invio" };
  if (parti.length === 2) return { cosa: "stato", lavoro: parti[1] };
  if (parti.length === 3 && parti[2] === "cancel") return { cosa: "annulla", lavoro: parti[1] };
  if (parti.length === 4 && parti[2] === "outputs" && /^\d+$/.test(parti[3])) {
    return { cosa: "uscita", lavoro: parti[1], indice: Number(parti[3]) };
  }
  return null;
}

// L'origine del deployment: solo https, senza percorso (come il motore).
export function deployment(ambiente) {
  const scritto = serve("AIRENDER_COMFY_WORKFLOW_URL", ambiente);
  let u;
  try { u = new URL(scritto); } catch { u = null; }
  if (!u || u.protocol !== "https:") {
    const e = new Error("AIRENDER_COMFY_WORKFLOW_URL non e' un indirizzo https.");
    e.name = "VariabileMancante";
    throw e;
  }
  return u.origin;
}

// L'id dell'asset che vede il cliente: quello di Comfy piu' una firma legata
// alla licenza. Senza tabella: chi non ha caricato l'asset non sa firmarlo.
export function firmaAsset(licenzaId, asset, chiave) {
  return createHash("sha256").update(`asset:${licenzaId}:${asset}:${chiave}`).digest("hex").slice(0, 32);
}

export function assetDelCliente(licenzaId, idCliente, chiave) {
  if (typeof idCliente !== "string") return null;
  const punto = idCliente.lastIndexOf(".");
  if (punto <= 0) return null;
  const asset = idCliente.slice(0, punto);
  return firmaAsset(licenzaId, asset, chiave) === idCliente.slice(punto + 1) ? asset : null;
}

// Il grafo da mandare: quello di geometria.json per i controlli scelti (gia'
// coi valori di config.py), e dal client solo asset, prompt e seme.
export function grafo(asset, prompt, seme, controlli = "spigoli", m = modello) {
  const g = structuredClone(m.grafi[controlli]);
  g[m.nodi.immagine].inputs.image = { __type: "core/ASSET", info: { id: asset } };
  g[m.nodi.prompt].inputs.text = prompt;
  g[m.nodi.campionatore].inputs.seed = seme;
  return g;
}

// Quali controlli (Spigoli, Profondita', Linee dritte) ha scelto il client:
// i nodi ControlNet che ci sono nel suo grafo, nell'ordine di geometria.json.
export function controlliDalGrafo(g, m = modello) {
  const scelti = m.controlli.filter(([, nodo]) => g[nodo]).map(([nome]) => nome);
  const chiave = scelti.join("+");
  return m.grafi[chiave] ? chiave : null;
}

// Cosa il client chiede, letto dal grafo che manda il motore.
export function richiestaDalGrafo(corpo, m = modello) {
  const g = corpo?.workflow;
  if (!g || typeof g !== "object") return null;
  const controlli = controlliDalGrafo(g, m);
  if (!controlli) return null;
  const asset = g[m.nodi.immagine]?.inputs?.image?.info?.id;
  const prompt = g[m.nodi.prompt]?.inputs?.text;
  const seme = g[m.nodi.campionatore]?.inputs?.seed;
  if (typeof prompt !== "string" || !prompt.trim() || prompt.length > PROMPT_MASSIMO) return null;
  if (!Number.isInteger(seme) || seme < 0 || seme > SEME_MASSIMO) return null;
  return { asset, prompt, seme, controlli };
}

export function pesoGeometria(l = listino) {
  return l.pesi_azioni?.tieni_geometria ?? null;
}

function fuoriDalPiano(licenza, canale) {
  const f = funzioni(licenza.piano);
  if (!f.canali.includes(canale)) {
    return errore(403, "canale_non_incluso", `Il piano ${f.nome} non comprende questo canale.`,
      "Usa il plugin per Allplan o la web app.");
  }
  if (!f.tieni_geometria) {
    return errore(403, "funzione_non_inclusa",
      `Il piano ${f.nome} non comprende «Tieni la geometria». Non e' partito niente.`,
      "Togli la spunta per mandare solo a Nano Banana, o passa al piano Studio dalla pagina dei prezzi di AIRENDER.");
  }
  return null;
}

export async function gestisci(req, { db, ambiente = process.env, chiama = fetch } = {}) {
  db = db || creaDb(ambiente, chiama);
  const percorso = analizzaPercorso(new URL(req.url).pathname);
  if (!percorso) return errore(404, "percorso_sconosciuto", "Questo indirizzo del server AIRENDER non esiste.", "Aggiorna il plugin.");

  const cliente = intestazioniCliente(req);
  const { licenza, risposta } = await licenzaDi(db, cliente.codice);
  if (risposta) return risposta;
  const ctx = { db, ambiente, chiama, cliente, licenza };

  if (req.method === "POST" && percorso.cosa === "asset") return caricaAsset(req, ctx);
  if (req.method === "POST" && percorso.cosa === "invio") return invia(req, ctx);
  if (req.method === "GET" && percorso.cosa === "stato") return stato(percorso.lavoro, ctx);
  if (req.method === "GET" && percorso.cosa === "uscita") return uscita(percorso.lavoro, percorso.indice, ctx);
  if (req.method === "POST" && percorso.cosa === "annulla") return annulla(percorso.lavoro, ctx);
  return errore(405, "metodo_non_ammesso", "Il server AIRENDER non accetta questa chiamata.", "Aggiorna il plugin.");
}

async function caricaAsset(req, { ambiente, chiama, cliente, licenza }) {
  const fuori = fuoriDalPiano(licenza, cliente.canale);
  if (fuori) return fuori;
  let file;
  try {
    file = (await req.formData()).get("file");
  } catch {
    file = null;
  }
  if (!file || typeof file.arrayBuffer !== "function" || !TIPI.includes(file.type)) {
    return errore(400, "vista_non_valida", "La vista non e' arrivata come immagine PNG, JPEG o WebP.",
      "Riprova; se si ripete, aggiorna il plugin.");
  }
  const chiave = serve("COMFY_API_KEY", ambiente);
  const base = deployment(ambiente);
  const pulita = immaginePulita(Buffer.from(await file.arrayBuffer()));
  const nome = `vista.${file.type.split("/")[1]}`;
  const modulo = new FormData();
  modulo.append("file_path", nome);
  modulo.append("content_type", file.type);
  modulo.append("file", new Blob([pulita], { type: file.type }), nome);
  let r;
  try {
    r = await chiama(`${base}/api/v2/assets`, {
      method: "POST", headers: { authorization: `Bearer ${chiave}`, accept: "application/json" },
      body: modulo, signal: AbortSignal.timeout(ATTESA_COMFY_MS),
    });
  } catch {
    return errore(504, "deployment_irraggiungibile", "Il workflow «Tieni la geometria» non ha risposto al server AIRENDER.",
      "Riprova fra un minuto: non e' stato scalato niente.");
  }
  const corpo = await r.json().catch(() => ({}));
  if (!r.ok || !corpo.id) return rifiutoDelDeployment(r.status, corpo, "il caricamento della vista");
  return json(201, { id: `${corpo.id}.${firmaAsset(licenza.id, String(corpo.id), chiave)}` });
}

async function invia(req, { db, ambiente, chiama, cliente, licenza }) {
  const fuori = fuoriDalPiano(licenza, cliente.canale);
  if (fuori) return fuori;
  let corpo;
  try {
    corpo = await req.json();
  } catch {
    return errore(400, "corpo_non_valido", "La richiesta non e' un JSON leggibile.", "Riprova; se si ripete, aggiorna il plugin.");
  }
  const chiesto = richiestaDalGrafo(corpo);
  if (!chiesto) {
    return errore(400, "workflow_non_valido", "La richiesta di «Tieni la geometria» non ha prompt e seme validi.",
      "Aggiorna il plugin.");
  }
  const chiaveComfy = serve("COMFY_API_KEY", ambiente);
  const base = deployment(ambiente);
  const asset = assetDelCliente(licenza.id, chiesto.asset, chiaveComfy);
  if (!asset) {
    return errore(403, "asset_sconosciuto", "La vista indicata non e' stata caricata da questa licenza.",
      "Rilancia il render: la vista si ricarica.");
  }
  const quanto = pesoGeometria();
  if (!quanto) {
    return errore(503, "servizio_non_configurato", "«Tieni la geometria» non ha un prezzo nel listino del server.",
      "Riprova piu' tardi; se dura, scrivi a AIRENDER.");
  }
  const chiave = (req.headers.get("idempotency-key") || "").slice(0, 200);
  if (!chiave) return errore(400, "idempotenza_mancante", "Manca la Idempotency-Key.", "Aggiorna il plugin.");

  const riserva = await db.rpc("airender_riserva", {
    p_licenza: licenza.id, p_postazione: cliente.postazione, p_canale: cliente.canale,
    p_chiave: chiave, p_modello: MODELLO, p_dimensione: `${modello.lato_massimo}px`, p_peso: quanto,
  });
  const rifiuto = rifiutoDellaRiserva(riserva, quanto);
  if (rifiuto) return rifiuto;

  let r;
  try {
    r = await chiama(`${base}/api/v2/jobs`, {
      method: "POST",
      headers: {
        authorization: `Bearer ${chiaveComfy}`,
        "idempotency-key": chiaveVersoComfy(licenza.id, chiave),
        "content-type": "application/json",
        accept: "application/json",
      },
      body: JSON.stringify({ workflow: grafo(asset, chiesto.prompt, chiesto.seme, chiesto.controlli) }),
      signal: AbortSignal.timeout(ATTESA_COMFY_MS),
    });
  } catch {
    // Non si sa se il deployment l'ha preso: la riserva resta, e con la
    // stessa Idempotency-Key il motore riprova senza pagare due volte.
    return errore(504, "deployment_irraggiungibile", "Il workflow «Tieni la geometria» non ha risposto al server AIRENDER.",
      "Riprova fra un minuto: il credito non e' stato scalato.");
  }
  const lavoro = await r.json().catch(() => ({}));
  if (!r.ok || !lavoro.id) {
    if (!riserva.ripetuto) await db.rpc("airender_annulla", { p_render: riserva.render });
    return rifiutoDelDeployment(r.status, lavoro, "l'invio del workflow");
  }
  await db.rpc("airender_avvia", { p_render: riserva.render, p_richiesta: String(lavoro.id) });
  return json(201, vistaDelLavoro(lavoro));
}

async function renderDelCliente(db, licenza, lavoro) {
  const render = await db.rpc("airender_render_di", { p_licenza: licenza.id, p_richiesta: lavoro });
  return render && render.modello === MODELLO ? render : null;
}

const sconosciuto = () => errore(404, "richiesta_sconosciuta", "Questo lavoro non e' della tua licenza.", "Rilancia il render.");

async function leggiLavoro(base, lavoro, ambiente, chiama) {
  // Il deployment dice di seguire i suoi link; il server pero' non li
  // conserva e li ricostruisce come li scrive l'API (NON VERIFICATO su un
  // deployment vero: PRD).
  return chiama(`${base}/api/v2/jobs/${encodeURIComponent(lavoro)}`, {
    headers: { authorization: `Bearer ${serve("COMFY_API_KEY", ambiente)}`, accept: "application/json" },
    signal: AbortSignal.timeout(ATTESA_COMFY_MS),
  });
}

async function stato(lavoro, { db, ambiente, chiama, licenza }) {
  const render = await renderDelCliente(db, licenza, lavoro);
  if (!render) return sconosciuto();
  let r;
  try {
    r = await leggiLavoro(deployment(ambiente), lavoro, ambiente, chiama);
  } catch {
    return errore(504, "deployment_irraggiungibile", "Il workflow «Tieni la geometria» non ha risposto al server AIRENDER.",
      "Riprova fra un minuto.");
  }
  const letto = await r.json().catch(() => ({}));
  if (!r.ok) return rifiutoDelDeployment(r.status, letto, "la lettura del lavoro");
  const vista = vistaDelLavoro(letto, lavoro);
  // Un lavoro gia' fermato dal cliente non si paga anche se poi finisce.
  if (render.stato === "annullato") return json(200, vista, { "x-airender-render-scalati": "0" });
  if (letto.status === "succeeded" && vista.outputs.length) {
    const addebito = await db.rpc("airender_addebita", { p_render: render.id, p_crediti_comfy: null });
    return json(200, vista, {
      "x-airender-render-scalati": String(addebito.ripetuto ? 0 : render.peso),
      "x-airender-saldo": String(Math.max(0, addebito.saldo?.disponibile ?? 0)),
    });
  }
  if (STATI_FINITI.includes(letto.status)) {
    await db.rpc("airender_annulla", { p_render: render.id });
    return json(200, vista, { "x-airender-render-scalati": "0" });
  }
  return json(200, vista);
}

async function uscita(lavoro, indice, { db, ambiente, chiama, licenza }) {
  const render = await renderDelCliente(db, licenza, lavoro);
  if (!render) return sconosciuto();
  if (render.stato !== "addebitato") {
    return errore(409, "lavoro_non_finito", "Il workflow «Tieni la geometria» non ha ancora un'immagine.",
      "Aspetta che il lavoro finisca, poi riprova.");
  }
  const base = deployment(ambiente);
  let r;
  try {
    r = await leggiLavoro(base, lavoro, ambiente, chiama);
  } catch {
    return errore(504, "deployment_irraggiungibile", "Il workflow «Tieni la geometria» non ha risposto al server AIRENDER.",
      "Riprova fra un minuto.");
  }
  const letto = await r.json().catch(() => ({}));
  const link = (letto.outputs || []).filter((u) => u?.url)[indice]?.url;
  if (!r.ok || !link) return rifiutoDelDeployment(r.ok ? 404 : r.status, letto, "la lettura dell'uscita");
  const assoluto = new URL(link, base);
  // La chiave va solo al deployment; un link firmato altrove si scarica senza.
  const intestazioni = assoluto.origin === base ? { authorization: `Bearer ${serve("COMFY_API_KEY", ambiente)}` } : {};
  if (assoluto.protocol !== "https:") return rifiutoDelDeployment(502, {}, "il link dell'uscita");
  let d;
  try {
    d = await chiama(assoluto.href, { headers: intestazioni, signal: AbortSignal.timeout(ATTESA_COMFY_MS) });
  } catch {
    return errore(504, "deployment_irraggiungibile", "L'immagine di «Tieni la geometria» non si e' scaricata.", "Riprova fra un minuto.");
  }
  if (!d.ok) return rifiutoDelDeployment(d.status, {}, "lo scaricamento dell'uscita");
  // Il corpo passa in streaming: un PNG a 1536 px puo' superare i 6 MB di
  // una risposta bufferizzata di Netlify (NON VERIFICATO: PRD).
  return new Response(d.body, { status: 200, headers: { "content-type": d.headers.get("content-type") || "image/png" } });
}

async function annulla(lavoro, { db, ambiente, chiama, licenza }) {
  const render = await renderDelCliente(db, licenza, lavoro);
  if (!render) return sconosciuto();
  try {
    await chiama(`${deployment(ambiente)}/api/v2/jobs/${encodeURIComponent(lavoro)}/cancel`, {
      method: "POST",
      headers: { authorization: `Bearer ${serve("COMFY_API_KEY", ambiente)}`, "content-type": "application/json" },
      body: "{}", signal: AbortSignal.timeout(ATTESA_COMFY_MS),
    });
  } catch {
    // Il deployment non ha risposto: il lavoro forse continua, ma il cliente
    // ha smesso di aspettarlo e non lo paga.
  }
  await db.rpc("airender_annulla", { p_render: render.id });
  return json(200, { id: lavoro, status: "canceled" }, { "x-airender-render-scalati": "0" });
}

// Al cliente torna solo cio' che il motore legge, coi link del server AIRENDER.
export function vistaDelLavoro(lavoro, id = String(lavoro.id)) {
  const qui = `${PREFISSO}/jobs/${encodeURIComponent(id)}`;
  const uscite = (Array.isArray(lavoro.outputs) ? lavoro.outputs : []).filter((u) => u?.url);
  return {
    id,
    status: String(lavoro.status || ""),
    outputs: uscite.map((u, i) => ({ node_id: u.node_id ?? null, url: `${qui}/outputs/${i}` })),
    ...(lavoro.error ? { error: { message: String(lavoro.error.message || lavoro.error.code || lavoro.error).slice(0, 300) } } : {}),
    urls: { self: qui, cancel: `${qui}/cancel` },
  };
}

// Un 401/402/403 del deployment riguarda la chiave di Riccardo, non il
// cliente: non si gira cosi' com'e'.
function rifiutoDelDeployment(stato, corpo, cosa) {
  if ([401, 402, 403].includes(stato)) {
    return errore(503, "servizio_non_disponibile",
      "«Tieni la geometria» e' momentaneamente ferma dal lato di Comfy. Il tuo credito non e' stato scalato.",
      "Togli la spunta per mandare solo a Nano Banana, o riprova piu' tardi; se dura, scrivi a AIRENDER.");
  }
  const dettaglio = String(corpo?.message || corpo?.error?.message || corpo?.error || "").slice(0, 300);
  return errore(stato >= 400 ? stato : 502, "workflow_rifiutato",
    `«Tieni la geometria»: ${cosa} non e' riuscito (HTTP ${stato})${dettaglio ? `: ${dettaglio}` : ""}. Il credito non e' stato scalato.`,
    "Togli la spunta per mandare solo a Nano Banana, o riprova.");
}

export default protetto("geometria", (req) => gestisci(req));

export const config = { path: "/geometria/api/v2/*" };
