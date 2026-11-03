// GET /api/saldo con X-Airender-Licenza: piano, saldo, scadenza, funzioni del
// piano e i link (firmati, un'ora) per Ricarica e Gestisci abbonamento. E'
// quello che il plugin e la web app mostrano accanto al pulsante Ricarica.

import { serve } from "../../lib/ambiente.mjs";
import { firma } from "../../lib/codice.mjs";
import { creaDb } from "../../lib/db.mjs";
import { intestazioniCliente, licenzaDi } from "../../lib/licenza.mjs";
import { funzioni, listino } from "../../lib/listino.mjs";
import { json } from "../../lib/risposte.mjs";

export async function gestisci(req, { ambiente = process.env, db = creaDb(ambiente) } = {}) {
  const { licenza, risposta } = await licenzaDi(db, intestazioniCliente(req).codice);
  if (risposta) return risposta;
  const sito = serve("SITO_URL", ambiente).replace(/\/$/, "");
  const gettone = firma({ licenza: licenza.id }, serve("AIRENDER_FIRMA", ambiente));
  return json(200, {
    piano: licenza.piano,
    funzioni: funzioni(licenza.piano),
    email: licenza.email,
    ultime_cifre: licenza.ultime_cifre,
    saldo: Math.max(0, licenza.saldo.disponibile),
    in_attesa: licenza.saldo.in_attesa,
    prossima_scadenza: licenza.saldo.prossima_scadenza,
    postazioni: { usate: licenza.postazioni_usate, massimo: licenza.postazioni_max },
    pesi: listino.pesi,
    ricarica_url: `${sito}/api/acquista?prodotto=ricarica&t=${gettone}`,
    gestisci_url: licenza.stripe_abbonamento ? `${sito}/api/gestisci?t=${gettone}` : null,
    prezzi_url: `${sito}/#prezzi`,
  });
}

export default (req) => gestisci(req);

export const config = { path: "/api/saldo" };
