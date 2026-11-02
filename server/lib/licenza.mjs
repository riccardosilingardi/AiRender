// La licenza di chi chiama, dalle intestazioni che manda il plugin (o la web
// app): X-Airender-Licenza col codice, X-Airender-Postazione con un'impronta
// della macchina, X-Airender-Canale ("plugin" o "web").

import { hashCodice, valido } from "./codice.mjs";
import { errore } from "./risposte.mjs";

export const CANALI = ["plugin", "web"];

export function intestazioniCliente(req) {
  return {
    codice: req.headers.get("x-airender-licenza") || "",
    postazione: (req.headers.get("x-airender-postazione") || "").slice(0, 128),
    canale: CANALI.includes(req.headers.get("x-airender-canale")) ? req.headers.get("x-airender-canale") : "plugin",
  };
}

// La licenza, o la Response d'errore da restituire subito.
export async function licenzaDi(db, codice) {
  if (!codice) {
    return { risposta: errore(401, "licenza_mancante",
      "Manca il codice licenza di AIRENDER: senza, non parte niente.",
      "Incolla il codice che hai ricevuto per email (python -m core.cli --licenza AIR-...).") };
  }
  if (!valido(codice)) {
    return { risposta: errore(401, "licenza_non_valida",
      "Il codice licenza non ha la forma giusta (AIR- e quattro gruppi di quattro caratteri).",
      "Ricopialo dall'email che hai ricevuto dopo l'acquisto.") };
  }
  const licenza = await db.rpc("airender_licenza", { p_hash: hashCodice(codice) });
  if (!licenza) {
    return { risposta: errore(401, "licenza_sconosciuta",
      "Questo codice licenza non esiste.",
      "Ricopialo dall'email che hai ricevuto dopo l'acquisto; se non la trovi, scrivi a AIRENDER.") };
  }
  if (licenza.stato !== "attiva") {
    return { risposta: errore(403, "licenza_sospesa",
      `La licenza che finisce con ${licenza.ultime_cifre} e' ${licenza.stato}.`,
      "Scrivi a AIRENDER per riattivarla.") };
  }
  return { licenza };
}
