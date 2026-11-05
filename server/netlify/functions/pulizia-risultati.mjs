// Ogni ora cancella dallo Storage i risultati piu' vecchi di
// RISULTATI_CONSERVATI_ORE. Sono i render troppo pesanti per stare nella
// risposta (router.mjs, alleggerisci): il plugin li scarica subito dal link
// firmato, e al server non serve tenerli (GDPR art. 5.1.e). Nel bucket ci sono
// solo cartelle per licenza con dentro i file: due livelli, non di piu'.

import { creaDb } from "../../lib/db.mjs";
import { RISULTATI_CONSERVATI_ORE } from "./router.mjs";

const ORA_MS = 3600 * 1000;

export async function pulisci({ db, adesso = Date.now(), ore = RISULTATI_CONSERVATI_ORE } = {}) {
  db = db || creaDb();
  const limite = adesso - ore * ORA_MS;
  const vecchi = [];
  for (const cartella of await db.elencaRisultati("")) {
    // Supabase elenca le cartelle come voci senza id.
    if (cartella.id) continue;
    for (const file of await db.elencaRisultati(`${cartella.name}/`)) {
      if (file.id && Date.parse(file.created_at) < limite) vecchi.push(`${cartella.name}/${file.name}`);
    }
  }
  await db.cancellaRisultati(vecchi);
  return { cancellati: vecchi.length };
}

export default async () => {
  const esito = await pulisci();
  return new Response(JSON.stringify(esito), { headers: { "content-type": "application/json" } });
};

export const config = { schedule: "@hourly" };
