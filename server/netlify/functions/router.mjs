// Il router dei render. Parla lo stesso protocollo a coda del Comfy Router
// (POST .../requests, GET .../requests/{id}/status, GET .../requests/{id}),
// cosi' il motore usa lo stesso codice di core/provider/comfy.py cambiando
// solo indirizzo e intestazione.
//
// Cosa aggiunge al Router:
// - al posto della chiave Comfy il cliente manda il suo codice licenza;
// - all'invio controlla piano e saldo e RISERVA il peso del render;
// - inoltra al Router con la chiave di Riccardo (COMFY_API_KEY, solo
//   nell'ambiente di Netlify) e fallback_provider=false sempre, qualunque
//   cosa chieda il client: la destinazione annunciata deve essere vera;
// - ADDEBITA solo quando il risultato torna con un'immagine; se il Router
//   rifiuta l'invio o chiude senza immagine, ANNULLA la riserva.
//
// Ogni chiamata di stato o risultato controlla che la richiesta sia della
// licenza che chiede: nessuno legge il render di un altro.

import { createHash } from "node:crypto";
import { serve } from "../../lib/ambiente.mjs";
import { creaDb } from "../../lib/db.mjs";
import { intestazioniCliente, licenzaDi } from "../../lib/licenza.mjs";
import { dimensioneDaCorpo, fuoriDalPiano, peso } from "../../lib/listino.mjs";
import { errore, json, protetto } from "../../lib/risposte.mjs";

export const COMFY = "https://api.comfy.org/v2/models";
// Il Router vuole esattamente "false": ogni altro valore lascia acceso il
// ripiego su un altro provider (CLAUDE.md, trappole note).
export const FALLBACK = "false";
// Oltre questo peso il risultato non sta nella risposta di una funzione
// Netlify (6 MB): si carica nello Storage e torna un link firmato.
export const RISPOSTA_MASSIMA_BYTE = 4_500_000;
export const LINK_RISULTATO_SECONDI = 24 * 3600;
const ATTESA_COMFY_MS = 20_000;

export function analizzaPercorso(pathname) {
  const m = pathname.match(/^\/v2\/models\/([^/]+)\/([^/]+)\/requests(?:\/([^/]+)(\/status)?)?\/?$/);
  if (!m) return null;
  return { modello: `${m[1]}/${m[2]}`, richiesta: m[3] ? decodeURIComponent(m[3]) : null, stato: Boolean(m[4]) };
}

// L'immagine nel risultato di Gemini: una parte inlineData o fileData.
export function haImmagine(uscita) {
  const parti = uscita?.candidates?.[0]?.content?.parts;
  if (!Array.isArray(parti)) return false;
  return parti.some((p) => p?.inlineData?.data || p?.fileData?.fileUri);
}

export function chiaveVersoComfy(licenzaId, chiave) {
  return createHash("sha256").update(`${licenzaId}:${chiave}`).digest("hex");
}

export async function gestisci(req, { db, ambiente = process.env, chiama = fetch } = {}) {
  db = db || creaDb(ambiente, chiama);
  const percorso = analizzaPercorso(new URL(req.url).pathname);
  if (!percorso) return errore(404, "percorso_sconosciuto", "Questo indirizzo del server AIRENDER non esiste.", "Aggiorna il plugin.");

  const cliente = intestazioniCliente(req);
  const { licenza, risposta } = await licenzaDi(db, cliente.codice);
  if (risposta) return risposta;

  if (req.method === "POST" && !percorso.richiesta) return invia(req, percorso, cliente, licenza, { db, ambiente, chiama });
  if (req.method === "GET" && percorso.richiesta) return leggi(percorso, licenza, { db, ambiente, chiama });
  return errore(405, "metodo_non_ammesso", "Il server AIRENDER non accetta questa chiamata.", "Aggiorna il plugin.");
}

