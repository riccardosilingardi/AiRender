// Il webhook di Stripe. Eventi da abilitare nel cruscotto Stripe:
// checkout.session.completed, invoice.paid, customer.subscription.updated,
// customer.subscription.deleted.
//
// - Prova e Ricarica (pagamenti una tantum): checkout.session.completed.
// - Abbonamenti: invoice.paid, che arriva a ogni rinnovo. La prima volta
//   (billing_reason subscription_create) crea anche la licenza, leggendo i
//   dati fiscali dalla sessione di Checkout dell'abbonamento: cosi' l'ordine
//   in cui Stripe manda i due eventi non conta.
//
// Ogni passo si puo' ripetere: se qualcosa fallisce si risponde 500 e Stripe
// riprova (per tre giorni), senza doppi accrediti ne' doppie fatture.

import { facoltativa, serve } from "../../lib/ambiente.mjs";
import { creaDb } from "../../lib/db.mjs";
import { creaEmail } from "../../lib/email.mjs";
import { creaFatture, fattura } from "../../lib/fatture.mjs";
import { listino, renderDelPeriodo } from "../../lib/listino.mjs";
import { json, protetto } from "../../lib/risposte.mjs";
import { creaStripe, datiFiscali, firmaValida, prodottoDelPrezzo } from "../../lib/stripe.mjs";
import { accredita, cambiaPiano, mandaCodice, nuovaLicenza, traMesi } from "../../lib/vendite.mjs";

export function servizi(ambiente = process.env, chiama = fetch) {
  return {
    db: creaDb(ambiente, chiama),
    stripe: creaStripe(ambiente, chiama),
    email: creaEmail(ambiente, chiama),
    fatture: facoltativa("FIC_TOKEN", ambiente) ? creaFatture(ambiente, chiama) : null,
    ambiente,
  };
}

export async function gestisci(req, s = servizi(), adesso = Date.now()) {
  const grezzo = await req.text();
  if (!firmaValida(grezzo, req.headers.get("stripe-signature"), serve("STRIPE_WEBHOOK_SECRET", s.ambiente), adesso)) {
    return json(400, { error: "firma non valida" });
  }
  const evento = JSON.parse(grezzo);
  const oggetto = evento.data?.object || {};
  try {
    if (evento.type === "checkout.session.completed") await sessioneCompletata(s, oggetto);
    else if (evento.type === "invoice.paid") await fatturaPagata(s, oggetto);
    else if (evento.type === "customer.subscription.updated") await abbonamentoCambiato(s, oggetto);
    else if (evento.type === "customer.subscription.deleted") await abbonamentoFinito(s, oggetto);
    else return json(200, { ignorato: evento.type });
  } catch (e) {
    console.error(`webhook ${evento.type} ${evento.id}: ${e.message}`);
    return json(500, { error: e.message });
  }
  await s.db.rpc("airender_evento_nuovo", { p_id: evento.id, p_tipo: evento.type });
  return json(200, { ricevuto: evento.type });
}

const giorno = (secondi) => new Date((secondi ? secondi * 1000 : Date.now())).toISOString().slice(0, 10);

async function sessioneCompletata(s, sessione) {
  if (sessione.mode !== "payment" || sessione.payment_status !== "paid") return;
  const prodotto = sessione.metadata?.prodotto;
  const dati = datiFiscali(sessione);
  let licenzaId;
  let descrizione;
  if (prodotto === "prova") {
    const p = listino.piani.prova;
    const lic = await nuovaLicenza(s, {
      email: dati.email, piano: "prova", origine: "stripe", riferimento: sessione.id,
      stripe_cliente: sessione.customer, dati_fiscali: dati,
      codice_sconto: sessione.discounts?.[0]?.promotion_code || null, manda_email: false,
    });
    licenzaId = lic.id;
    await accredita(s, licenzaId, "prova", p.render, traMesi(p.validita_mesi), sessione.id);
    await mandaCodice(s, licenzaId, dati.email, lic.codice, p.nome);
    descrizione = `AIRENDER ${p.nome}: ${p.render} render validi ${p.validita_mesi} mesi`;
  } else if (prodotto === "ricarica") {
    const r = listino.ricarica;
    licenzaId = sessione.metadata?.licenza;
    if (!licenzaId) throw new Error(`ricarica senza licenza: ${sessione.id}`);
    await accredita(s, licenzaId, "ricarica", r.render, traMesi(r.validita_mesi), sessione.id);
    descrizione = `AIRENDER ${r.nome}: ${r.render} render validi ${r.validita_mesi} mesi`;
  } else {
    return;
  }
  if (s.fatture && sessione.amount_total > 0) {
    await fattura(s, sessione.id, licenzaId, dati, {
      descrizione,
      imponibile: sessione.amount_subtotal - (sessione.total_details?.amount_discount || 0),
      totale: sessione.amount_total,
      data: giorno(sessione.created),
    });
  }
}

