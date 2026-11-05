// Funzione programmata (ogni ora): cancella dallo Storage i risultati piu'
// vecchi di RISULTATI_CONSERVATI_ORE (48): il link firmato dato al plugin
// scade dopo 24 ore, poi resta un giorno di margine. Le 48 ore sono quelle
// promesse nei testi legali (docs/legale). Vedi supabase/migrations/002_pulizia_risultati.sql.

import { creaDb } from "../../lib/db.mjs";
import { json, protetto } from "../../lib/risposte.mjs";
import { RISULTATI_CONSERVATI_ORE } from "./router.mjs";

export const ORE = RISULTATI_CONSERVATI_ORE;
const PER_GIRO = 500;

export async function pulisci({ db = creaDb(), giri = 10, log = console.log } = {}) {
  let tolti = 0;
  for (let i = 0; i < giri; i++) {
    const nomi = (await db.rpc("airender_risultati_vecchi", { p_ore: ORE, p_quanti: PER_GIRO })) || [];
    if (!nomi.length) break;
    await db.rimuoviRisultati(nomi);
    tolti += nomi.length;
    if (nomi.length < PER_GIRO) break;
  }
  log(JSON.stringify({ funzione: "pulizia", risultati_tolti: tolti }));
  return tolti;
}

export default protetto("pulizia", async () => json(200, { tolti: await pulisci() }));

export const config = { schedule: "@hourly" };
