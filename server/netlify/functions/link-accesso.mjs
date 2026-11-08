// POST /api/link-accesso {email}: manda per email il link per entrare nella
// web app, uno per ogni licenza attiva di quell'email.
//
// La risposta e' sempre la stessa, che l'email sia di un cliente o no: chi
// prova email a caso non scopre quali sono clienti. Nel database del link
// resta solo lo SHA-256 del gettone (migrazione 004).
//
// L'indirizzo del link lo decide il server, mai la richiesta: chi mettesse
// un Origin falso riceverebbe comunque un link verso il sito AIRENDER, nella
// casella del cliente. Nelle anteprime Netlify il link torna all'anteprima.

import { createHash, randomBytes } from "node:crypto";
import { serve } from "../../lib/ambiente.mjs";
import { creaDb } from "../../lib/db.mjs";
import { creaEmail } from "../../lib/email.mjs";
import { listino, piano } from "../../lib/listino.mjs";
import { errore, json, protetto } from "../../lib/risposte.mjs";
import { normalizzaEmail } from "./accedi.mjs";

export const hashGettone = (gettone) => createHash("sha256").update(String(gettone)).digest("hex");

export function sitoDelLink(ambiente) {
  if (ambiente.CONTEXT === "deploy-preview" && ambiente.DEPLOY_PRIME_URL) return ambiente.DEPLOY_PRIME_URL.replace(/\/$/, "");
  return serve("SITO_URL", ambiente).replace(/\/$/, "");
}

const MANDATA = (email) => json(200, {
  inviata: true,
  messaggio: `Se ${email} e' l'email di una licenza AIRENDER, ti abbiamo mandato un link per entrare. Vale ${listino.accesso.link_minuti} minuti.`,
});

export async function gestisci(req, { ambiente = process.env, db = creaDb(ambiente), email: posta = creaEmail(ambiente), casuale = randomBytes } = {}) {
  if (req.method !== "POST") {
    return errore(405, "metodo", "Questa pagina accetta solo la richiesta del link.", "Torna alla pagina di accesso.");
  }
  const dati = await req.json().catch(() => ({}));
  const email = normalizzaEmail(dati.email);
  if (!email.includes("@") || email.length > 254) {
    return errore(400, "email_mancante", "Manca l'email, o non ha la forma di un'email.",
      "Scrivi l'email con cui hai comprato AIRENDER.");
  }
  const licenze = (await db.rpc("airender_licenze_di", { p_email: email })) || [];
  const minuti = listino.accesso.link_minuti;
  const sito = sitoDelLink(ambiente);
  const voci = [];
  for (const l of licenze) {
    if (l.link_recenti >= listino.accesso.link_massimi_ora) continue; // in silenzio: la risposta resta uguale
    const gettone = casuale(32).toString("base64url");
    await db.rpc("airender_crea_link", { p_hash_gettone: hashGettone(gettone), p_licenza: l.id, p_minuti: minuti });
    voci.push({ nomePiano: piano(l.piano).nome, ultime_cifre: l.ultime_cifre, link: `${sito}/studio/#accesso=${gettone}` });
  }
  if (voci.length) await posta.inviaLink(email, voci, minuti);
  return MANDATA(email);
}

export default protetto("link-accesso", (req) => gestisci(req));

export const config = { path: "/api/link-accesso" };
