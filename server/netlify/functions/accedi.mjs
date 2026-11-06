// POST /api/accedi {email, codice}: l'accesso alla web app. Una licenza e'
// l'account del cliente (email + codice, migrazione 001): si entra se il
// codice esiste, e' attivo ed e' di quell'email. Il codice resta nel browser
// del cliente (web/ponte.py lo salva come lo Studio sul PC); il server non
// tiene sessioni.
//
// Un rifiuto non dice quale dei due e' sbagliato: chi prova email a caso non
// scopre quali sono clienti. Piu' avanti l'accesso passa a un link via email
// (stesso account, stessa tabella licenze).

import { valido } from "../../lib/codice.mjs";
import { creaDb } from "../../lib/db.mjs";
import { licenzaDi } from "../../lib/licenza.mjs";
import { funzioni } from "../../lib/listino.mjs";
import { errore, json, protetto } from "../../lib/risposte.mjs";

const NON_CORRISPONDONO = () => errore(401, "accesso_rifiutato",
  "Email e codice licenza non corrispondono a una licenza AIRENDER.",
  "Usa l'email con cui hai comprato AIRENDER e il codice AIR-... che ti e' arrivato dopo l'acquisto.");

export const normalizzaEmail = (email) => String(email || "").trim().toLowerCase();

export async function gestisci(req, { ambiente = process.env, db = creaDb(ambiente) } = {}) {
  if (req.method !== "POST") {
    return errore(405, "metodo", "Questa pagina accetta solo l'invio del modulo di accesso.", "Torna alla pagina di accesso.");
  }
  const dati = await req.json().catch(() => ({}));
  const email = normalizzaEmail(dati.email);
  const codice = String(dati.codice || "").trim();
  if (!email.includes("@")) {
    return errore(400, "email_mancante", "Manca l'email, o non ha la forma di un'email.",
      "Scrivi l'email con cui hai comprato AIRENDER.");
  }
  if (!valido(codice)) {
    return errore(400, "licenza_non_valida",
      "Il codice licenza non ha la forma giusta (AIR- e quattro gruppi di quattro caratteri).",
      "Ricopialo dall'email che hai ricevuto dopo l'acquisto.");
  }
  const { licenza, risposta } = await licenzaDi(db, codice);
  if (risposta) {
    // Sospesa: lo si dice, il codice e' giusto. Sconosciuta: lo stesso rifiuto
    // di un'email sbagliata.
    return risposta.status === 403 ? risposta : NON_CORRISPONDONO();
  }
  if (normalizzaEmail(licenza.email) !== email) return NON_CORRISPONDONO();
  return json(200, {
    email: licenza.email,
    piano: licenza.piano,
    funzioni: funzioni(licenza.piano),
    ultime_cifre: licenza.ultime_cifre,
    saldo: Math.max(0, licenza.saldo.disponibile),
  });
}

export default protetto("accedi", (req) => gestisci(req));

export const config = { path: "/api/accedi" };
