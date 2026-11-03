// POST /api/admin con Authorization: Bearer <AIRENDER_ADMIN_TOKEN>.
// Le licenze che non passano da Stripe: la rivendita Serteco (fattura
// Serteco, attivazione a mano di Riccardo), le prove regalate, i rimborsi in
// crediti. Si usa da scripts/licenze.py.
//
// azioni:
//   crea       { email, piano, mesi?, rivenditore?, render?, manda_email? }
//   accredita  { licenza|email, render, mesi?, nota? }
//   piano      { licenza|email, piano }
//   sospendi / riattiva  { licenza|email }
//   nuovo_codice { licenza|email }
//   cerca      { email }

import { randomUUID, timingSafeEqual } from "node:crypto";
import { serve } from "../../lib/ambiente.mjs";
import { creaDb } from "../../lib/db.mjs";
import { creaEmail } from "../../lib/email.mjs";
import { listino } from "../../lib/listino.mjs";
import { errore, json } from "../../lib/risposte.mjs";
import { accredita, cambiaPiano, nuovaLicenza, nuovoCodice, traMesi } from "../../lib/vendite.mjs";

function autorizzato(req, ambiente) {
  const atteso = Buffer.from(`Bearer ${serve("AIRENDER_ADMIN_TOKEN", ambiente)}`);
  const dato = Buffer.from(req.headers.get("authorization") || "");
  return dato.length === atteso.length && timingSafeEqual(dato, atteso);
}

async function trova(db, { licenza, email }) {
  const filtro = licenza ? `id=eq.${encodeURIComponent(licenza)}` : `email=ilike.${encodeURIComponent(email || "")}`;
  const righe = await db.select("licenze", `${filtro}&select=id,email,piano,stato,origine,rivenditore,ultime_cifre,creata_il`);
  return righe;
}

export async function gestisci(req, { ambiente = process.env, db = creaDb(ambiente), email = creaEmail(ambiente), casuale } = {}) {
  if (req.method !== "POST") return errore(405, "metodo_non_ammesso", "Solo POST.", "Usa scripts/licenze.py.");
  if (!autorizzato(req, ambiente)) return errore(401, "non_autorizzato", "Gettone di amministrazione mancante o sbagliato.", "Controlla AIRENDER_ADMIN_TOKEN.");
  const a = await req.json();

  if (a.azione === "crea") {
    const p = listino.piani[a.piano];
    if (!p || a.piano === "nessuno") return errore(400, "piano_sconosciuto", `Piano sconosciuto: ${a.piano}.`, "Usa prova, base, pro o studio.");
    const lic = await nuovaLicenza({ db, email }, {
      email: a.email, piano: a.piano, origine: "manuale", riferimento: `manuale:${randomUUID()}`,
      rivenditore: a.rivenditore || null, manda_email: a.manda_email !== false,
    }, casuale);
    const mesi = Number(a.mesi) || (p.tipo === "una_tantum" ? p.validita_mesi : 1);
    const render = Number(a.render) || (p.tipo === "una_tantum" ? p.render : p.render_mese * mesi);
    await accredita({ db }, lic.id, a.piano === "prova" ? "prova" : "piano", render, traMesi(mesi), `manuale:${lic.id}:iniziale`);
    return json(200, { licenza: lic.id, codice: lic.codice, render, scade_il: traMesi(mesi) });
  }

  if (a.azione === "cerca") return json(200, { licenze: await trova(db, a) });

  const trovate = await trova(db, a);
  if (trovate.length !== 1) {
    return errore(400, "licenza_ambigua", `Trovate ${trovate.length} licenze per questa ricerca.`, "Indica l'id della licenza (azione cerca).", { licenze: trovate });
  }
  const licenza = trovate[0];

  if (a.azione === "accredita") {
    const render = Number(a.render);
    if (!(render > 0)) return errore(400, "render_mancanti", "Quanti render accreditare?", "Passa render > 0.");
    const esito = await accredita({ db }, licenza.id, "manuale", render, traMesi(Number(a.mesi) || 12), `manuale:${randomUUID()}`);
    return json(200, { licenza: licenza.id, ...esito });
  }
  if (a.azione === "piano") {
    if (!listino.piani[a.piano]) return errore(400, "piano_sconosciuto", `Piano sconosciuto: ${a.piano}.`, "Usa prova, base, pro, studio o nessuno.");
    await cambiaPiano({ db }, licenza.id, a.piano);
    return json(200, { licenza: licenza.id, piano: a.piano });
  }
  if (a.azione === "sospendi" || a.azione === "riattiva") {
    await db.aggiorna("licenze", `id=eq.${licenza.id}`, { stato: a.azione === "sospendi" ? "sospesa" : "attiva" });
    return json(200, { licenza: licenza.id, stato: a.azione === "sospendi" ? "sospesa" : "attiva" });
  }
  if (a.azione === "nuovo_codice") {
    const codice = await nuovoCodice({ db, email: a.manda_email === false ? null : email }, licenza, casuale);
    return json(200, { licenza: licenza.id, codice });
  }
  return errore(400, "azione_sconosciuta", `Azione sconosciuta: ${a.azione}.`, "Vedi l'elenco in testa a server/netlify/functions/admin.mjs.");
}

export default (req) => gestisci(req);

export const config = { path: "/api/admin" };
