// GET /api/gestisci?t=<gettone>  -> 303 verso il portale clienti di Stripe
// (cambio piano, carta, disdetta, ricevute). Il gettone lo da' /api/saldo.

import { serve } from "../../lib/ambiente.mjs";
import { leggiFirma } from "../../lib/codice.mjs";
import { creaDb } from "../../lib/db.mjs";
import { errore } from "../../lib/risposte.mjs";
import { creaStripe } from "../../lib/stripe.mjs";

export async function gestisci(req, { ambiente = process.env, db = creaDb(ambiente), stripe = creaStripe(ambiente) } = {}) {
  const dati = leggiFirma(new URL(req.url).searchParams.get("t"), serve("AIRENDER_FIRMA", ambiente));
  if (!dati?.licenza) {
    return errore(401, "link_scaduto", "Il link e' scaduto o non e' valido.", "Riaprilo dal plugin: vale un'ora.");
  }
  const [licenza] = await db.select("licenze", `id=eq.${encodeURIComponent(dati.licenza)}&select=stripe_cliente`);
  if (!licenza?.stripe_cliente) {
    return errore(404, "senza_abbonamento", "Questa licenza non ha un abbonamento Stripe da gestire.",
      "Se l'hai comprata da un rivenditore, scrivi a lui; se no, scrivi a AIRENDER.");
  }
  const portale = await stripe.api("POST", "billing_portal/sessions", {
    customer: licenza.stripe_cliente,
    return_url: serve("SITO_URL", ambiente),
  });
  return new Response(null, { status: 303, headers: { location: portale.url } });
}

export default (req) => gestisci(req);

export const config = { path: "/api/gestisci" };