async function invia(req, { modello }, cliente, licenza, { db, ambiente, chiama }) {
  let corpo;
  try {
    corpo = await req.json();
  } catch {
    return errore(400, "corpo_non_valido", "La richiesta non e' un JSON leggibile.", "Riprova; se si ripete, aggiorna il plugin.");
  }
  const dimensione = dimensioneDaCorpo(corpo);
  const quanto = dimensione && peso(modello, dimensione);
  if (!quanto) {
    return errore(403, "modello_non_incluso",
      `Il modello ${modello}${dimensione ? ` a ${dimensione}` : ""} non e' compreso nei crediti AIRENDER.`,
      "Scegli Nano Banana 2 o Nano Banana Pro nel preset, oppure usa la tua chiave Comfy (--provider comfy).");
  }
  const fuori = fuoriDalPiano(licenza.piano, modello, dimensione, cliente.canale);
  if (fuori) return errore(403, fuori.tipo, fuori.messaggio, fuori.cosa_fare);

  const chiave = (req.headers.get("idempotency-key") || "").slice(0, 200);
  if (!chiave) return errore(400, "idempotenza_mancante", "Manca la Idempotency-Key.", "Aggiorna il plugin.");
  // Prima di riservare: senza la chiave di Riccardo non partirebbe niente, e
  // una riserva fatta per niente terrebbe fermo il credito per 24 ore.
  const chiaveComfy = serve("COMFY_API_KEY", ambiente);

  const riserva = await db.rpc("airender_riserva", {
    p_licenza: licenza.id, p_postazione: cliente.postazione, p_canale: cliente.canale,
    p_chiave: chiave, p_modello: modello, p_dimensione: dimensione, p_peso: quanto,
  });
  if (riserva.esito === "saldo") {
    return errore(402, "insufficient_credits",
      `Il saldo AIRENDER non basta: questo render costa ${quanto} e ne restano ${Math.max(0, riserva.disponibile)}. Non e' partito niente.`,
      "Premi Ricarica (o apri la pagina dei prezzi di AIRENDER), poi rilancia.",
      { saldo: Math.max(0, riserva.disponibile), peso: quanto });
  }
  if (riserva.esito === "postazioni") {
    return errore(403, "postazioni_esaurite",
      `Questa licenza e' gia' usata su ${riserva.usate} postazioni, il massimo del piano.`,
      "Passa al piano Studio (3 postazioni) o scrivi a AIRENDER per liberare una postazione.");
  }
  if (riserva.esito !== "ok") {
    return errore(403, "licenza_sospesa", "La licenza non e' attiva.", "Scrivi a AIRENDER per riattivarla.");
  }

  const query = new URLSearchParams({ fallback_provider: FALLBACK });
  let r;
  try {
    r = await chiama(`${COMFY}/${modello}/requests?${query}`, {
      method: "POST",
      headers: {
        "x-api-key": chiaveComfy,
        "idempotency-key": chiaveVersoComfy(licenza.id, chiave),
        "content-type": "application/json",
        accept: "application/json",
      },
      body: JSON.stringify(corpo),
      signal: AbortSignal.timeout(ATTESA_COMFY_MS),
    });
  } catch {
    // Non si sa se il Router l'ha preso: la riserva resta, e con la stessa
    // Idempotency-Key il plugin riprova senza pagare due volte.
    return errore(504, "router_irraggiungibile", "Il Comfy Router non ha risposto al server AIRENDER.",
      "Riprova fra un minuto: il credito non e' stato scalato.");
  }
  const uscita = await r.json().catch(() => ({}));
  if (!r.ok) {
    if (!riserva.ripetuto) await db.rpc("airender_annulla", { p_render: riserva.render });
    return rifiutoDelRouter(r.status, uscita);
  }
  if (uscita.request_id) await db.rpc("airender_avvia", { p_render: riserva.render, p_richiesta: String(uscita.request_id) });
  return json(r.status, uscita, inoltra(r, ["retry-after"]));
}

async function leggi({ modello, richiesta, stato }, licenza, { db, ambiente, chiama }) {
  const render = await db.rpc("airender_render_di", { p_licenza: licenza.id, p_richiesta: richiesta });
  if (!render) return errore(404, "richiesta_sconosciuta", "Questa richiesta non e' della tua licenza.", "Rilancia il render.");

  const indirizzo = `${COMFY}/${modello}/requests/${encodeURIComponent(richiesta)}${stato ? "/status" : ""}`;
  let r;
  try {
    r = await chiama(indirizzo, {
      headers: { "x-api-key": serve("COMFY_API_KEY", ambiente), accept: "application/json" },
      signal: AbortSignal.timeout(ATTESA_COMFY_MS),
    });
  } catch {
    return errore(504, "router_irraggiungibile", "Il Comfy Router non ha risposto al server AIRENDER.", "Riprova fra un minuto.");
  }
  const uscita = await r.json().catch(() => ({}));
  if (stato || r.status === 202) return json(r.status, uscita, inoltra(r, ["retry-after"]));
  if (!r.ok) return rifiutoDelRouter(r.status, uscita);

  if (!haImmagine(uscita)) {
    await db.rpc("airender_annulla", { p_render: render.id });
    return json(200, uscita, { "x-airender-render-scalati": "0" });
  }
  const crediti = Number(r.headers.get("x-comfy-credits-used")) || null;
  const addebito = await db.rpc("airender_addebita", { p_render: render.id, p_crediti_comfy: crediti });
  const corpo = await alleggerisci(uscita, render, db);
  return json(200, corpo, {
    "x-airender-render-scalati": String(addebito.ripetuto ? 0 : render.peso),
    "x-airender-saldo": String(Math.max(0, addebito.saldo?.disponibile ?? 0)),
  });
}

// Un'immagine inline troppo pesante per la risposta diventa un link firmato
// (fileData.fileUri): il motore la scarica come fa con i link di FLUX.
export async function alleggerisci(uscita, render, db) {
  if (JSON.stringify(uscita).length <= RISPOSTA_MASSIMA_BYTE) return uscita;
  const copia = structuredClone(uscita);
  const parti = copia.candidates[0].content.parts;
  for (let i = 0; i < parti.length; i++) {
    const dati = parti[i]?.inlineData;
    if (!dati?.data) continue;
    const tipo = dati.mimeType || "image/png";
    const link = await db.caricaRisultato(`${render.licenza_id}/${render.id}-${i}.${tipo.split("/")[1] || "png"}`,
      Buffer.from(dati.data, "base64"), tipo, LINK_RISULTATO_SECONDI);
    parti[i] = { fileData: { mimeType: tipo, fileUri: link } };
  }
  return copia;
}

// Un 401/402/403 del Router riguarda la chiave di Riccardo, non il cliente:
// non si gira cosi' com'e'.
function rifiutoDelRouter(stato, uscita) {
  if ([401, 402, 403].includes(stato)) {
    return errore(503, "servizio_non_disponibile",
      "Il servizio AIRENDER e' momentaneamente fermo dal lato del Comfy Router. Il tuo credito non e' stato scalato.",
      "Riprova piu' tardi; se dura, scrivi a AIRENDER.");
  }
  return json(stato, uscita);
}

function inoltra(r, nomi) {
  const fuori = {};
  for (const n of nomi) if (r.headers.get(n)) fuori[n] = r.headers.get(n);
  return fuori;
}

export default protetto("router", (req) => gestisci(req));

export const config = { path: "/v2/models/*" };