// La riga dell'abbonamento: prezzo e periodo. Le versioni recenti dell'API
// di Stripe spostano il prezzo in pricing.price_details.
export function rigaAbbonamento(invoice) {
  const riga = invoice.lines?.data?.find((l) => l.price?.id || l.pricing?.price_details?.price) || invoice.lines?.data?.[0];
  return {
    prezzo: riga?.price?.id || riga?.pricing?.price_details?.price || "",
    fine: riga?.period?.end,
  };
}

function abbonamentoDi(invoice) {
  return invoice.subscription || invoice.parent?.subscription_details?.subscription || "";
}

async function licenzaDellAbbonamento(db, abbonamento) {
  const [l] = await db.select("licenze", `stripe_abbonamento=eq.${encodeURIComponent(abbonamento)}&select=id,piano,email,dati_fiscali`);
  return l || null;
}

async function fatturaPagata(s, invoice) {
  const abbonamento = abbonamentoDi(invoice);
  if (!abbonamento) return;
  const { prezzo, fine } = rigaAbbonamento(invoice);
  const prodotto = prodottoDelPrezzo(prezzo, s.ambiente);
  if (!prodotto?.piano || prodotto.modo !== "subscription") throw new Error(`prezzo sconosciuto ${prezzo} in ${invoice.id}`);

  let licenza = await licenzaDellAbbonamento(s.db, abbonamento);
  if (!licenza) {
    const elenco = await s.stripe.api("GET", "checkout/sessions", { subscription: abbonamento, limit: 1 });
    const sessione = elenco.data?.[0];
    if (!sessione) throw new Error(`nessuna sessione di Checkout per ${abbonamento}`);
    const dati = datiFiscali(sessione);
    const lic = await nuovaLicenza(s, {
      email: dati.email || invoice.customer_email, piano: prodotto.piano, origine: "stripe",
      riferimento: sessione.id, stripe_cliente: invoice.customer, stripe_abbonamento: abbonamento,
      dati_fiscali: dati, codice_sconto: sessione.discounts?.[0]?.promotion_code || null,
      manda_email: false,
    });
    licenza = { id: lic.id, piano: prodotto.piano, dati_fiscali: dati, email: dati.email || invoice.customer_email, codice: lic.codice };
  } else if (licenza.piano !== prodotto.piano) {
    await cambiaPiano(s, licenza.id, prodotto.piano);
  }

  // I render del piano arrivano col primo pagamento e a ogni rinnovo. Un
  // conguaglio per cambio piano (subscription_update) non accredita un mese
  // intero: arriva col rinnovo successivo.
  if (["subscription_create", "subscription_cycle"].includes(invoice.billing_reason)) {
    const quanti = renderDelPeriodo(prodotto.piano, prodotto.intervallo);
    const scade = fine ? new Date(fine * 1000).toISOString() : traMesi(prodotto.intervallo === "anno" ? 12 : 1);
    await accredita(s, licenza.id, "piano", quanti, scade, invoice.id);
  }
  await mandaCodice(s, licenza.id, licenza.email, licenza.codice, listino.piani[prodotto.piano].nome);

  if (s.fatture && invoice.amount_paid > 0) {
    const p = listino.piani[prodotto.piano];
    await fattura(s, invoice.id, licenza.id, licenza.dati_fiscali, {
      descrizione: `AIRENDER ${p.nome}, abbonamento ${prodotto.intervallo === "anno" ? "annuale" : "mensile"}`,
      imponibile: invoice.total_excluding_tax ?? invoice.subtotal,
      totale: invoice.amount_paid,
      data: giorno(invoice.status_transitions?.paid_at || invoice.created),
    });
  }
}

async function abbonamentoCambiato(s, abbonamento) {
  const licenza = await licenzaDellAbbonamento(s.db, abbonamento.id);
  if (!licenza) return; // la crea invoice.paid
  const prezzo = abbonamento.items?.data?.[0]?.price?.id;
  const prodotto = prodottoDelPrezzo(prezzo, s.ambiente);
  if (prodotto?.piano && prodotto.piano !== licenza.piano && ["active", "trialing"].includes(abbonamento.status)) {
    await cambiaPiano(s, licenza.id, prodotto.piano);
  }
}

// Abbonamento chiuso: la licenza resta, con i crediti di ricarica e
// benvenuto ancora validi e le funzioni di "nessuno". Il lotto del piano
// scade da solo a fine periodo.
async function abbonamentoFinito(s, abbonamento) {
  const licenza = await licenzaDellAbbonamento(s.db, abbonamento.id);
  if (licenza) await cambiaPiano(s, licenza.id, "nessuno");
}

export default protetto("stripe-webhook", (req) => gestisci(req));

export const config = { path: "/api/stripe-webhook" };
