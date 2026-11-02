// GET /api/acquista?prodotto=pro_mese  -> 303 verso il Checkout di Stripe.
// GET /api/acquista?prodotto=ricarica&t=<gettone firmato>  -> la ricarica
// di una licenza esistente (il gettone lo da' /api/saldo al plugin).
//
// Il Checkout raccoglie quello che serve alla fattura elettronica: indirizzo,
// partita IVA, codice destinatario SDI o PEC, codice fiscale. I codici
// sconto (segnalazioni Serteco) si scrivono nel Checkout stesso.

import { facoltativa, serve } from "../../lib/ambiente.mjs";
import { leggiFirma } from "../../lib/codice.mjs";
import { errore } from "../../lib/risposte.mjs";
import { creaStripe, PRODOTTI } from "../../lib/stripe.mjs";

export function parametriCheckout(nome, { sito, prezzo, licenza, iva }) {
  const p = PRODOTTI[nome];
  const parametri = {
    mode: p.modo,
    line_items: [{ price: prezzo, quantity: 1, ...(iva ? { tax_rates: [iva] } : {}) }],
    success_url: `${sito}/grazie.html?prodotto=${nome}`,
    cancel_url: `${sito}/#prezzi`,
    allow_promotion_codes: true,
    billing_address_collection: "required",
    tax_id_collection: { enabled: true },
    locale: "it",
    custom_fields: [
      { key: "sdi", type: "text", optional: true,
        label: { type: "custom", custom: "Codice destinatario SDI o PEC" } },
      { key: "codice_fiscale", type: "text", optional: true,
        label: { type: "custom", custom: "Codice fiscale" } },
    ],
    metadata: { prodotto: nome, ...(licenza ? { licenza } : {}) },
  };
  if (p.modo === "payment") parametri.customer_creation = "always";
  else parametri.subscription_data = { metadata: { prodotto: nome } };
  return parametri;
}

export async function gestisci(req, { ambiente = process.env, stripe = creaStripe(ambiente) } = {}) {
  const url = new URL(req.url);
  const nome = url.searchParams.get("prodotto") || "";
  const p = PRODOTTI[nome];
  if (!p) return errore(400, "prodotto_sconosciuto", `Non conosco il prodotto "${nome}".`, "Torna alla pagina dei prezzi e scegli un piano.");
  let licenza = null;
  if (nome === "ricarica") {
    const dati = leggiFirma(url.searchParams.get("t"), serve("AIRENDER_FIRMA", ambiente));
    if (!dati?.licenza) {
      return errore(401, "link_scaduto", "Il link di ricarica e' scaduto o non e' valido.",
        "Premi di nuovo Ricarica nel plugin: il link vale un'ora.");
    }
    licenza = dati.licenza;
  }
  const sessione = await stripe.api("POST", "checkout/sessions", parametriCheckout(nome, {
    sito: serve("SITO_URL", ambiente).replace(/\/$/, ""),
    prezzo: serve(p.variabile, ambiente),
    licenza,
    iva: facoltativa("STRIPE_ALIQUOTA_IVA", ambiente),
  }));
  return new Response(null, { status: 303, headers: { location: sessione.url } });
}

export default (req) => gestisci(req);

export const config = { path: "/api/acquista" };
